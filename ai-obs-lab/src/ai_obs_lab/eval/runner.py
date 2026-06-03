"""Eval runner: read a suite YAML, run all (version, case) x N repeats, persist.

The runner is upstream-agnostic: it builds requests for either Anthropic or
OpenAI-style endpoints. By default it calls the upstream DIRECTLY (no proxy),
because eval is typically run as a batch and we don't want it competing for the
proxy's logs. The same Store is used so traces show up in the dashboard.

Trace IDs from eval runs are prefixed with `eval-` so they're easy to filter.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

from ..core.models import (
    Chunk,
    EvalCaseResult,
    EvalRun,
    ToolCallRecord,
    TraceFull,
    TraceSummary,
)
from ..core.store import JSONLStore
from .metrics import (
    avg_logprob_top1,
    keyword_hit_rate,
    pairwise_similarity_variance,
    schema_compliance_rate,
)

DEFAULT_UPSTREAMS = {
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com",
}


# ---------------------------------------------------------------------------
# Suite loading (uses the same tiny YAML parser as ProxyConfig, but inlined for
# clarity since suites have a different shape).
# ---------------------------------------------------------------------------


@dataclass
class SuiteVersion:
    id: str
    system: str
    extra: dict[str, Any]


@dataclass
class SuiteCase:
    id: str
    user: str
    expect_schema: dict | None = None
    expect_keywords: list[str] | None = None


@dataclass
class Suite:
    name: str
    upstream: str             # "anthropic" | "openai" | profile name
    base_url: str             # resolved base URL
    model: str
    temperature: float
    max_tokens: int
    versions: list[SuiteVersion]
    cases: list[SuiteCase]


def load_suite(path: str | os.PathLike, profiles: dict[str, str] | None = None) -> Suite:
    text = Path(os.path.expanduser(str(path))).read_text(encoding="utf-8")
    data = _yaml_load(text)
    upstream = str(data.get("upstream") or "openai")
    base_url = (profiles or {}).get(upstream) or DEFAULT_UPSTREAMS.get(upstream)
    if not base_url:
        raise ValueError(f"unknown upstream '{upstream}' (provide via profiles=)")

    versions = []
    for v in data.get("versions") or []:
        vid = str(v.get("id") or f"v{len(versions)+1}")
        sys_prompt = str(v.get("system") or "")
        extra = {k: v[k] for k in v if k not in ("id", "system")}
        versions.append(SuiteVersion(id=vid, system=sys_prompt, extra=extra))

    cases = []
    for c in data.get("cases") or []:
        cases.append(SuiteCase(
            id=str(c.get("id") or f"case{len(cases)+1}"),
            user=str(c.get("user") or ""),
            expect_schema=c.get("expect_schema"),
            expect_keywords=c.get("expect_keywords"),
        ))

    return Suite(
        name=str(data.get("name") or Path(path).stem),
        upstream=upstream,
        base_url=str(base_url),
        model=str(data.get("model") or "gpt-4o-mini"),
        temperature=float(data.get("temperature") or 0.0),
        max_tokens=int(data.get("max_tokens") or 512),
        versions=versions,
        cases=cases,
    )


# ---------------------------------------------------------------------------
# Tiny YAML loader (suite-shaped: nested dicts, lists of dicts, scalars)
# ---------------------------------------------------------------------------


def _yaml_load(text: str) -> dict:
    """Parse the suite YAML subset used in eval/suites/*.yaml.

    Supports: mappings, lists (`- key: val` block style and `[a, b]` flow style
    for keyword arrays), pipe `|` block scalars, JSON-like inline values for
    expect_schema (`{...}`), comments with `#`. No anchors, no merge keys.
    """
    lines = text.splitlines()
    pos = 0

    def peek_indent(i: int) -> int:
        s = lines[i]
        return len(s) - len(s.lstrip(" "))

    def parse_block(indent: int) -> Any:
        nonlocal pos
        # Determine if this block is a sequence or mapping by peeking first
        # non-empty/non-comment line at >= indent.
        # Default to dict; switch to list if we see `- ` at indent.
        kind = None
        result_dict: dict = {}
        result_list: list = []
        while pos < len(lines):
            raw = lines[pos]
            stripped = raw.split("#", 1)[0].rstrip()
            if not stripped.strip():
                pos += 1
                continue
            cur_indent = len(raw) - len(raw.lstrip(" "))
            if cur_indent < indent:
                break
            if cur_indent > indent:
                # Shouldn't happen at our level; let outer handler deal.
                break
            body = stripped.strip()

            if body.startswith("- "):
                if kind is None:
                    kind = "list"
                elif kind != "list":
                    break
                pos += 1
                # The item may be a scalar or a mapping starting on same line.
                item_body = body[2:].lstrip()
                if ":" in item_body and not item_body.startswith("{") and not item_body.startswith("["):
                    # `- key: val` -> a one-key mapping that may have siblings indented further.
                    # Reconstruct as a mapping by injecting a virtual line.
                    # We parse the rest of this item as a mapping at indent+2.
                    item_indent = cur_indent + 2
                    key, _, val = item_body.partition(":")
                    key = key.strip()
                    val = val.strip()
                    item_map: dict = {}
                    if val == "":
                        # nested mapping/list under this key.
                        sub = parse_block(item_indent + 2) if pos < len(lines) and peek_indent_skip() > item_indent else {}
                        item_map[key] = sub
                    else:
                        item_map[key] = _scalar(val)
                    # Continue absorbing further keys belonging to this list item.
                    while pos < len(lines):
                        raw2 = lines[pos]
                        s2 = raw2.split("#", 1)[0].rstrip()
                        if not s2.strip():
                            pos += 1
                            continue
                        ind2 = len(raw2) - len(raw2.lstrip(" "))
                        if ind2 < item_indent:
                            break
                        if ind2 > item_indent:
                            break
                        body2 = s2.strip()
                        if body2.startswith("- "):
                            break
                        if ":" not in body2:
                            break
                        k2, _, v2 = body2.partition(":")
                        k2 = k2.strip()
                        v2 = v2.strip()
                        pos += 1
                        if v2 == "":
                            sub = parse_block(item_indent + 2)
                            item_map[k2] = sub
                        elif v2 == "|":
                            item_map[k2] = _read_block_scalar(item_indent + 2)
                        else:
                            item_map[k2] = _scalar(v2)
                    result_list.append(item_map)
                else:
                    result_list.append(_scalar(item_body))
                continue

            # Mapping line.
            if kind is None:
                kind = "dict"
            elif kind != "dict":
                break
            if ":" not in body:
                pos += 1
                continue
            key, _, val = body.partition(":")
            key = key.strip()
            val = val.strip()
            pos += 1
            if val == "":
                result_dict[key] = parse_block(indent + 2)
            elif val == "|":
                result_dict[key] = _read_block_scalar(indent + 2)
            else:
                result_dict[key] = _scalar(val)

        return result_list if kind == "list" else result_dict

    def peek_indent_skip() -> int:
        i = pos
        while i < len(lines):
            s = lines[i]
            stripped = s.split("#", 1)[0].rstrip()
            if stripped.strip():
                return len(s) - len(s.lstrip(" "))
            i += 1
        return -1

    def _read_block_scalar(min_indent: int) -> str:
        nonlocal pos
        out_lines: list[str] = []
        while pos < len(lines):
            raw = lines[pos]
            if not raw.strip():
                out_lines.append("")
                pos += 1
                continue
            ind = len(raw) - len(raw.lstrip(" "))
            if ind < min_indent:
                break
            out_lines.append(raw[min_indent:])
            pos += 1
        # Strip trailing empty lines.
        while out_lines and out_lines[-1] == "":
            out_lines.pop()
        return "\n".join(out_lines) + ("\n" if out_lines else "")

    def _scalar(s: str) -> Any:
        s = s.strip()
        if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
            return s[1:-1]
        # JSON-ish inline (object / array).
        if s.startswith("{") or s.startswith("["):
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                # Try to coerce single-quoted keys (rare in our suites; skip).
                return s
        if s in ("true", "True"):
            return True
        if s in ("false", "False"):
            return False
        if s in ("null", "~", ""):
            return None
        try:
            if "." in s or "e" in s.lower():
                return float(s)
            return int(s)
        except ValueError:
            return s

    root = parse_block(0)
    return root if isinstance(root, dict) else {"_root": root}


# ---------------------------------------------------------------------------
# Upstream invocation
# ---------------------------------------------------------------------------


def _build_anthropic_payload(suite: Suite, version: SuiteVersion, case: SuiteCase) -> dict:
    payload = {
        "model": suite.model,
        "max_tokens": suite.max_tokens,
        "temperature": suite.temperature,
        "system": version.system,
        "messages": [{"role": "user", "content": case.user}],
    }
    return payload


def _build_openai_payload(suite: Suite, version: SuiteVersion, case: SuiteCase, want_logprobs: bool) -> dict:
    payload: dict = {
        "model": suite.model,
        "temperature": suite.temperature,
        "max_tokens": suite.max_tokens,
        "messages": [
            {"role": "system", "content": version.system},
            {"role": "user", "content": case.user},
        ],
    }
    if want_logprobs:
        payload["logprobs"] = True
        payload["top_logprobs"] = 5
    return payload


def _call_upstream(
    suite: Suite, payload: dict, api_key: str | None
) -> tuple[int, str, float, float, list[float] | None]:
    """Return (status, response_text, ttft_ms, total_ms, chosen_logprobs)."""
    url = _endpoint_url(suite)
    headers = {"Content-Type": "application/json"}
    if suite.upstream == "anthropic":
        headers["x-api-key"] = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        headers["anthropic-version"] = "2023-06-01"
    else:
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        elif os.environ.get("OPENAI_API_KEY"):
            headers["Authorization"] = f"Bearer {os.environ['OPENAI_API_KEY']}"
    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(url, data=data, method="POST", headers=headers)
    t0 = time.time()
    try:
        with urlrequest.urlopen(req, timeout=120) as resp:
            t1 = time.time()
            body = resp.read()
            t2 = time.time()
            text = body.decode("utf-8", errors="replace")
            ttft_ms = (t1 - t0) * 1000.0
            total_ms = (t2 - t0) * 1000.0
            chosen_lp = _extract_chosen_logprobs(text) if suite.upstream != "anthropic" else None
            return resp.getcode(), text, ttft_ms, total_ms, chosen_lp
    except urlerror.HTTPError as he:
        total_ms = (time.time() - t0) * 1000.0
        body = he.read() if hasattr(he, "read") else b""
        return he.code, body.decode("utf-8", errors="replace"), total_ms, total_ms, None
    except (urlerror.URLError, OSError) as e:
        total_ms = (time.time() - t0) * 1000.0
        return 0, f"upstream_error: {e}", total_ms, total_ms, None


def _endpoint_url(suite: Suite) -> str:
    base = suite.base_url.rstrip("/")
    if suite.upstream == "anthropic":
        return f"{base}/v1/messages"
    # openai-compat
    return f"{base}/v1/chat/completions"


def _extract_output_text(suite: Suite, raw_text: str) -> str:
    try:
        obj = json.loads(raw_text)
    except json.JSONDecodeError:
        return raw_text
    if suite.upstream == "anthropic":
        parts = []
        for block in obj.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts) or raw_text
    # openai
    choices = obj.get("choices") or []
    if choices and isinstance(choices[0], dict):
        msg = choices[0].get("message") or {}
        return msg.get("content") or ""
    return raw_text


def _extract_usage(suite: Suite, raw_text: str) -> tuple[int | None, int | None]:
    try:
        obj = json.loads(raw_text)
    except json.JSONDecodeError:
        return None, None
    if suite.upstream == "anthropic":
        u = obj.get("usage") or {}
        return u.get("input_tokens"), u.get("output_tokens")
    u = obj.get("usage") or {}
    return u.get("prompt_tokens"), u.get("completion_tokens")


def _extract_chosen_logprobs(raw_text: str) -> list[float] | None:
    try:
        obj = json.loads(raw_text)
    except json.JSONDecodeError:
        return None
    choices = obj.get("choices") or []
    if not choices:
        return None
    lp = (choices[0] or {}).get("logprobs") or {}
    content = lp.get("content") or []
    out: list[float] = []
    for t in content:
        if isinstance(t, dict) and "logprob" in t:
            try:
                out.append(float(t["logprob"]))
            except (TypeError, ValueError):
                pass
    return out or None


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


@dataclass
class _RepeatOutcome:
    """Result of one independent (version, case, repeat-index) upstream call."""

    trace_id: str
    output: str
    ttft_ms: float
    total_ms: float
    tokens_out: int | None
    logprobs: list[float]
    ok: bool


def _run_one_repeat(
    suite: Suite,
    version: SuiteVersion,
    case: SuiteCase,
    k: int,
    eval_run_id: str,
    store: JSONLStore,
    api_key: str | None,
    want_logprobs: bool,
) -> _RepeatOutcome:
    """Execute a single upstream call and persist its trace.

    Pure with respect to shared mutable state except for `store`, which is
    thread-safe (coarse lock). Safe to call concurrently across repeats.
    """
    if suite.upstream == "anthropic":
        payload = _build_anthropic_payload(suite, version, case)
    else:
        payload = _build_openai_payload(suite, version, case, want_logprobs)
    status, text, ttft_ms, total_ms, chosen_lp = _call_upstream(suite, payload, api_key)
    ok = 200 <= status < 300
    out_text = _extract_output_text(suite, text) if ok else ""
    tin, tout = _extract_usage(suite, text)

    trace_id = f"eval-{eval_run_id}-{version.id}-{case.id}-{k}"
    summary = TraceSummary(
        trace_id=trace_id,
        ts_start=time.time(),
        client_hint=f"eval:{eval_run_id}",
        upstream=suite.upstream,
        method="POST",
        path=_endpoint_url(suite),
        model=suite.model,
        status=status,
        ttft_ms=ttft_ms,
        total_ms=total_ms,
        tokens_in=tin,
        tokens_out=tout,
        chunks=None,
        tool_call_count=0,
        error=None if ok else f"status={status}",
    )
    tf = TraceFull(
        summary=summary,
        request_headers={"x-eval-run": eval_run_id, "x-version": version.id, "x-case": case.id},
        request_body=payload,
        response_headers={},
        response_text=text,
        chunks=[],
        tool_calls=[],
        pauses_ms=[],
    )
    try:
        store.append_summary(summary)
        store.write_trace(tf)
    except Exception as e:
        sys.stderr.write(f"[eval] persist failed: {e}\n")

    return _RepeatOutcome(
        trace_id=trace_id,
        output=out_text,
        ttft_ms=ttft_ms,
        total_ms=total_ms,
        tokens_out=tout,
        logprobs=chosen_lp or [],
        ok=ok,
    )


def run_suite(
    suite: Suite,
    *,
    repeat: int = 1,
    store: JSONLStore,
    api_key: str | None = None,
    want_logprobs: bool = False,
    concurrency: int = 1,
) -> EvalRun:
    eval_run_id = f"er-{uuid.uuid4().hex[:10]}"
    ts_start = time.time()
    er = EvalRun(
        eval_run_id=eval_run_id,
        ts_start=ts_start,
        suite_name=suite.name,
        suite_path="",  # filled by caller if known
        upstream=suite.upstream,
        model=suite.model,
        temperature=suite.temperature,
        repeat=repeat,
        version_ids=[v.id for v in suite.versions],
        case_ids=[c.id for c in suite.cases],
        results=[],
    )

    workers = max(1, concurrency)
    for version in suite.versions:
        for case in suite.cases:
            # Run the `repeat` independent calls, optionally in parallel. Results
            # are reassembled in repeat order (by k) so aggregated metrics are
            # deterministic regardless of completion order.
            repeats_out: list[_RepeatOutcome] = [None] * repeat  # type: ignore[list-item]
            if workers == 1:
                for k in range(repeat):
                    repeats_out[k] = _run_one_repeat(
                        suite, version, case, k, eval_run_id, store, api_key, want_logprobs
                    )
            else:
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    futures = {
                        pool.submit(
                            _run_one_repeat, suite, version, case, k,
                            eval_run_id, store, api_key, want_logprobs,
                        ): k
                        for k in range(repeat)
                    }
                    for fut in as_completed(futures):
                        repeats_out[futures[fut]] = fut.result()

            outputs = [r.output for r in repeats_out]
            ttfts = [r.ttft_ms for r in repeats_out]
            totals = [r.total_ms for r in repeats_out]
            out_tokens = [int(r.tokens_out) for r in repeats_out if r.tokens_out is not None]
            lp_seqs = [r.logprobs for r in repeats_out if r.logprobs]
            errors = sum(1 for r in repeats_out if not r.ok)
            trace_ids = [r.trace_id for r in repeats_out]

            result = EvalCaseResult(
                version_id=version.id,
                case_id=case.id,
                repeats=repeat,
                trace_ids=trace_ids,
                outputs=outputs,
                similarity_variance=pairwise_similarity_variance(outputs),
                schema_compliance_rate=schema_compliance_rate(outputs, case.expect_schema),
                keyword_hit_rate=keyword_hit_rate(outputs, case.expect_keywords),
                avg_logprob_top1=avg_logprob_top1(lp_seqs) if lp_seqs else None,
                avg_ttft_ms=(sum(ttfts) / len(ttfts)) if ttfts else None,
                avg_total_ms=(sum(totals) / len(totals)) if totals else None,
                avg_tokens_out=(sum(out_tokens) / len(out_tokens)) if out_tokens else None,
                errors=errors,
            )
            er.results.append(result)

    store.append_eval_run(er)
    return er


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ai_obs_lab.eval.runner")
    p.add_argument("--suite", required=True, help="Path to suite YAML")
    p.add_argument("--repeat", type=int, default=1)
    p.add_argument("--concurrency", type=int, default=1,
                   help="Parallel upstream calls per (version, case). Default 1 (sequential).")
    p.add_argument("--logprobs", action="store_true", help="OpenAI: request logprobs=true")
    p.add_argument("--log-dir", default=None)
    p.add_argument("--judge", action="store_true", help="Run LLM-as-Judge after eval")
    p.add_argument("--judge-model", default="openai:gpt-4o-mini")
    args = p.parse_args(argv)

    suite = load_suite(args.suite)
    store = JSONLStore(args.log_dir) if args.log_dir else JSONLStore()
    er = run_suite(suite, repeat=args.repeat, store=store,
                   want_logprobs=args.logprobs, concurrency=args.concurrency)
    er.suite_path = str(Path(args.suite).resolve())
    sys.stdout.write(json.dumps({
        "eval_run_id": er.eval_run_id,
        "suite": er.suite_name,
        "results": [
            {
                "version": r.version_id,
                "case": r.case_id,
                "similarity_variance": r.similarity_variance,
                "schema_compliance_rate": r.schema_compliance_rate,
                "keyword_hit_rate": r.keyword_hit_rate,
                "avg_logprob_top1": r.avg_logprob_top1,
                "avg_ttft_ms": r.avg_ttft_ms,
                "avg_tokens_out": r.avg_tokens_out,
                "errors": r.errors,
            } for r in er.results
        ],
    }, indent=2))
    sys.stdout.write("\n")

    if args.judge:
        from .judge import judge_eval_run
        judge_eval_run(er, store=store, judge_model=args.judge_model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
