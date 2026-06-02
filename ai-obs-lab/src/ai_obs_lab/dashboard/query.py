"""Pure data query layer for the dashboard.

This module is the abstraction boundary between storage and view. Phase 2's
FastAPI service should depend on `query.py` and not on `html.py` or `store.py`
directly. All functions return plain dicts / dataclasses (JSON-serializable).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import Any, Iterable

from ..core.models import EvalRun, JudgeResult, TraceFull, TraceSummary
from ..core.store import JSONLStore


# ---------------------------------------------------------------------------
# Trace queries
# ---------------------------------------------------------------------------


def list_traces(
    store: JSONLStore,
    *,
    start: date | None = None,
    end: date | None = None,
    client: str | None = None,
    upstream: str | None = None,
    limit: int | None = None,
) -> list[TraceSummary]:
    """Return trace summaries in time-descending order with optional filters."""
    items: list[TraceSummary] = []
    for s in store.iter_summaries(start=start, end=end):
        if client and s.client_hint != client:
            continue
        if upstream and s.upstream != upstream:
            continue
        items.append(s)
    items.sort(key=lambda s: s.ts_start, reverse=True)
    if limit is not None:
        items = items[:limit]
    return items


def get_trace_detail(store: JSONLStore, trace_id: str, ts: float | None = None) -> TraceFull:
    return store.load_trace(trace_id, ts=ts)


def trace_overview(traces: Iterable[TraceSummary]) -> dict[str, Any]:
    """Aggregate counters across a list of trace summaries."""
    by_client: Counter = Counter()
    by_upstream: Counter = Counter()
    by_model: Counter = Counter()
    errors = 0
    total = 0
    ttft_vals: list[float] = []
    tok_in: int = 0
    tok_out: int = 0
    tool_calls = 0
    for t in traces:
        total += 1
        by_client[t.client_hint or "unknown"] += 1
        by_upstream[t.upstream or "unknown"] += 1
        if t.model:
            by_model[t.model] += 1
        if t.error or (t.status is not None and not (200 <= t.status < 300)):
            errors += 1
        if t.ttft_ms is not None:
            ttft_vals.append(t.ttft_ms)
        if t.tokens_in:
            tok_in += int(t.tokens_in)
        if t.tokens_out:
            tok_out += int(t.tokens_out)
        tool_calls += int(t.tool_call_count or 0)
    return {
        "total": total,
        "errors": errors,
        "by_client": dict(by_client),
        "by_upstream": dict(by_upstream),
        "by_model": dict(by_model.most_common(10)),
        "avg_ttft_ms": (sum(ttft_vals) / len(ttft_vals)) if ttft_vals else None,
        "tokens_in_total": tok_in,
        "tokens_out_total": tok_out,
        "tool_call_total": tool_calls,
    }


# ---------------------------------------------------------------------------
# Eval queries
# ---------------------------------------------------------------------------


def list_eval_runs(
    store: JSONLStore,
    *,
    start: date | None = None,
    end: date | None = None,
    suite_name: str | None = None,
) -> list[EvalRun]:
    runs = []
    for er in store.iter_eval_runs(start=start, end=end):
        if suite_name and er.suite_name != suite_name:
            continue
        runs.append(er)
    runs.sort(key=lambda e: e.ts_start, reverse=True)
    return runs


def compare_eval_versions(er: EvalRun) -> dict[str, Any]:
    """Pivot an EvalRun into a per-case version comparison table."""
    table: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for r in er.results:
        table[r.case_id][r.version_id] = {
            "similarity_variance": r.similarity_variance,
            "schema_compliance_rate": r.schema_compliance_rate,
            "keyword_hit_rate": r.keyword_hit_rate,
            "avg_logprob_top1": r.avg_logprob_top1,
            "avg_ttft_ms": r.avg_ttft_ms,
            "avg_total_ms": r.avg_total_ms,
            "avg_tokens_out": r.avg_tokens_out,
            "errors": r.errors,
            "sample_outputs": r.outputs[:3],
            "trace_ids": r.trace_ids,
        }
    return {
        "eval_run_id": er.eval_run_id,
        "suite_name": er.suite_name,
        "model": er.model,
        "temperature": er.temperature,
        "repeat": er.repeat,
        "version_ids": er.version_ids,
        "case_ids": er.case_ids,
        "table": {k: dict(v) for k, v in table.items()},
    }


# ---------------------------------------------------------------------------
# Tool / MCP aggregation
# ---------------------------------------------------------------------------


def aggregate_tool_calls(
    store: JSONLStore,
    *,
    start: date | None = None,
    end: date | None = None,
    max_traces: int = 500,
) -> dict[str, dict[str, Any]]:
    """Group tool calls by tool name, with frequency, parse-success rate, and a sample.

    To stay cheap we scan summaries first, then only `load_trace` for those with
    `tool_call_count > 0`, capped at `max_traces`.
    """
    grouped: dict[str, dict[str, Any]] = {}
    loaded = 0
    for s in sorted(store.iter_summaries(start=start, end=end),
                    key=lambda x: x.ts_start, reverse=True):
        if not s.tool_call_count:
            continue
        if loaded >= max_traces:
            break
        try:
            tf = store.load_trace(s.trace_id, ts=s.ts_start)
        except FileNotFoundError:
            continue
        loaded += 1
        for tc in tf.tool_calls:
            slot = grouped.setdefault(tc.name or "<unknown>", {
                "count": 0,
                "parsed_ok": 0,
                "parsed_fail": 0,
                "sample_arguments": [],
                "sample_trace_ids": [],
            })
            slot["count"] += 1
            if tc.parsed_ok:
                slot["parsed_ok"] += 1
            else:
                slot["parsed_fail"] += 1
            if len(slot["sample_arguments"]) < 3:
                slot["sample_arguments"].append(tc.arguments_json[:400])
            if len(slot["sample_trace_ids"]) < 5:
                slot["sample_trace_ids"].append(tf.summary.trace_id)
    return grouped


# ---------------------------------------------------------------------------
# Request context parsing —— 把"模型看到的完整上下文"拆开
# ---------------------------------------------------------------------------
#
# 这是理解 skill / MCP 工作原理的核心视图。一次请求里，模型实际"看到"的东西
# 远不止你打的那句话，而是：
#   1. system prompt（产品/工具注入的人设、规则、CLAUDE.md 等）
#   2. tools 菜单（每个 skill / MCP 工具的 name + description + JSON Schema，
#      这些被 Claude Code / cfuse 悄悄塞进请求，模型据此决定调用谁）
#   3. 历史消息（user / assistant / tool_result，token 主要被这部分吃掉）
#
# 把它们拆开 + 估算各自的 token 占比，你就能直观看到"上下文是怎么被填满的"。


def _estimate_tokens(text: str) -> int:
    """粗略 token 估算（无第三方依赖）。

    经验值：英文约 4 字符/token，中文约 1.5 字符/token。这里取混合近似：
    ascii 字符按 /4，非 ascii（主要中文）按 /1.5，足够看占比趋势。
    """
    if not text:
        return 0
    ascii_chars = sum(1 for ch in text if ord(ch) < 128)
    other_chars = len(text) - ascii_chars
    return int(ascii_chars / 4 + other_chars / 1.5) + 1


def _text_of(content: Any) -> str:
    """把 Anthropic/OpenAI 的 content（可能是 str 或 block 数组）拍平成纯文本。"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                t = block.get("type")
                if t == "text":
                    parts.append(str(block.get("text", "")))
                elif t == "tool_use":
                    parts.append(f"[tool_use {block.get('name')} input={json_dumps_safe(block.get('input'))}]")
                elif t == "tool_result":
                    parts.append(f"[tool_result {_text_of(block.get('content'))}]")
                elif t == "thinking":
                    parts.append(str(block.get("thinking", "")))
                else:
                    parts.append(json_dumps_safe(block))
        return "\n".join(parts)
    return str(content)


def json_dumps_safe(obj: Any, limit: int = 600) -> str:
    import json
    try:
        s = json.dumps(obj, ensure_ascii=False)
    except Exception:
        s = str(obj)
    return s if len(s) <= limit else s[:limit] + "…"


def _guess_tool_origin(name: str, description: str) -> str:
    """根据工具名/描述猜测它来自 skill 还是 MCP 还是内置工具。

    纯启发式，给你一个快速分类视角，不保证 100% 准确：
    - MCP 工具名常带 'mcp__<server>__<tool>' 前缀（Claude Code 约定）
    - skill 触发通常是内置 Skill 工具或 slash command
    - 其余按内置工具（Read/Write/Bash/Edit/Grep...）匹配
    """
    n = (name or "").lower()
    if n.startswith("mcp__") or "mcp" in n.split("__")[0:1]:
        # mcp__server__tool -> 提取 server
        parts = name.split("__")
        server = parts[1] if len(parts) >= 2 else "?"
        return f"MCP({server})"
    builtin = {"read", "write", "edit", "bash", "grep", "glob", "ls",
               "webfetch", "websearch", "task", "todowrite", "notebookedit"}
    if n in builtin:
        return "builtin"
    if "skill" in n or n.startswith("slash"):
        return "skill"
    return "other"


def parse_request_context(request_body: Any) -> dict[str, Any]:
    """把请求体拆成 system / tools / messages 三层，并估算各自 token 占比。

    支持 Anthropic Messages API 与 OpenAI Chat Completions 两种格式。
    返回结构对 dashboard 友好（全部 JSON 可序列化）。
    """
    if not isinstance(request_body, dict):
        return {"available": False, "reason": "request body is not a JSON object"}

    # --- system prompt ---
    system_text = ""
    sys_raw = request_body.get("system")
    if sys_raw is not None:
        system_text = _text_of(sys_raw)
    else:
        # OpenAI 风格：messages 里 role=system
        for m in request_body.get("messages", []) or []:
            if isinstance(m, dict) and m.get("role") == "system":
                system_text += _text_of(m.get("content")) + "\n"
    system_text = system_text.strip()

    # --- tools 菜单（skill / MCP 暴露给模型的"菜单"）---
    tools_out: list[dict[str, Any]] = []
    raw_tools = request_body.get("tools") or []
    for t in raw_tools:
        if not isinstance(t, dict):
            continue
        # Anthropic: {name, description, input_schema}
        # OpenAI: {type:function, function:{name, description, parameters}}
        if t.get("type") == "function" and isinstance(t.get("function"), dict):
            fn = t["function"]
            name = fn.get("name", "")
            desc = fn.get("description", "")
            schema = fn.get("parameters")
        else:
            name = t.get("name", "")
            desc = t.get("description", "")
            schema = t.get("input_schema")
        schema_str = json_dumps_safe(schema, limit=4000)
        tools_out.append({
            "name": name,
            "origin": _guess_tool_origin(name, desc),
            "description": desc,
            "description_tokens": _estimate_tokens(desc),
            "schema": schema_str,
            "schema_tokens": _estimate_tokens(schema_str),
        })

    # --- messages 分层 ---
    messages_out: list[dict[str, Any]] = []
    for idx, m in enumerate(request_body.get("messages", []) or []):
        if not isinstance(m, dict):
            continue
        role = m.get("role", "?")
        if role == "system":
            continue  # 已并入 system
        content = m.get("content")
        text = _text_of(content)
        has_tool_use = False
        has_tool_result = False
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict):
                    if b.get("type") == "tool_use":
                        has_tool_use = True
                    if b.get("type") == "tool_result":
                        has_tool_result = True
        messages_out.append({
            "index": idx,
            "role": role,
            "tokens": _estimate_tokens(text),
            "chars": len(text),
            "has_tool_use": has_tool_use,
            "has_tool_result": has_tool_result,
            "preview": text[:500] + ("…" if len(text) > 500 else ""),
        })

    # --- token 占比汇总 ---
    sys_tokens = _estimate_tokens(system_text)
    tools_tokens = sum(t["description_tokens"] + t["schema_tokens"] for t in tools_out)
    msg_tokens = sum(m["tokens"] for m in messages_out)
    total = sys_tokens + tools_tokens + msg_tokens or 1

    return {
        "available": True,
        "model": request_body.get("model"),
        "system": {
            "tokens": sys_tokens,
            "chars": len(system_text),
            "text": system_text,
        },
        "tools": tools_out,
        "tools_count": len(tools_out),
        "messages": messages_out,
        "messages_count": len(messages_out),
        "token_breakdown": {
            "system": sys_tokens,
            "tools": tools_tokens,
            "messages": msg_tokens,
            "total_estimated": total,
            "system_pct": round(100 * sys_tokens / total, 1),
            "tools_pct": round(100 * tools_tokens / total, 1),
            "messages_pct": round(100 * msg_tokens / total, 1),
        },
    }


# ---------------------------------------------------------------------------
# Judge aggregation
# ---------------------------------------------------------------------------


def aggregate_judge_for_run(
    store: JSONLStore, eval_run_id: str, *, around: date | None = None
) -> dict[str, dict[str, dict[str, float]]]:
    """Average judge scores per (case_id -> version_id -> rubric)."""
    sums: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    # Scan a small window around 'around' date (default: today and yesterday).
    today = around or date.today()
    days = [today, today - timedelta(days=1)]
    for d in days:
        for jr in store.iter_judge_results(start=d, end=d):
            if jr.eval_run_id != eval_run_id:
                continue
            case_id = jr.case_id or "?"
            ver_id = jr.version_id or "?"
            for k, v in jr.rubric.items():
                sums[case_id][ver_id][k].append(float(v))
            sums[case_id][ver_id]["overall"].append(float(jr.overall))
    out: dict[str, dict[str, dict[str, float]]] = {}
    for case_id, vers in sums.items():
        out[case_id] = {}
        for ver_id, axes in vers.items():
            out[case_id][ver_id] = {
                k: (sum(vs) / len(vs)) if vs else 0.0 for k, vs in axes.items()
            }
    return out


# ---------------------------------------------------------------------------
# Convenience: a single "dashboard snapshot" payload
# ---------------------------------------------------------------------------


def dashboard_snapshot(
    store: JSONLStore,
    *,
    start: date | None = None,
    end: date | None = None,
    trace_limit: int = 200,
) -> dict[str, Any]:
    summaries = list_traces(store, start=start, end=end, limit=trace_limit)
    eval_runs = list_eval_runs(store, start=start, end=end)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "range": {
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
        },
        "overview": trace_overview(summaries),
        "traces": [asdict(s) for s in summaries],
        "eval_runs": [
            {
                "meta": {
                    "eval_run_id": er.eval_run_id,
                    "suite_name": er.suite_name,
                    "model": er.model,
                    "temperature": er.temperature,
                    "repeat": er.repeat,
                    "ts_start": er.ts_start,
                },
                "compare": compare_eval_versions(er),
                "judge": aggregate_judge_for_run(store, er.eval_run_id, around=end or date.today()),
            }
            for er in eval_runs
        ],
        "tools": aggregate_tool_calls(store, start=start, end=end),
    }
