"""Test SQLiteStore: behavioral equivalence with JSONLStore + JSONL migration."""

from __future__ import annotations

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
from ai_obs_lab.core.sqlite_store import SQLiteStore
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


def _mk_trace(trace_id: str, ts: float, *, big: bool = False) -> TraceFull:
    content = ("x" * (LARGE_BODY_BYTES + 1024)) if big else "hi"
    return TraceFull(
        summary=_mk_summary(trace_id, ts=ts),
        request_headers={"x-api-key": "sha256:abcd1234"},
        request_body={"model": "claude-3-5-sonnet",
                      "messages": [{"role": "user", "content": content}]},
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


def _mk_eval_run(run_id: str, ts: float) -> EvalRun:
    return EvalRun(
        eval_run_id=run_id,
        ts_start=ts,
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
                trace_ids=["eval-x-v1-c1-0"], outputs=["{}", "{}"],
                similarity_variance=0.0, schema_compliance_rate=1.0,
                keyword_hit_rate=None, avg_logprob_top1=None,
                avg_ttft_ms=120.0, avg_total_ms=800.0, avg_tokens_out=42.0,
                errors=0,
            ),
        ],
    )


def _mk_judge(judge_id: str, ts: float) -> JudgeResult:
    return JudgeResult(
        judge_id=judge_id, trace_id="t-1", eval_run_id="er-1",
        version_id="v1", case_id="c1", judge_model="openai:gpt-4o-mini",
        rubric={"correctness": 5, "format": 4, "conciseness": 5, "faithfulness": 5},
        overall=4.75, rationale="ok", ts=ts,
    )


class TestSQLiteStore(unittest.TestCase):
    def _store(self, tmp: str) -> SQLiteStore:
        return SQLiteStore(Path(tmp) / "obs.db")

    def test_summary_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            s1 = _mk_summary("t-aaa")
            s2 = _mk_summary("t-bbb", ts=s1.ts_start + 1)
            store.append_summary(s1)
            store.append_summary(s2)
            today = date.today()
            got = list(store.iter_summaries(start=today, end=today))
            self.assertEqual(sorted(x.trace_id for x in got), ["t-aaa", "t-bbb"])
            store.close()

    def test_trace_round_trip_with_chunks_and_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            tf = _mk_trace("t-1", ts=time.time())
            store.write_trace(tf)
            loaded = store.load_trace("t-1")
            self.assertEqual(loaded.summary.trace_id, "t-1")
            self.assertEqual(loaded.response_text, "hello world")
            self.assertEqual(len(loaded.chunks), 3)
            self.assertEqual(loaded.tool_calls[0].name, "Read")
            self.assertEqual(loaded.pauses_ms, [1150.0])
            self.assertEqual(loaded.request_headers["x-api-key"], "sha256:abcd1234")
            self.assertEqual(loaded.request_body["model"], "claude-3-5-sonnet")
            store.close()

    def test_large_body_kept_inline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            tf = _mk_trace("t-big", ts=time.time(), big=True)
            store.write_trace(tf)
            loaded = store.load_trace("t-big")
            self.assertIsNotNone(loaded.request_body)
            self.assertEqual(
                len(loaded.request_body["messages"][0]["content"]),
                LARGE_BODY_BYTES + 1024,
            )
            store.close()

    def test_load_missing_trace_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            with self.assertRaises(FileNotFoundError):
                store.load_trace("nope")
            store.close()

    def test_eval_run_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            store.append_eval_run(_mk_eval_run("er-xyz", time.time()))
            got = list(store.iter_eval_runs())
            self.assertEqual(len(got), 1)
            self.assertEqual(got[0].eval_run_id, "er-xyz")
            self.assertEqual(got[0].results[0].schema_compliance_rate, 1.0)
            store.close()

    def test_judge_result_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            store.append_judge_result(_mk_judge("jr-1", time.time()))
            got = list(store.iter_judge_results())
            self.assertEqual(len(got), 1)
            self.assertEqual(got[0].rubric["correctness"], 5)
            self.assertEqual(got[0].overall, 4.75)
            store.close()

    def test_mcp_session_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            now = time.time()
            store.write_mcp_meta("sess-1", "npx some-mcp", now, label="fs")
            store.append_mcp_frame(
                "sess-1", now, "client->server",
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                method="tools/list", kind="request",
            )
            store.append_mcp_frame(
                "sess-1", now + 0.1, "server->client",
                {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}},
                kind="result",
            )
            sessions = list(store.iter_mcp_sessions())
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0]["command"], "npx some-mcp")
            self.assertEqual(len(sessions[0]["frames"]), 2)
            self.assertEqual(sessions[0]["frames"][0]["method"], "tools/list")
            store.close()

    def test_from_jsonl_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jsonl_dir = Path(tmp) / "logs"
            src = JSONLStore(jsonl_dir)
            now = time.time()
            tf = _mk_trace("t-mig", ts=now)
            src.append_summary(tf.summary)
            src.write_trace(tf)
            src.append_eval_run(_mk_eval_run("er-mig", now))
            src.append_judge_result(_mk_judge("jr-mig", now))
            src.write_mcp_meta("sess-mig", "npx mcp", now)
            src.append_mcp_frame(
                "sess-mig", now, "client->server",
                {"jsonrpc": "2.0", "method": "initialize"}, method="initialize",
            )

            store = SQLiteStore.from_jsonl(jsonl_dir, Path(tmp) / "obs.db")
            self.assertEqual([s.trace_id for s in store.iter_summaries()], ["t-mig"])
            self.assertEqual(store.load_trace("t-mig").response_text, "hello world")
            self.assertEqual([e.eval_run_id for e in store.iter_eval_runs()], ["er-mig"])
            self.assertEqual([j.judge_id for j in store.iter_judge_results()], ["jr-mig"])
            sessions = list(store.iter_mcp_sessions())
            self.assertEqual(len(sessions), 1)
            self.assertEqual(len(sessions[0]["frames"]), 1)
            store.close()


if __name__ == "__main__":
    unittest.main()
