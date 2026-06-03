"""Test the optional FastAPI web backend + its stdlib graceful-degradation path.

The FastAPI dependency is optional. These tests:
- Always verify the pure payload builders (shared with the stdlib server) and
  the `fastapi_available()` probe.
- Only exercise the actual FastAPI app when FastAPI is installed (skipped
  otherwise), so the suite stays green on a stdlib-only install.
"""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from ai_obs_lab.core.models import TraceFull, TraceSummary
from ai_obs_lab.core.store import JSONLStore
from ai_obs_lab.dashboard.web import app as webapp


def _seed_store(tmp: str) -> JSONLStore:
    store = JSONLStore(tmp)
    s = TraceSummary(
        trace_id="t-web", ts_start=time.time(), client_hint="claude-code",
        upstream="anthropic", method="POST", path="/v1/messages",
        model="claude-3-5-sonnet", status=200, ttft_ms=80.0, total_ms=400.0,
        tokens_in=12, tokens_out=20, chunks=2, tool_call_count=0,
    )
    store.append_summary(s)
    store.write_trace(TraceFull(
        summary=s,
        request_body={"model": "claude-3-5-sonnet",
                      "messages": [{"role": "user", "content": "hi"}]},
        response_text="hello",
    ))
    return store


class TestPurePayloads(unittest.TestCase):
    def test_snapshot_payload_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_store(tmp)
            payload = webapp._snapshot_payload(store, "today")
        self.assertIn("overview", payload)
        self.assertIn("traces", payload)
        self.assertIn("tools", payload)
        self.assertIn("mcp_sessions", payload)
        self.assertEqual(payload["traces"][0]["trace_id"], "t-web")

    def test_trace_payload_includes_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_store(tmp)
            d = webapp._trace_payload(store, "t-web", ts=None)
        self.assertEqual(d["summary"]["trace_id"], "t-web")
        self.assertIn("context", d)

    def test_trace_payload_missing_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = JSONLStore(tmp)
            with self.assertRaises(FileNotFoundError):
                webapp._trace_payload(store, "nope", ts=None)


class TestAvailabilityProbe(unittest.TestCase):
    def test_probe_returns_bool(self) -> None:
        self.assertIsInstance(webapp.fastapi_available(), bool)

    def test_build_app_raises_without_fastapi(self) -> None:
        if webapp.fastapi_available():
            self.skipTest("FastAPI installed; degradation path not exercised here")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ImportError):
                webapp.build_app(JSONLStore(tmp))


@unittest.skipUnless(webapp.fastapi_available(), "FastAPI not installed")
class TestFastAPIApp(unittest.TestCase):
    def _client(self, store: JSONLStore):
        from fastapi.testclient import TestClient
        return TestClient(webapp.build_app(store))

    def test_health(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = self._client(_seed_store(tmp))
            r = client.get("/_health")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.text, "ok")

    def test_snapshot_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = self._client(_seed_store(tmp))
            r = client.get("/api/snapshot?date=today")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["traces"][0]["trace_id"], "t-web")

    def test_trace_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = self._client(_seed_store(tmp))
            r = client.get("/api/trace/t-web")
            self.assertEqual(r.status_code, 200)
            self.assertIn("context", r.json())

    def test_trace_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = self._client(_seed_store(tmp))
            r = client.get("/api/trace/missing")
            self.assertEqual(r.status_code, 404)

    def test_index_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = self._client(_seed_store(tmp))
            r = client.get("/")
            self.assertEqual(r.status_code, 200)
            self.assertIn("text/html", r.headers["content-type"])


if __name__ == "__main__":
    unittest.main()
