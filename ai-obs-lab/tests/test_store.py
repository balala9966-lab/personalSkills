"""Test JSONLStore: write/read round-trip and large-body sidecar offload."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path

from ai_obs_lab.core.models import (
    Chunk,
    EvalCaseResult,
    EvalRun,
    JudgeResult,
    ToolCallRecord,
    TraceFull,
    TraceSummary,
)
from ai_obs_lab.core.store import JSONLStore, LARGE_BODY_BYTES


def _mk_summary(trace_id: str, ts: float | None = None, **overrides) -> TraceSummary:
    base = dict(
        trace_id=trace_id,
        ts_start=ts or time.time(),
        client_hint="claude-code",
        upstream="anthropic",
        method="POST",
        path="/v1/messages",
        model="claude-3-5-sonnet",
        status=200,
        ttft_ms=100.0,
        total_ms=500.0,
        tokens_in=10,
        tokens_out=20,
        chunks=3,
        tool_call_count=1,
    )
    base.update(overrides)
    return TraceSummary(**base)


class TestJSONLStore(unittest.TestCase):
    def test_summary_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = JSONLStore(tmp)
            s1 = _mk_summary("t-aaa")
            s2 = _mk_summary("t-bbb", ts=s1.ts_start + 1)
            store.append_summary(s1)
            store.append_summary(s2)

            today = date.today()
            got = list(store.iter_summaries(start=today, end=today))
            ids = sorted(x.trace_id for x in got)
            self.assertEqual(ids, ["t-aaa", "t-bbb"])

    def test_trace_round_trip_with_chunks_and_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = JSONLStore(tmp)
            s = _mk_summary("t-1")
            tf = TraceFull(
                summary=s,
                request_headers={"x-api-key": "sha256:abcd1234"},
                request_body={"model": "claude-3-5-sonnet", "messages": [{"role": "user", "content": "hi"}]},
                response_headers={"content-type": "text/event-stream"},
                response_text="hello world",
                chunks=[
                    Chunk(seq=0, ts_offset_ms=50, kind="text", text="hello"),
                    Chunk(seq=1, ts_offset_ms=1200, kind="pause", text="1150ms"),
                    Chunk(seq=2, ts_offset_ms=1210, kind="text", text=" world"),
                ],
                tool_calls=[
                    ToolCallRecord(tool_id="call_1", name="Read",
                                   arguments_json='{"path":"x"}', parsed_ok=True),
                ],
                pauses_ms=[1150.0],
            )
            store.write_trace(tf)
            store.append_summary(s)

            loaded = store.load_trace("t-1", ts=s.ts_start)
            self.assertEqual(loaded.summary.trace_id, "t-1")
            self.assertEqual(loaded.response_text, "hello world")
            self.assertEqual(len(loaded.chunks), 3)
            self.assertEqual(loaded.tool_calls[0].name, "Read")
            self.assertEqual(loaded.pauses_ms, [1150.0])
            # Headers preserved
            self.assertEqual(loaded.request_headers["x-api-key"], "sha256:abcd1234")
            # Body kept inline (small)
            self.assertIsNone(loaded.request_body_ref)
            self.assertEqual(loaded.request_body["model"], "claude-3-5-sonnet")

    def test_large_body_offloaded_to_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = JSONLStore(tmp)
            s = _mk_summary("t-big")
            # Build a body that JSON-encodes to > 256KB.
            big_text = "x" * (LARGE_BODY_BYTES + 1024)
            tf = TraceFull(
                summary=s,
                request_body={"messages": [{"role": "user", "content": big_text}]},
            )
            store.write_trace(tf)

            # Sidecar file must exist.
            day = date.today().strftime("%Y-%m-%d")
            traces_dir = Path(tmp) / day / "traces"
            sidecar = traces_dir / "t-big.body.json"
            self.assertTrue(sidecar.exists())
            # Reload should hydrate the body back in via the ref.
            loaded = store.load_trace("t-big", ts=s.ts_start)
            self.assertIsNotNone(loaded.request_body_ref)
            self.assertIsNotNone(loaded.request_body)
            self.assertEqual(
                loaded.request_body["messages"][0]["content"], big_text
            )

    def test_eval_run_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = JSONLStore(tmp)
            er = EvalRun(
                eval_run_id="er-xyz",
                ts_start=time.time(),
                suite_name="demo",
                suite_path="",
                upstream="openai",
                model="gpt-4o-mini",
                temperature=0.8,
                repeat=2,
                version_ids=["v1", "v2"],
                case_ids=["c1"],
                results=[
                    EvalCaseResult(
                        version_id="v1", case_id="c1", repeats=2,
                        trace_ids=["eval-er-xyz-v1-c1-0"],
                        outputs=["{}", "{}"],
                        similarity_variance=0.0,
                        schema_compliance_rate=1.0,
                        keyword_hit_rate=None,
                        avg_logprob_top1=None,
                        avg_ttft_ms=120.0,
                        avg_total_ms=800.0,
                        avg_tokens_out=42.0,
                        errors=0,
                    ),
                ],
            )
            store.append_eval_run(er)
            got = list(store.iter_eval_runs())
            self.assertEqual(len(got), 1)
            self.assertEqual(got[0].eval_run_id, "er-xyz")
            self.assertEqual(got[0].results[0].version_id, "v1")
            self.assertEqual(got[0].results[0].schema_compliance_rate, 1.0)

    def test_judge_result_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = JSONLStore(tmp)
            jr = JudgeResult(
                judge_id="jr-1",
                trace_id="t-1",
                eval_run_id="er-1",
                version_id="v1",
                case_id="c1",
                judge_model="openai:gpt-4o-mini",
                rubric={"correctness": 5, "format": 4, "conciseness": 5, "faithfulness": 5},
                overall=4.75,
                rationale="ok",
                ts=time.time(),
            )
            store.append_judge_result(jr)
            got = list(store.iter_judge_results())
            self.assertEqual(len(got), 1)
            self.assertEqual(got[0].rubric["correctness"], 5)
            self.assertEqual(got[0].overall, 4.75)


if __name__ == "__main__":
    unittest.main()
