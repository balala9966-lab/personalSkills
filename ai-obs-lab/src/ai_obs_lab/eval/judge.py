"""LLM-as-Judge: score each (version, case, repeat) output on a 4-axis rubric.

Default rubric (1-5 each):
  correctness  — does it answer the user's request?
  format       — does it follow requested format / schema?
  conciseness  — no rambling or filler.
  faithfulness — no fabrication beyond input.

Scores + rationale are stored as JudgeResult rows; the dashboard renders them
alongside the objective metrics. Judge calls are made directly to the upstream
(no proxy), parallelism is sequential to keep things deterministic.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from urllib import error as urlerror
from urllib import request as urlrequest

from ..core.models import EvalRun, JudgeResult
from ..core.store import JSONLStore

DEFAULT_RUBRIC = ("correctness", "format", "conciseness", "faithfulness")

JUDGE_SYSTEM = (
    "You are a strict evaluator. Given a USER prompt and a MODEL OUTPUT, score "
    "the output on four 1-5 dimensions: correctness, format, conciseness, "
    "faithfulness. 5 = excellent, 1 = unacceptable. Be terse. "
    "Respond with ONLY a JSON object of the form: "
    '{"correctness":N,"format":N,"conciseness":N,"faithfulness":N,"rationale":"..."} '
    "No markdown fences. No prose outside the JSON."
)


def judge_eval_run(
    er: EvalRun,
    *,
    store: JSONLStore,
    judge_model: str = "openai:gpt-4o-mini",
    user_inputs_by_case: dict[str, str] | None = None,
) -> list[JudgeResult]:
    """Score every output in an EvalRun and persist JudgeResults."""
    results: list[JudgeResult] = []
    user_inputs_by_case = user_inputs_by_case or {}
    for r in er.results:
        user_text = user_inputs_by_case.get(r.case_id, "")
        for i, out in enumerate(r.outputs):
            trace_id = r.trace_ids[i] if i < len(r.trace_ids) else ""
            scores, rationale = _call_judge(judge_model, user_text, out)
            overall = sum(scores.get(k, 0) for k in DEFAULT_RUBRIC) / float(len(DEFAULT_RUBRIC))
            jr = JudgeResult(
                judge_id=f"jr-{uuid.uuid4().hex[:10]}",
                trace_id=trace_id,
                eval_run_id=er.eval_run_id,
                version_id=r.version_id,
                case_id=r.case_id,
                judge_model=judge_model,
                rubric={k: int(scores.get(k, 0)) for k in DEFAULT_RUBRIC},
                overall=round(overall, 3),
                rationale=rationale,
                ts=time.time(),
            )
            try:
                store.append_judge_result(jr)
            except Exception as e:
                sys.stderr.write(f"[judge] persist failed: {e}\n")
            results.append(jr)
    return results


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _call_judge(judge_model: str, user_text: str, output: str) -> tuple[dict, str]:
    """Call the configured judge model and return (rubric_dict, rationale)."""
    provider, _, model = judge_model.partition(":")
    if not model:
        provider, model = "openai", judge_model

    prompt = (
        f"USER PROMPT:\n{user_text or '(not provided)'}\n\n"
        f"MODEL OUTPUT:\n{output}\n"
    )

    try:
        if provider == "anthropic":
            raw = _post_anthropic(model, JUDGE_SYSTEM, prompt)
        else:
            raw = _post_openai(model, JUDGE_SYSTEM, prompt)
    except Exception as e:
        return {k: 0 for k in DEFAULT_RUBRIC}, f"judge_error: {e}"

    obj = _safe_json(raw)
    if not isinstance(obj, dict):
        return {k: 0 for k in DEFAULT_RUBRIC}, f"unparseable judge response: {raw[:200]}"
    scores = {k: _clip15(obj.get(k)) for k in DEFAULT_RUBRIC}
    rationale = str(obj.get("rationale") or "")[:1000]
    return scores, rationale


def _clip15(v) -> int:
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        return 0
    return max(1, min(5, n))


def _post_openai(model: str, system: str, user: str) -> str:
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com").rstrip("/")
    if "/v1" not in base:
        base = base + "/v1"
    url = f"{base}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if os.environ.get("OPENAI_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['OPENAI_API_KEY']}"
    payload = {
        "model": model,
        "temperature": 0.0,
        "max_tokens": 256,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    return _http_post_text(url, headers, payload)


def _post_anthropic(model: str, system: str, user: str) -> str:
    base = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
    url = f"{base}/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    if os.environ.get("ANTHROPIC_API_KEY"):
        headers["x-api-key"] = os.environ["ANTHROPIC_API_KEY"]
    payload = {
        "model": model,
        "max_tokens": 256,
        "temperature": 0.0,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    return _http_post_text(url, headers, payload)


def _http_post_text(url: str, headers: dict, payload: dict) -> str:
    req = urlrequest.Request(url, data=json.dumps(payload).encode("utf-8"),
                             method="POST", headers=headers)
    try:
        with urlrequest.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urlerror.HTTPError as he:
        raw = (he.read() if hasattr(he, "read") else b"").decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {he.code}: {raw[:300]}")
    return _extract_first_text(raw)


def _extract_first_text(raw: str) -> str:
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    # OpenAI
    choices = obj.get("choices") or []
    if choices and isinstance(choices[0], dict):
        return (choices[0].get("message") or {}).get("content") or raw
    # Anthropic
    parts = []
    for blk in obj.get("content") or []:
        if isinstance(blk, dict) and blk.get("type") == "text":
            parts.append(blk.get("text", ""))
    return "".join(parts) or raw


def _safe_json(text: str):
    if not text:
        return None
    t = text.strip()
    fence = re.match(r"^```(?:json)?\s*([\s\S]+?)\s*```\s*$", t)
    if fence:
        t = fence.group(1)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        # find first balanced object
        depth = 0
        in_str = False
        esc = False
        start = t.find("{")
        if start < 0:
            return None
        for i in range(start, len(t)):
            c = t[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(t[start: i + 1])
                    except json.JSONDecodeError:
                        return None
        return None
