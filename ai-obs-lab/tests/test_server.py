"""实时看板 HTTP 服务的冒烟测试。

在随机端口起一个真实的 ThreadingHTTPServer，用 http.client 打三个端点：
  /_health        健康检查
  /api/snapshot   概览 + trace 列表（JSON）
  /api/trace/<id> 单条详情 + 上下文解析（JSON）
验证返回的 JSON 结构符合前端期望，不校验具体业务数值。
"""

from __future__ import annotations

import http.client
import json
import tempfile
import threading
import time
import unittest

from ai_obs_lab.core.models import Chunk, ToolCallRecord, TraceFull, TraceSummary
from ai_obs_lab.core.store import JSONLStore
from ai_obs_lab.dashboard.server import _make_handler, _ThreadingHTTPServer


def _mk_summary(trace_id: str, ts: float, **overrides) -> TraceSummary:
    base = dict(
        trace_id=trace_id,
        ts_start=ts,
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
        chunks=2,
        tool_call_count=1,
    )
    base.update(overrides)
    return TraceSummary(**base)


def _seed_one_trace(store: JSONLStore, trace_id: str) -> float:
    ts = time.time()
    summary = _mk_summary(trace_id, ts)
    trace = TraceFull(
        summary=summary,
        request_headers={"x-api-key": "sha256:abcd1234"},
        request_body={
            "model": "claude-3-5-sonnet",
            "system": "你是一个助手",
            "tools": [
                {"name": "Read", "description": "读文件", "input_schema": {"type": "object"}},
            ],
            "messages": [{"role": "user", "content": "你好"}],
        },
        response_text="hi",
        chunks=[Chunk(seq=0, ts_offset_ms=50, kind="text", text="hi")],
        tool_calls=[
            ToolCallRecord(tool_id="call_1", name="Read",
                           arguments_json='{"path":"x"}', parsed_ok=True),
        ],
        pauses_ms=[],
    )
    store.write_trace(trace)
    store.append_summary(summary)
    return ts


class TestLiveServer(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = JSONLStore(self._tmp.name)
        self.trace_id = "t-live-1"
        self.trace_ts = _seed_one_trace(self.store, self.trace_id)

        handler = _make_handler(self.store)
        # port=0 让 OS 自动分配空闲端口，避免端口占用。
        self.server = _ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self._tmp.cleanup()

    def _get(self, path: str):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("GET", path)
            resp = conn.getresponse()
            body = resp.read().decode("utf-8")
            return resp.status, body
        finally:
            conn.close()

    def test_health(self) -> None:
        status, body = self._get("/_health")
        self.assertEqual(status, 200)
        self.assertEqual(body, "ok")

    def test_snapshot_structure(self) -> None:
        status, body = self._get("/api/snapshot?date=today")
        self.assertEqual(status, 200)
        data = json.loads(body)
        # 前端依赖的四个顶层键必须存在。
        for key in ("overview", "traces", "tools", "mcp_sessions"):
            self.assertIn(key, data)
        self.assertIsInstance(data["traces"], list)
        self.assertIsInstance(data["mcp_sessions"], list)
        self.assertGreaterEqual(data["overview"]["total"], 1)
        ids = [t["trace_id"] for t in data["traces"]]
        self.assertIn(self.trace_id, ids)

    def test_trace_detail_with_context(self) -> None:
        status, body = self._get(
            f"/api/trace/{self.trace_id}?ts={self.trace_ts}")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["summary"]["trace_id"], self.trace_id)
        # 上下文解析必须挂在详情里，且 tools 菜单被识别出来。
        self.assertIn("context", data)
        ctx = data["context"]
        self.assertTrue(ctx.get("available"))
        self.assertGreaterEqual(ctx.get("tools_count", 0), 1)
        # 参数名保持原样（不被中文化）。
        self.assertIn("token_breakdown", ctx)
        self.assertIn("system_pct", ctx["token_breakdown"])

    def test_trace_not_found(self) -> None:
        status, body = self._get("/api/trace/does-not-exist?ts=1")
        self.assertEqual(status, 404)
        data = json.loads(body)
        self.assertIn("error", data)

    def test_unknown_path_404(self) -> None:
        status, _ = self._get("/nope")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
