"""Objective metrics for prompt/skill A/B evaluation.

All functions are pure: input strings/lists -> floats. No I/O, no LLM calls.

The schema validator is a deliberately tiny subset (type / required / properties
/ items / enum) — enough for "did the model produce JSON with the right keys?"
without dragging in jsonschema as a dependency.
"""

from __future__ import annotations

import json
import math
import re
from difflib import SequenceMatcher
from typing import Any

# ---------------------------------------------------------------------------
# Similarity / variance
# ---------------------------------------------------------------------------


def pairwise_similarity_variance(outputs: list[str]) -> float | None:
    """Return 1 - mean pairwise SequenceMatcher ratio over all unordered pairs.

    Interpretation: 0.0 == identical outputs (perfectly stable prompt),
    1.0 == completely dissimilar. Returns None if <2 outputs.
    """
    if not outputs or len(outputs) < 2:
        return None
    n = len(outputs)
    total = 0.0
    pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            sm = SequenceMatcher(None, outputs[i] or "", outputs[j] or "")
            total += sm.ratio()
            pairs += 1
    if pairs == 0:
        return None
    mean_ratio = total / pairs
    return max(0.0, min(1.0, 1.0 - mean_ratio))


# ---------------------------------------------------------------------------
# Schema compliance (tiny JSON Schema subset)
# ---------------------------------------------------------------------------


def schema_compliance_rate(outputs: list[str], schema: dict | None) -> float | None:
    """Fraction of outputs whose extracted JSON validates against `schema`."""
    if not outputs:
        return None
    if not schema:
        return None
    ok = 0
    for out in outputs:
        obj = _extract_json(out)
        if obj is None:
            continue
        if _validate(obj, schema):
            ok += 1
    return ok / len(outputs)


def _extract_json(text: str) -> Any:
    """Try strict JSON first, then look for the first balanced {...} or [...]."""
    if text is None:
        return None
    t = text.strip()
    if not t:
        return None
    # Strip markdown fences if present.
    fence = re.match(r"^```(?:json)?\s*([\s\S]+?)\s*```\s*$", t)
    if fence:
        t = fence.group(1)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    # Find first balanced JSON object or array.
    for opener, closer in (("{", "}"), ("[", "]")):
        start = t.find(opener)
        if start < 0:
            continue
        depth = 0
        in_str = False
        esc = False
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
            if c == opener:
                depth += 1
            elif c == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(t[start : i + 1])
                    except json.JSONDecodeError:
                        break
    return None


def _validate(obj: Any, schema: dict) -> bool:
    """Tiny JSON Schema subset validator."""
    t = schema.get("type")
    if t == "object":
        if not isinstance(obj, dict):
            return False
        for req in schema.get("required") or []:
            if req not in obj:
                return False
        for key, sub in (schema.get("properties") or {}).items():
            if key in obj and not _validate(obj[key], sub):
                return False
        return True
    if t == "array":
        if not isinstance(obj, list):
            return False
        items_schema = schema.get("items")
        if items_schema:
            return all(_validate(it, items_schema) for it in obj)
        return True
    if t == "string":
        if not isinstance(obj, str):
            return False
    elif t == "integer":
        if not (isinstance(obj, int) and not isinstance(obj, bool)):
            return False
    elif t == "number":
        if not (isinstance(obj, (int, float)) and not isinstance(obj, bool)):
            return False
    elif t == "boolean":
        if not isinstance(obj, bool):
            return False
    elif t == "null":
        if obj is not None:
            return False
    # enum constraint
    enum = schema.get("enum")
    if enum is not None and obj not in enum:
        return False
    return True


# ---------------------------------------------------------------------------
# Keyword hit rate
# ---------------------------------------------------------------------------


def keyword_hit_rate(outputs: list[str], keywords: list[str] | None) -> float | None:
    """Fraction of outputs that contain ALL given keywords (case-insensitive)."""
    if not outputs:
        return None
    if not keywords:
        return None
    kws = [k.lower() for k in keywords if k]
    if not kws:
        return None
    ok = 0
    for out in outputs:
        low = (out or "").lower()
        if all(k in low for k in kws):
            ok += 1
    return ok / len(outputs)


# ---------------------------------------------------------------------------
# Logprob top-1 average
# ---------------------------------------------------------------------------


def avg_logprob_top1(logprobs_lists: list[list[float]] | None) -> float | None:
    """Convert list of per-token logprob lists to mean top-1 probability.

    Input shape: outer list = one entry per generated response, inner list =
    chosen-token logprobs for each token in that response. Returns the mean of
    exp(logprob) across all tokens across all responses.
    """
    if not logprobs_lists:
        return None
    total = 0.0
    n = 0
    for seq in logprobs_lists:
        for lp in seq or []:
            try:
                total += math.exp(float(lp))
                n += 1
            except (TypeError, ValueError, OverflowError):
                continue
    if n == 0:
        return None
    return total / n
