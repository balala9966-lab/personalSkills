"""HTTP reverse proxy that captures every request/response and writes traces.

Design choices:

* Stdlib only: `http.server` + `urllib.request`. No FastAPI / requests / httpx.
* One thread per request via `ThreadingHTTPServer` — sufficient for interactive
  AI-tool usage (a few concurrent streams at most). Not designed for production
  high-throughput proxy duty.
* SSE responses are streamed back to the client byte-by-byte while a parallel
  line-buffered parser observes timestamps and extracts structured chunks.
* Header redaction: configured header values are replaced with `sha256:<hex8>`
  in the persisted trace. The upstream request still receives the real value
  (the proxy is not an auth gateway).

Routing:
    /anthropic/<path...>          -> https://api.anthropic.com/<path...>
    /openai/<path...>             -> https://api.openai.com/<path...>
    /upstream/<profile>/<path...> -> <profiles[profile]>/<path...>
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import re
import socket
import socketserver
import ssl
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import urlsplit, urlunsplit

from ..core.models import TraceFull, TraceSummary
from ..core.store import JSONLStore
from .sse_parser import parse_sse_lines

DEFAULT_LISTEN = "127.0.0.1:8788"
DEFAULT_REDACT = ("authorization", "x-api-key", "x-goog-api-key", "anthropic-api-key")

# Headers we strip from outgoing upstream requests (hop-by-hop / framing).
HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}
# Response hop-by-hop headers we don't forward to client as-is.
RESP_STRIP = {"transfer-encoding", "content-encoding", "content-length", "connection"}


# ---------------------------------------------------------------------------
# Config loading (tiny YAML subset, stdlib only)
# ---------------------------------------------------------------------------


@dataclass
class ProxyConfig:
    listen_host: str = "127.0.0.1"
    listen_port: int = 8788
    log_dir: str = "~/.ai-obs-lab/logs"
    redact_headers: tuple[str, ...] = DEFAULT_REDACT
    upstreams: dict[str, str] = field(default_factory=dict)        # anthropic / openai
    profiles: dict[str, str] = field(default_factory=dict)         # cfuse / glm / ...
    # 是否在调上游 https 时跳过 TLS 校验。本地观测代理，用于内网自签网关场景。
    # 默认 False，避免对公网厂商接口降低安全性。需要时在 proxy.yaml 设 `insecure_upstream: true`。
    insecure_upstream: bool = False

    @classmethod
    def from_yaml_file(cls, path: str | os.PathLike) -> "ProxyConfig":
        text = Path(os.path.expanduser(str(path))).read_text(encoding="utf-8")
        return cls.from_yaml_text(text)

    @classmethod
    def from_yaml_text(cls, text: str) -> "ProxyConfig":
        data = _tiny_yaml(text)
        listen = str(data.get("listen") or DEFAULT_LISTEN)
        if ":" in listen:
            host, port_s = listen.rsplit(":", 1)
            port = int(port_s)
        else:
            host, port = "127.0.0.1", int(listen)
        redact_raw = data.get("redact_headers") or list(DEFAULT_REDACT)
        redact = tuple(h.lower() for h in redact_raw)
        ups = data.get("upstreams") or {}
        upstreams = {k: str(v) for k, v in ups.items() if k != "profiles" and isinstance(v, str)}
        profiles_raw = (ups.get("profiles") if isinstance(ups, dict) else None) or {}
        profiles = {k: str(v) for k, v in profiles_raw.items()}
        # Built-in defaults if user omitted them.
        upstreams.setdefault("anthropic", "https://api.anthropic.com")
        upstreams.setdefault("openai", "https://api.openai.com")
        # insecure_upstream 解析：支持 true/yes/1（大小写不敏感）
        ins_raw = str(data.get("insecure_upstream") or "").strip().lower()
        insecure = ins_raw in ("true", "yes", "1", "on")
        return cls(
            listen_host=host,
            listen_port=port,
            log_dir=str(data.get("log_dir") or "~/.ai-obs-lab/logs"),
            redact_headers=redact,
            upstreams=upstreams,
            profiles=profiles,
            insecure_upstream=insecure,
        )


def _tiny_yaml(text: str) -> dict:
    """Parse the limited YAML subset our config uses.

    Supports: top-level scalars, nested 2-space-indented mappings, and `- item`
    sequences of strings. No anchors, flow style, or quotes-handling beyond
    trivial unquoting. Comments start with `#`.
    """
    root: dict = {}
    stack: list[tuple[int, Any]] = [(-1, root)]  # (indent, container)

    def trim(s: str) -> str:
        i = s.find("#")
        if i >= 0:
            s = s[:i]
        return s.rstrip()

    def unquote(v: str) -> str:
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
            return v[1:-1]
        return v

    for raw_line in text.splitlines():
        line = trim(raw_line)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()

        # Pop deeper containers.
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent_indent, parent = stack[-1] if stack else (-1, root)

        if body.startswith("- "):
            item = unquote(body[2:])
            if not isinstance(parent, list):
                # Convert the most-recently-added key's value to a list.
                # In our tiny YAML, list items always follow a `key:` line that
                # created an empty dict. We turn that dict back into a list.
                # Find the key whose value is `parent`.
                # Easier: parent should already have been switched to list by the
                # `key:` step below when the next line started with `-`.
                pass
            if isinstance(parent, list):
                parent.append(item)
            continue

        if ":" in body:
            key, _, val = body.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "":
                # Could be a mapping or a list — decide on first child line.
                new: Any = {}
                parent[key] = new
                stack.append((indent, new))
                # Peek: if next non-empty line starts with `-` at deeper indent,
                # we want a list. We handle that lazily by upgrading on first `-`.
                # Implement via swap when we encounter the dash:
                #   when stack top is empty dict and a `- item` arrives at the
                #   current container, replace it with a list in its parent.
                # (Handled in the `- ` branch logic above is incomplete; do it now.)
                continue
            parent[key] = unquote(val)
            continue

    # Post-process: any dict that ended up empty and is referenced by `redact_headers`
    # or `profiles` should be coerced from {} if we accidentally created one for a
    # list. Walk and patch known list-valued keys.
    def coerce_list(d: dict, key: str) -> None:
        if key in d and isinstance(d[key], dict) and not d[key]:
            d[key] = []

    coerce_list(root, "redact_headers")
    if isinstance(root.get("upstreams"), dict):
        coerce_list(root["upstreams"], "profiles")

    # The list-coercion above keeps things empty. The real list values come from
    # a second pass: reparse with a tiny dedicated list scanner for known keys.
    root = _reparse_known_lists(text, root)
    return root


_KNOWN_LIST_KEYS = ("redact_headers",)


def _reparse_known_lists(text: str, root: dict) -> dict:
    """Second pass: collect `- item` sequences under known list keys."""
    lines = text.splitlines()
    n = len(lines)
    for i, raw in enumerate(lines):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        key = None
        if stripped.endswith(":") and stripped[:-1] in _KNOWN_LIST_KEYS:
            key = stripped[:-1]
        if key is None:
            continue
        items: list[str] = []
        j = i + 1
        while j < n:
            nxt = lines[j].split("#", 1)[0].rstrip()
            if not nxt.strip():
                j += 1
                continue
            indent = len(nxt) - len(nxt.lstrip(" "))
            base_indent = len(line) - len(line.lstrip(" "))
            if indent <= base_indent:
                break
            body = nxt.strip()
            if body.startswith("- "):
                v = body[2:].strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
                    v = v[1:-1]
                items.append(v)
            j += 1
        root[key] = items
    return root


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------


_CLIENT_HINT_PATTERNS = (
    (re.compile(r"claude-cli|claude-code|anthropic-cli", re.I), "claude-code"),
    (re.compile(r"codex", re.I), "codex"),
    (re.compile(r"cfuse|codefuse", re.I), "cfuse"),
    (re.compile(r"cursor", re.I), "cursor"),
)


def _client_hint(user_agent: str) -> str:
    if not user_agent:
        return "unknown"
    for pat, name in _CLIENT_HINT_PATTERNS:
        if pat.search(user_agent):
            return name
    return "unknown"


def _redact_headers(
    headers: dict[str, str], redact_keys: tuple[str, ...]
) -> dict[str, str]:
    redact_set = {k.lower() for k in redact_keys}
    out: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() in redact_set and v:
            digest = hashlib.sha256(v.encode("utf-8", errors="replace")).hexdigest()[:8]
            out[k] = f"sha256:{digest}"
        else:
            out[k] = v
    return out


def _extract_model(body: dict | None) -> str | None:
    if not isinstance(body, dict):
        return None
    return body.get("model") or None


def _make_proxy_handler(config: ProxyConfig, store: JSONLStore):
    class ProxyHandler(BaseHTTPRequestHandler):
        # Override to silence stdout per-request access logging from BaseHTTPRequestHandler.
        def log_message(self, format: str, *args) -> None:  # noqa: A003
            sys.stderr.write("[proxy] %s - %s\n" % (self.address_string(), format % args))

        # Single dispatch for all HTTP methods.
        def do_GET(self): self._dispatch()         # noqa: N802
        def do_POST(self): self._dispatch()        # noqa: N802
        def do_PUT(self): self._dispatch()         # noqa: N802
        def do_DELETE(self): self._dispatch()      # noqa: N802
        def do_PATCH(self): self._dispatch()       # noqa: N802
        def do_OPTIONS(self): self._dispatch()     # noqa: N802

        # ---------- core ----------

        def _dispatch(self) -> None:
            trace_id = uuid.uuid4().hex
            ts_start = time.time()
            try:
                upstream_name, target_url = self._resolve_target()
            except _RouteError as e:
                self._send_simple(e.code, str(e))
                return

            # Read request body.
            length = int(self.headers.get("Content-Length") or 0)
            raw_body = self.rfile.read(length) if length > 0 else b""
            req_headers = {k: v for k, v in self.headers.items()}
            ua = req_headers.get("User-Agent") or req_headers.get("user-agent") or ""
            client_hint = _client_hint(ua)

            # Build upstream request.
            out_headers = {
                k: v for k, v in req_headers.items()
                if k.lower() not in HOP_BY_HOP
            }
            # Force Host header derivation from target_url to avoid SNI/Host mismatches.
            try:
                parts = urlsplit(target_url)
                out_headers["Host"] = parts.netloc
            except Exception:
                pass

            req = urlrequest.Request(
                target_url,
                data=raw_body if raw_body else None,
                method=self.command,
                headers=out_headers,
            )

            # Try to decode request body as JSON for storage (best-effort).
            try:
                req_body_json = json.loads(raw_body.decode("utf-8")) if raw_body else None
            except (UnicodeDecodeError, json.JSONDecodeError):
                req_body_json = {"_raw_base64_truncated": _b64_preview(raw_body)}

            summary = TraceSummary(
                trace_id=trace_id,
                ts_start=ts_start,
                client_hint=client_hint,
                upstream=upstream_name,
                method=self.command,
                path=self.path,
                model=_extract_model(req_body_json),
            )
            redacted_req_headers = _redact_headers(req_headers, config.redact_headers)

            # Issue upstream call (streaming).
            # 对自签 / 内网网关场景，允许通过 insecure_upstream 关闭 TLS 校验。
            ssl_ctx = None
            if target_url.startswith("https://") and config.insecure_upstream:
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE
            try:
                resp = urlrequest.urlopen(req, timeout=300, context=ssl_ctx) if ssl_ctx else urlrequest.urlopen(req, timeout=300)
            except urlerror.HTTPError as he:
                # Even on HTTP error, capture body and forward.
                err_body = he.read() or b""
                summary.status = he.code
                summary.total_ms = (time.time() - ts_start) * 1000.0
                summary.error = f"HTTPError {he.code}"
                self._send_buffered(he.code, dict(he.headers), err_body)
                self._persist(summary, redacted_req_headers, req_body_json,
                              dict(he.headers), err_body.decode("utf-8", errors="replace"), [], [], [])
                return
            except (urlerror.URLError, socket.timeout, OSError) as e:
                summary.status = 0
                summary.error = f"{type(e).__name__}: {e}"
                summary.total_ms = (time.time() - ts_start) * 1000.0
                self._send_simple(502, f"upstream error: {e}")
                self._persist(summary, redacted_req_headers, req_body_json, {}, "", [], [], [])
                return

            # Forward status + headers.
            status = resp.getcode()
            resp_headers_raw = dict(resp.headers.items())
            forwarded_headers = {k: v for k, v in resp_headers_raw.items()
                                 if k.lower() not in RESP_STRIP}
            self.send_response(status)
            for k, v in forwarded_headers.items():
                self.send_header(k, v)
            # Force chunked-like transfer: we don't know length ahead.
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()

            # Stream response.
            ctype = (resp_headers_raw.get("Content-Type")
                     or resp_headers_raw.get("content-type") or "").lower()
            is_sse = "text/event-stream" in ctype
            timed_lines: list[tuple[float, bytes]] = []
            ttft_ms: float | None = None
            collected = bytearray()
            try:
                if is_sse:
                    # Read line-by-line for SSE.
                    line_buf = bytearray()
                    while True:
                        b = resp.read(1)
                        if not b:
                            if line_buf:
                                ts = time.time()
                                if ttft_ms is None:
                                    ttft_ms = (ts - ts_start) * 1000.0
                                timed_lines.append((ts, bytes(line_buf)))
                                self._write_chunked(bytes(line_buf) + b"\n")
                                collected.extend(line_buf)
                                collected.extend(b"\n")
                                line_buf.clear()
                            break
                        line_buf.extend(b)
                        if b == b"\n":
                            ts = time.time()
                            if ttft_ms is None:
                                ttft_ms = (ts - ts_start) * 1000.0
                            full = bytes(line_buf)
                            timed_lines.append((ts, full.rstrip(b"\r\n")))
                            self._write_chunked(full)
                            collected.extend(full)
                            line_buf.clear()
                    self._write_chunked(b"")  # terminating zero-length chunk
                else:
                    # Non-SSE: stream in 16KB blocks.
                    while True:
                        block = resp.read(16 * 1024)
                        if not block:
                            break
                        if ttft_ms is None:
                            ttft_ms = (time.time() - ts_start) * 1000.0
                        self._write_chunked(block)
                        collected.extend(block)
                    self._write_chunked(b"")
            except Exception as e:
                summary.error = f"stream error: {e}"

            total_ms = (time.time() - ts_start) * 1000.0
            summary.status = status
            summary.ttft_ms = ttft_ms
            summary.total_ms = total_ms

            # Parse to extract structured data.
            parse_state = None
            chunks_serialized = []
            tool_calls_serialized = []
            pauses = []
            if is_sse and timed_lines:
                parse_state = parse_sse_lines(iter(timed_lines), ts_start)
                summary.tokens_in = parse_state.tokens_in
                summary.tokens_out = parse_state.tokens_out
                summary.model = summary.model or parse_state.model
                summary.chunks = len([c for c in parse_state.chunks if c.kind != "pause"])
                tcalls = parse_state.finalized_tool_calls()
                summary.tool_call_count = len(tcalls)
                chunks_serialized = parse_state.chunks
                tool_calls_serialized = tcalls
                pauses = parse_state.pauses_ms
                response_text = "".join(parse_state.text_parts)
            else:
                # Try to decode non-stream JSON response and pull usage / output.
                response_text = _safe_decode(bytes(collected), resp_headers_raw)
                _enrich_from_non_stream(summary, response_text)

            self._persist(
                summary,
                redacted_req_headers,
                req_body_json,
                resp_headers_raw,
                response_text,
                chunks_serialized,
                tool_calls_serialized,
                pauses,
            )

        # ---------- routing ----------

        def _resolve_target(self) -> tuple[str, str]:
            path = self.path or "/"
            # Strip leading slash.
            p = path.lstrip("/")
            if not p:
                raise _RouteError(404, "ai-obs-lab proxy: no upstream specified")
            head, _, rest = p.partition("/")
            if head == "anthropic":
                base = config.upstreams.get("anthropic", "https://api.anthropic.com")
                return "anthropic", _join_url(base, rest)
            if head == "openai":
                base = config.upstreams.get("openai", "https://api.openai.com")
                return "openai", _join_url(base, rest)
            if head == "upstream":
                profile, _, sub = rest.partition("/")
                base = config.profiles.get(profile)
                if not base:
                    raise _RouteError(404, f"unknown upstream profile: {profile}")
                return profile, _join_url(base, sub)
            if head == "_health":
                raise _RouteError(200, "ok")
            raise _RouteError(404, f"unknown route: /{head}")

        # ---------- io helpers ----------

        def _write_chunked(self, data: bytes) -> None:
            try:
                self.wfile.write(("%x\r\n" % len(data)).encode("ascii"))
                if data:
                    self.wfile.write(data)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _send_simple(self, status: int, text: str) -> None:
            body = text.encode("utf-8")
            try:
                self.send_response(status)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _send_buffered(self, status: int, headers: dict, body: bytes) -> None:
            try:
                self.send_response(status)
                for k, v in headers.items():
                    if k.lower() in RESP_STRIP:
                        continue
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if body:
                    self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        # ---------- persistence ----------

        def _persist(self, summary, req_headers, req_body, resp_headers,
                     response_text, chunks, tool_calls, pauses) -> None:
            try:
                store.append_summary(summary)
                tf = TraceFull(
                    summary=summary,
                    request_headers=req_headers,
                    request_body=req_body,
                    response_headers=resp_headers,
                    response_text=response_text,
                    chunks=list(chunks),
                    tool_calls=list(tool_calls),
                    pauses_ms=list(pauses),
                )
                store.write_trace(tf)
            except Exception as e:
                sys.stderr.write(f"[proxy] persist error: {e}\n")

    return ProxyHandler


class _RouteError(Exception):
    def __init__(self, code: int, msg: str):
        super().__init__(msg)
        self.code = code


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _join_url(base: str, sub: str) -> str:
    if not sub:
        return base
    if base.endswith("/"):
        return base + sub
    return base + "/" + sub


def _b64_preview(b: bytes, n: int = 256) -> str:
    import base64
    return base64.b64encode(b[:n]).decode("ascii") + ("..." if len(b) > n else "")


def _safe_decode(data: bytes, headers: dict) -> str:
    if not data:
        return ""
    ce = (headers.get("Content-Encoding") or headers.get("content-encoding") or "").lower()
    if "gzip" in ce:
        try:
            data = gzip.decompress(data)
        except Exception:
            pass
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _enrich_from_non_stream(summary: TraceSummary, text: str) -> None:
    if not text:
        return
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return
    if not isinstance(obj, dict):
        return
    # OpenAI non-stream usage.
    usage = obj.get("usage")
    if isinstance(usage, dict):
        if summary.tokens_in is None:
            summary.tokens_in = usage.get("prompt_tokens") or usage.get("input_tokens")
        if summary.tokens_out is None:
            summary.tokens_out = usage.get("completion_tokens") or usage.get("output_tokens")
    # Anthropic non-stream tool_use blocks.
    if obj.get("type") == "message":
        contents = obj.get("content") or []
        tool_calls = sum(1 for b in contents if isinstance(b, dict) and b.get("type") == "tool_use")
        if tool_calls:
            summary.tool_call_count = tool_calls
    summary.model = summary.model or obj.get("model")


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


class _ThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def run_proxy(config: ProxyConfig, store: JSONLStore | None = None) -> None:
    store = store or JSONLStore(config.log_dir)
    handler_cls = _make_proxy_handler(config, store)
    addr = (config.listen_host, config.listen_port)
    server = _ThreadingHTTPServer(addr, handler_cls)
    sys.stderr.write(
        f"[ai-obs-lab] proxy listening on http://{addr[0]}:{addr[1]}\n"
        f"             log_dir = {store.base_dir}\n"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("[ai-obs-lab] shutting down\n")
    finally:
        server.server_close()
