"""Interop: import/export between this project's Suite and external eval formats.

Two external ecosystems are supported, both stdlib-only:

- **PromptFoo** (https://promptfoo.dev) — config with `prompts`, `providers`,
  `tests`. We map prompts -> versions (system prompt), tests -> cases (user +
  keyword/schema assertions), the first provider -> upstream/model.
- **OpenAI Evals** — JSONL samples, one record per line, typically
  `{"input": [{"role","content"}...], "ideal": "..."}`. Each record becomes a
  case; the user content is the last user-role message, `ideal` becomes an
  expected keyword.

The goal is round-trippable, lossy-but-useful conversion — enough to run an
external suite through this project's runner and to hand a Suite back out.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .runner import Suite, SuiteCase, SuiteVersion, DEFAULT_UPSTREAMS, _yaml_load


# ---------------------------------------------------------------------------
# PromptFoo
# ---------------------------------------------------------------------------

_PROMPTFOO_PROVIDER_UPSTREAM = {
    "openai": "openai",
    "anthropic": "anthropic",
}


def _provider_to_upstream_model(provider: Any) -> tuple[str, str]:
    """Map a PromptFoo provider entry to (upstream, model).

    Accepts forms like "openai:gpt-4o-mini", "anthropic:claude-3-5-sonnet",
    or a dict {"id": "openai:gpt-4o-mini"}.
    """
    pid = provider.get("id") if isinstance(provider, dict) else provider
    pid = str(pid or "openai:gpt-4o-mini")
    head, _, tail = pid.partition(":")
    upstream = _PROMPTFOO_PROVIDER_UPSTREAM.get(head, head or "openai")
    model = tail or "gpt-4o-mini"
    return upstream, model


def _asserts_to_expectations(asserts: list[dict] | None) -> tuple[dict | None, list[str] | None]:
    """Map PromptFoo `assert` entries to (expect_schema, expect_keywords)."""
    if not asserts:
        return None, None
    schema: dict | None = None
    keywords: list[str] = []
    for a in asserts:
        atype = str(a.get("type") or "")
        value = a.get("value")
        if atype in ("is-json", "json-schema") and isinstance(value, dict):
            schema = value
        elif atype in ("contains", "icontains") and value is not None:
            keywords.append(str(value))
        elif atype == "contains-all" and isinstance(value, list):
            keywords.extend(str(v) for v in value)
    return schema, (keywords or None)


def import_promptfoo(path: str | Path) -> Suite:
    """Parse a PromptFoo config (YAML or JSON) into a Suite."""
    text = Path(path).expanduser().read_text(encoding="utf-8")
    data = _load_yaml_or_json(text)

    providers = data.get("providers") or ["openai:gpt-4o-mini"]
    upstream, model = _provider_to_upstream_model(providers[0])
    base_url = DEFAULT_UPSTREAMS.get(upstream, DEFAULT_UPSTREAMS["openai"])

    versions: list[SuiteVersion] = []
    for i, prompt in enumerate(data.get("prompts") or []):
        # PromptFoo prompts are usually the *user* template, but many configs put
        # the system instruction here. We treat each prompt as a version's system.
        text_val = prompt if isinstance(prompt, str) else str(prompt.get("raw") or prompt.get("label") or "")
        versions.append(SuiteVersion(id=f"v{i+1}", system=text_val, extra={}))
    if not versions:
        versions.append(SuiteVersion(id="v1", system="", extra={}))

    cases: list[SuiteCase] = []
    for i, test in enumerate(data.get("tests") or []):
        vars_ = test.get("vars") or {}
        user = vars_.get("input") or vars_.get("query") or vars_.get("text") or ""
        if not user and vars_:
            user = next(iter(vars_.values()))
        schema, keywords = _asserts_to_expectations(test.get("assert"))
        cases.append(SuiteCase(
            id=str(test.get("description") or f"case{i+1}"),
            user=str(user),
            expect_schema=schema,
            expect_keywords=keywords,
        ))

    return Suite(
        name=str(data.get("description") or "promptfoo-import"),
        upstream=upstream,
        base_url=base_url,
        model=model,
        temperature=0.0,
        max_tokens=512,
        versions=versions,
        cases=cases,
    )


def export_promptfoo(suite: Suite) -> dict:
    """Serialize a Suite into a PromptFoo-compatible config dict."""
    prompts = [v.system for v in suite.versions]
    tests = []
    for case in suite.cases:
        asserts: list[dict] = []
        if case.expect_schema:
            asserts.append({"type": "json-schema", "value": case.expect_schema})
        if case.expect_keywords:
            asserts.append({"type": "contains-all", "value": list(case.expect_keywords)})
        tests.append({
            "description": case.id,
            "vars": {"input": case.user},
            "assert": asserts,
        })
    return {
        "description": suite.name,
        "providers": [f"{suite.upstream}:{suite.model}"],
        "prompts": prompts,
        "tests": tests,
    }


# ---------------------------------------------------------------------------
# OpenAI Evals (JSONL samples)
# ---------------------------------------------------------------------------


def import_openai_evals(
    path: str | Path,
    *,
    name: str = "openai-evals-import",
    upstream: str = "openai",
    model: str = "gpt-4o-mini",
    system: str = "",
) -> Suite:
    """Parse an OpenAI Evals JSONL samples file into a Suite (single version).

    Each line is a JSON object. Recognized shapes:
      {"input": [{"role","content"}...], "ideal": "..."}
      {"input": "raw user text", "ideal": "..."}
    """
    cases: list[SuiteCase] = []
    for i, line in enumerate(Path(path).expanduser().read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        user = _extract_user_from_sample(rec.get("input"))
        ideal = rec.get("ideal")
        keywords = None
        if isinstance(ideal, str) and ideal:
            keywords = [ideal]
        elif isinstance(ideal, list) and ideal:
            keywords = [str(x) for x in ideal]
        cases.append(SuiteCase(
            id=f"sample{i+1}", user=user, expect_schema=None, expect_keywords=keywords
        ))

    return Suite(
        name=name,
        upstream=upstream,
        base_url=DEFAULT_UPSTREAMS.get(upstream, DEFAULT_UPSTREAMS["openai"]),
        model=model,
        temperature=0.0,
        max_tokens=512,
        versions=[SuiteVersion(id="v1", system=system, extra={})],
        cases=cases,
    )


def export_openai_evals(suite: Suite) -> list[dict]:
    """Serialize a Suite's cases into OpenAI Evals JSONL records (list of dicts)."""
    records: list[dict] = []
    for case in suite.cases:
        rec: dict[str, Any] = {
            "input": [{"role": "user", "content": case.user}],
        }
        if case.expect_keywords:
            rec["ideal"] = (
                case.expect_keywords[0]
                if len(case.expect_keywords) == 1
                else list(case.expect_keywords)
            )
        records.append(rec)
    return records


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _load_yaml_or_json(text: str) -> dict:
    stripped = text.lstrip()
    if stripped.startswith("{"):
        return json.loads(text)
    return _yaml_load(text)


def _extract_user_from_sample(inp: Any) -> str:
    if isinstance(inp, str):
        return inp
    if isinstance(inp, list):
        user_msgs = [m for m in inp if isinstance(m, dict) and m.get("role") == "user"]
        if user_msgs:
            return str(user_msgs[-1].get("content") or "")
        if inp and isinstance(inp[-1], dict):
            return str(inp[-1].get("content") or "")
    return ""
