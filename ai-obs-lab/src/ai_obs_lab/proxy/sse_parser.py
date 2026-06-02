"""Incremental SSE parser for Anthropic Messages API and OpenAI Chat Completions.

This module is intentionally pure: it does NOT do any I/O. Feed it bytes (or
lines) and timestamps; it produces structured events that the proxy persists.

Two flavors are auto-detected by event field shape:

* Anthropic (Messages API streaming, `event: <name>` + `data: <json>`):
    - message_start / content_block_start / content_block_delta / content_block_stop
    - message_delta / message_stop
    - Tool calls arrive as content_block_start(type=tool_use, id=..., name=...)
      followed by content_block_delta(type=input_json_delta, partial_json=...).
* OpenAI (Chat Completions streaming, `data: <json>` lines, ends with `[DONE]`):
    - chunk.choices[].delta.content  -> text
    - chunk.choices[].delta.tool_calls[] -> tool call deltas (function.name / arguments)
    - chunk.choices[].finish_reason -> stop

The parser emits a stream of `Chunk` records (see core.models) plus extracted
`ToolCallRecord`s. Pause detection (>800ms between chunks) is also applied.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Iterable

from ..core.models import Chunk, ToolCallRecord

PAUSE_THRESHOLD_MS = 800.0


@dataclass
class ParseState:
    """Mutable parser state accumulated across SSE events of one response."""

    ts_start: float
    seq: int = 0
    last_chunk_ts: float = 0.0
    # Buffered SSE event under construction (Anthropic-style).
    cur_event_name: str = ""
    cur_data_lines: list[str] = field(default_factory=list)
    # Tool call accumulators keyed by tool id (or content_block index for Anthropic).
    tool_buf: dict[str, dict] = field(default_factory=dict)
    # Output collectors.
    chunks: list[Chunk] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)
    pauses_ms: list[float] = field(default_factory=list)
    # Token usage (filled by message_start / message_delta on Anthropic, or by
    # `usage` field on the final OpenAI chunk when stream_options.include_usage=true).
    tokens_in: int | None = None
    tokens_out: int | None = None
    model: str | None = None
    finish_reason: str | None = None

    def now_offset_ms(self, now: float | None = None) -> float:
        return ((now if now is not None else time.time()) - self.ts_start) * 1000.0

    def emit(self, kind: str, *, text: str = "", tool_id: str = "", raw_event: str = "", now: float | None = None) -> None:
        ts = now if now is not None else time.time()
        offset = (ts - self.ts_start) * 1000.0
        # Pause detection (only for "content-ful" chunks, not for synthetic pauses).
        if kind in ("text", "tool_use", "tool_args") and self.last_chunk_ts > 0:
            gap_ms = (ts - self.last_chunk_ts) * 1000.0
            if gap_ms > PAUSE_THRESHOLD_MS:
                self.pauses_ms.append(gap_ms)
                self.chunks.append(Chunk(
                    seq=self.seq,
                    ts_offset_ms=offset,
                    kind="pause",
                    text=f"{gap_ms:.0f}ms",
                    raw_event="pause",
                ))
                self.seq += 1
        self.chunks.append(Chunk(
            seq=self.seq,
            ts_offset_ms=offset,
            kind=kind,
            text=text,
            tool_id=tool_id,
            raw_event=raw_event,
        ))
        self.seq += 1
        if kind in ("text", "tool_use", "tool_args"):
            self.last_chunk_ts = ts
            if kind == "text" and text:
                self.text_parts.append(text)

    def finalized_tool_calls(self) -> list[ToolCallRecord]:
        out: list[ToolCallRecord] = []
        for tid, info in self.tool_buf.items():
            args = info.get("arguments", "")
            parsed_ok = False
            if args:
                try:
                    json.loads(args)
                    parsed_ok = True
                except json.JSONDecodeError:
                    parsed_ok = False
            out.append(ToolCallRecord(
                tool_id=str(info.get("id", tid)),
                name=str(info.get("name", "")),
                arguments_json=args,
                parsed_ok=parsed_ok,
            ))
        return out


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def parse_sse_lines(lines: Iterable[tuple[float, bytes]], ts_start: float) -> ParseState:
    """Parse a sequence of (timestamp, raw_line_bytes) tuples.

    `lines` should be CRLF/LF-stripped individual lines as they arrive from the
    upstream. Empty lines act as SSE event delimiters (Anthropic style).
    """
    state = ParseState(ts_start=ts_start)
    for ts, raw in lines:
        try:
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
        except Exception:
            continue

        # OpenAI style: "data: {...json...}" or "data: [DONE]" (no `event:` header).
        # We handle both formats in a unified way: if line starts with `data: `
        # AND the buffer has no prior event name AND the JSON parses as an OpenAI
        # chunk shape, route to OpenAI handler. Else fall back to Anthropic-style
        # event-block buffering.
        if line == "":
            # End of an Anthropic-style event block.
            if state.cur_event_name or state.cur_data_lines:
                _flush_anthropic_event(state, ts)
            continue

        if line.startswith(":"):
            # SSE comment / keepalive. Ignore.
            continue

        if line.startswith("event:"):
            state.cur_event_name = line[len("event:"):].strip()
            continue

        if line.startswith("data:"):
            data = line[len("data:"):].lstrip()
            # OpenAI sentinel.
            if data == "[DONE]":
                state.emit("stop", raw_event="openai_done", now=ts)
                state.finish_reason = state.finish_reason or "stop"
                continue
            # Try OpenAI chunk shape first when no event name is set.
            if not state.cur_event_name:
                handled = _try_openai_chunk(state, data, ts)
                if handled:
                    continue
            # Otherwise buffer for the Anthropic event block.
            state.cur_data_lines.append(data)
            continue

        # Unknown line - ignore.
        continue

    # Drain any trailing buffered event.
    if state.cur_event_name or state.cur_data_lines:
        _flush_anthropic_event(state, ts_start)
    return state


# ---------------------------------------------------------------------------
# OpenAI handler
# ---------------------------------------------------------------------------


def _try_openai_chunk(state: ParseState, data: str, ts: float) -> bool:
    try:
        obj = json.loads(data)
    except json.JSONDecodeError:
        return False
    if not isinstance(obj, dict):
        return False
    if obj.get("object") != "chat.completion.chunk" and "choices" not in obj:
        return False

    state.model = state.model or obj.get("model")
    choices = obj.get("choices") or []
    for ch in choices:
        delta = (ch or {}).get("delta") or {}
        content = delta.get("content")
        if isinstance(content, str) and content:
            state.emit("text", text=content, raw_event="openai_delta", now=ts)
        for tc in delta.get("tool_calls") or []:
            idx = tc.get("index", 0)
            key = f"openai:{idx}"
            buf = state.tool_buf.setdefault(key, {"id": "", "name": "", "arguments": ""})
            if tc.get("id"):
                buf["id"] = tc["id"]
            fn = tc.get("function") or {}
            if fn.get("name"):
                buf["name"] = fn["name"]
                state.emit("tool_use", tool_id=buf["id"] or key, text=fn["name"], raw_event="openai_tool_name", now=ts)
            if fn.get("arguments"):
                buf["arguments"] += fn["arguments"]
                state.emit("tool_args", tool_id=buf["id"] or key, text=fn["arguments"], raw_event="openai_tool_args", now=ts)
        if ch.get("finish_reason"):
            state.finish_reason = ch["finish_reason"]
            state.emit("stop", raw_event=f"openai_finish:{ch['finish_reason']}", now=ts)

    # Usage may appear on the final chunk when include_usage=true.
    usage = obj.get("usage")
    if isinstance(usage, dict):
        state.tokens_in = usage.get("prompt_tokens", state.tokens_in)
        state.tokens_out = usage.get("completion_tokens", state.tokens_out)
    return True


# ---------------------------------------------------------------------------
# Anthropic handler
# ---------------------------------------------------------------------------


def _flush_anthropic_event(state: ParseState, ts: float) -> None:
    event_name = state.cur_event_name
    data_raw = "\n".join(state.cur_data_lines).strip()
    state.cur_event_name = ""
    state.cur_data_lines = []

    if not data_raw:
        return
    try:
        obj = json.loads(data_raw)
    except json.JSONDecodeError:
        return
    if not isinstance(obj, dict):
        return

    et = event_name or obj.get("type") or ""

    if et == "message_start":
        msg = obj.get("message") or {}
        state.model = state.model or msg.get("model")
        usage = msg.get("usage") or {}
        state.tokens_in = usage.get("input_tokens", state.tokens_in)
        return

    if et == "content_block_start":
        block = obj.get("content_block") or {}
        idx = obj.get("index", 0)
        if block.get("type") == "tool_use":
            tid = block.get("id") or f"anthropic:{idx}"
            state.tool_buf[str(idx)] = {
                "id": tid,
                "name": block.get("name", ""),
                "arguments": "",
            }
            state.emit("tool_use", tool_id=tid, text=block.get("name", ""), raw_event=et, now=ts)
        return

    if et == "content_block_delta":
        idx = str(obj.get("index", 0))
        delta = obj.get("delta") or {}
        dt = delta.get("type")
        if dt == "text_delta":
            text = delta.get("text", "")
            if text:
                state.emit("text", text=text, raw_event=et, now=ts)
        elif dt == "input_json_delta":
            partial = delta.get("partial_json", "")
            buf = state.tool_buf.get(idx)
            if buf is not None and partial:
                buf["arguments"] += partial
                state.emit("tool_args", tool_id=buf["id"], text=partial, raw_event=et, now=ts)
        return

    if et == "message_delta":
        usage = obj.get("usage") or {}
        if "output_tokens" in usage:
            state.tokens_out = usage["output_tokens"]
        delta = obj.get("delta") or {}
        if "stop_reason" in delta:
            state.finish_reason = delta["stop_reason"]
        return

    if et == "message_stop":
        state.emit("stop", raw_event=et, now=ts)
        return

    # content_block_stop / ping / etc. — ignored.
    return
