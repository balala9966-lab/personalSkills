"""Test parallel eval execution: equivalence with sequential + no data races."""

from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path

from ai_obs_lab.core.store import JSONLStore
from ai_obs_lab.eval import runner
from ai_obs_lab.eval.runner import Suite, SuiteCase, SuiteVersion, run_suite


def _mk_suite() -> Suite:
    return Suite(
        name="parallel-demo",
        upstream="openai",
        base_url="https://example.invalid",
        model="gpt-4o-mini",
        temperature=0.0,
        max_tokens=128,
        versions=[
            SuiteVersion(id="v1", system="strict", extra={}),
            SuiteVersion(id="v2", system="loose", extra={}),
        ],
        cases=[
            SuiteCase(id="c1", user="extract name", expect_keywords=["alice"]),
            SuiteCase(id="c2", user="extract city", expect_keywords=["paris"]),
        ],
    )


class TestParallelRunner(unittest.TestCase):
    def setUp(self) -> None:
        # Deterministic fake upstream: returns text derived from the payload so
        # outputs are stable and comparable across runs. Records max concurrent
        # in-flight calls to prove parallelism actually happens.
        self._inflight = 0
        self._max_inflight = 0
        self._lock = threading.Lock()

        def fake_call(suite, payload, api_key):
            with self._lock:
                self._inflight += 1
                self._max_inflight = max(self._max_inflight, self._inflight)
            try:
                time.sleep(0.02)  # widen the window so overlap is observable
                user = payload["messages"][-1]["content"]
                body = (
                    '{"choices":[{"message":{"content":"'
                    + f"echo:{user}"
                    + '"}}],"usage":{"prompt_tokens":5,"completion_tokens":7}}'
                )
                return 200, body, 10.0, 20.0, []
            finally:
                with self._lock:
                    self._inflight -= 1

        self._orig_call = runner._call_upstream
        runner._call_upstream = fake_call  # type: ignore[assignment]

    def tearDown(self) -> None:
        runner._call_upstream = self._orig_call  # type: ignore[assignment]

    def _outputs_by_pair(self, er) -> dict:
        return {(r.version_id, r.case_id): list(r.outputs) for r in er.results}

    def test_parallel_matches_sequential(self) -> None:
        suite = _mk_suite()
        with tempfile.TemporaryDirectory() as tmp:
            seq = run_suite(suite, repeat=4, store=JSONLStore(Path(tmp) / "a"),
                            concurrency=1)
            par = run_suite(suite, repeat=4, store=JSONLStore(Path(tmp) / "b"),
                            concurrency=4)
        self.assertEqual(self._outputs_by_pair(seq), self._outputs_by_pair(par))

    def test_parallelism_actually_overlaps(self) -> None:
        suite = _mk_suite()
        with tempfile.TemporaryDirectory() as tmp:
            run_suite(suite, repeat=5, store=JSONLStore(tmp), concurrency=5)
        self.assertGreater(self._max_inflight, 1)

    def test_repeat_order_preserved(self) -> None:
        # Each repeat output is identical here, but trace_ids must follow k order.
        suite = _mk_suite()
        with tempfile.TemporaryDirectory() as tmp:
            er = run_suite(suite, repeat=3, store=JSONLStore(tmp), concurrency=3)
        for r in er.results:
            expected = [
                f"eval-{er.eval_run_id}-{r.version_id}-{r.case_id}-{k}"
                for k in range(3)
            ]
            self.assertEqual(r.trace_ids, expected)

    def test_all_traces_persisted_no_loss(self) -> None:
        suite = _mk_suite()
        with tempfile.TemporaryDirectory() as tmp:
            store = JSONLStore(tmp)
            er = run_suite(suite, repeat=4, store=store, concurrency=4)
            persisted = {s.trace_id for s in store.iter_summaries()}
        expected = {
            tid for r in er.results for tid in r.trace_ids
        }
        self.assertEqual(persisted, expected)
        # 2 versions x 2 cases x 4 repeats = 16 traces
        self.assertEqual(len(persisted), 16)


if __name__ == "__main__":
    unittest.main()
