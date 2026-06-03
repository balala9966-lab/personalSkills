"""Test eval interop: PromptFoo / OpenAI Evals import & export round-trips."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ai_obs_lab.eval import interop
from ai_obs_lab.eval.runner import Suite, SuiteCase, SuiteVersion


_PROMPTFOO_JSON = {
    "description": "extract-suite",
    "providers": ["openai:gpt-4o-mini"],
    "prompts": ["Extract fields as JSON.", "Return ONLY a JSON object."],
    "tests": [
        {
            "description": "case-john",
            "vars": {"input": "John, 29, lives in Hangzhou."},
            "assert": [
                {"type": "contains-all", "value": ["Hangzhou", "John"]},
                {"type": "json-schema", "value": {"type": "object",
                                                  "required": ["name", "age"]}},
            ],
        },
        {
            "description": "case-lily",
            "vars": {"input": "Lily is 34 in Shanghai."},
            "assert": [{"type": "contains", "value": "Shanghai"}],
        },
    ],
}


class TestPromptFooImport(unittest.TestCase):
    def test_import_from_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "pf.json"
            p.write_text(json.dumps(_PROMPTFOO_JSON))
            suite = interop.import_promptfoo(p)
        self.assertEqual(suite.name, "extract-suite")
        self.assertEqual(suite.upstream, "openai")
        self.assertEqual(suite.model, "gpt-4o-mini")
        self.assertEqual([v.id for v in suite.versions], ["v1", "v2"])
        self.assertEqual(suite.versions[0].system, "Extract fields as JSON.")
        self.assertEqual([c.id for c in suite.cases], ["case-john", "case-lily"])
        john = suite.cases[0]
        self.assertEqual(john.user, "John, 29, lives in Hangzhou.")
        self.assertEqual(john.expect_keywords, ["Hangzhou", "John"])
        self.assertEqual(john.expect_schema["required"], ["name", "age"])
        self.assertEqual(suite.cases[1].expect_keywords, ["Shanghai"])

    def test_provider_dict_form(self) -> None:
        cfg = dict(_PROMPTFOO_JSON)
        cfg["providers"] = [{"id": "anthropic:claude-3-5-sonnet"}]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "pf.json"
            p.write_text(json.dumps(cfg))
            suite = interop.import_promptfoo(p)
        self.assertEqual(suite.upstream, "anthropic")
        self.assertEqual(suite.model, "claude-3-5-sonnet")


class TestPromptFooExport(unittest.TestCase):
    def test_export_shape(self) -> None:
        suite = Suite(
            name="s", upstream="openai", base_url="x", model="gpt-4o-mini",
            temperature=0.0, max_tokens=256,
            versions=[SuiteVersion(id="v1", system="sys-a", extra={})],
            cases=[SuiteCase(id="c1", user="hi",
                             expect_schema={"type": "object"},
                             expect_keywords=["a", "b"])],
        )
        cfg = interop.export_promptfoo(suite)
        self.assertEqual(cfg["providers"], ["openai:gpt-4o-mini"])
        self.assertEqual(cfg["prompts"], ["sys-a"])
        test = cfg["tests"][0]
        self.assertEqual(test["vars"]["input"], "hi")
        atypes = {a["type"] for a in test["assert"]}
        self.assertEqual(atypes, {"json-schema", "contains-all"})

    def test_export_then_import_preserves_cases(self) -> None:
        suite = Suite(
            name="rt", upstream="openai", base_url="x", model="gpt-4o-mini",
            temperature=0.0, max_tokens=256,
            versions=[SuiteVersion(id="v1", system="sys", extra={})],
            cases=[SuiteCase(id="c1", user="hello world",
                             expect_schema=None, expect_keywords=["world"])],
        )
        cfg = interop.export_promptfoo(suite)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "pf.json"
            p.write_text(json.dumps(cfg))
            back = interop.import_promptfoo(p)
        self.assertEqual([c.user for c in back.cases], ["hello world"])
        self.assertEqual(back.cases[0].expect_keywords, ["world"])


class TestOpenAIEvals(unittest.TestCase):
    def test_import_messages_form(self) -> None:
        samples = [
            {"input": [{"role": "system", "content": "be terse"},
                       {"role": "user", "content": "capital of France?"}],
             "ideal": "Paris"},
            {"input": "raw text question", "ideal": ["a", "b"]},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "samples.jsonl"
            p.write_text("\n".join(json.dumps(s) for s in samples))
            suite = interop.import_openai_evals(p, model="gpt-4o-mini")
        self.assertEqual(len(suite.cases), 2)
        self.assertEqual(suite.cases[0].user, "capital of France?")
        self.assertEqual(suite.cases[0].expect_keywords, ["Paris"])
        self.assertEqual(suite.cases[1].user, "raw text question")
        self.assertEqual(suite.cases[1].expect_keywords, ["a", "b"])

    def test_export_records(self) -> None:
        suite = Suite(
            name="s", upstream="openai", base_url="x", model="gpt-4o-mini",
            temperature=0.0, max_tokens=256,
            versions=[SuiteVersion(id="v1", system="", extra={})],
            cases=[
                SuiteCase(id="c1", user="q1", expect_schema=None,
                          expect_keywords=["only"]),
                SuiteCase(id="c2", user="q2", expect_schema=None,
                          expect_keywords=["x", "y"]),
            ],
        )
        records = interop.export_openai_evals(suite)
        self.assertEqual(records[0]["input"], [{"role": "user", "content": "q1"}])
        self.assertEqual(records[0]["ideal"], "only")
        self.assertEqual(records[1]["ideal"], ["x", "y"])

    def test_import_skips_malformed_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "samples.jsonl"
            p.write_text('{"input":"ok","ideal":"z"}\nNOT JSON\n\n')
            suite = interop.import_openai_evals(p)
        self.assertEqual(len(suite.cases), 1)
        self.assertEqual(suite.cases[0].user, "ok")


if __name__ == "__main__":
    unittest.main()
