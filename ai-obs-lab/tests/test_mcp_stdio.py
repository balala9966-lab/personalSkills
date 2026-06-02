"""stdio MCP wrapper 的测试。

两层验证：
  1. 单元：_classify 正确区分 request/response/notification/error；
     _pump 把每行透明转发 + 把合法 JSON 帧 tee 到 store（非 JSON 行只转发）。
  2. 端到端：用一个假的 echo MCP server（子进程），通过 run_mcp_wrapper 把
     client 的请求转发给它、把它的响应转回来，并确认两端的 JSON-RPC 帧都落了盘。
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import date

from ai_obs_lab.core.store import JSONLStore
from ai_obs_lab.proxy.mcp_stdio import _classify, _pump, run_mcp_wrapper


# 一个最小的假 echo MCP server：每读到一行 JSON-RPC 请求，就回一行 result。
# 写成可独立运行的脚本字符串，测试时落到临时文件用子进程跑。
_FAKE_SERVER = r"""
import sys, json
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        req = json.loads(line)
    except Exception:
        continue
    resp = {"jsonrpc": "2.0", "id": req.get("id"),
            "result": {"echo": req.get("method"), "params": req.get("params")}}
    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()
    if req.get("method") == "shutdown":
        break
"""


class TestClassify(unittest.TestCase):
    def test_request(self) -> None:
        m, kind = _classify({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(m, "tools/list")
        self.assertEqual(kind, "request")

    def test_notification(self) -> None:
        m, kind = _classify({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertEqual(m, "notifications/initialized")
        self.assertEqual(kind, "notification")

    def test_response(self) -> None:
        m, kind = _classify({"jsonrpc": "2.0", "id": 1, "result": {"tools": []}})
        self.assertIsNone(m)
        self.assertEqual(kind, "response")

    def test_error(self) -> None:
        m, kind = _classify({"jsonrpc": "2.0", "id": 1, "error": {"code": -1}})
        self.assertEqual(kind, "error")


class _KeepOpenBytesIO(io.BytesIO):
    """_pump 结束会 close(dst)（真实管道需要），测试里忽略 close 以便读取内容。"""

    def close(self) -> None:  # noqa: D401
        pass


class TestPump(unittest.TestCase):
    def test_pump_tees_json_and_forwards_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = JSONLStore(tmp)
            session_id = "sess-pump"
            src = io.BytesIO(
                b'{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n'
                b'this is a plain log line, not json\n'
                b'{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}\n'
            )
            dst = _KeepOpenBytesIO()
            _pump(src, dst, direction="server->client",
                  store=store, session_id=session_id)

            # 透明转发：所有 3 行都应原样出现在 dst。
            forwarded = dst.getvalue()
            self.assertIn(b"plain log line", forwarded)
            self.assertEqual(forwarded.count(b"\n"), 3)

            # 只有 2 行合法 JSON 被 tee 成帧。
            sessions = list(store.iter_mcp_sessions())
            self.assertEqual(len(sessions), 1)
            frames = sessions[0]["frames"]
            self.assertEqual(len(frames), 2)
            self.assertEqual(frames[0]["method"], "tools/list")
            self.assertEqual(frames[0]["direction"], "server->client")
            self.assertEqual(frames[1]["kind"], "response")


class TestEndToEnd(unittest.TestCase):
    def test_wrapper_forwards_and_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = JSONLStore(tmp)
            server_path = os.path.join(tmp, "fake_server.py")
            with open(server_path, "w") as f:
                f.write(_FAKE_SERVER)

            # run_mcp_wrapper 直接读 sys.stdin.buffer / 写 sys.stdout.buffer，
            # 为隔离，改用子进程跑 wrapper：父进程喂请求、收响应。
            wrapper_code = (
                "import sys;"
                "sys.path.insert(0, %r);"
                "from ai_obs_lab.core.store import JSONLStore;"
                "from ai_obs_lab.proxy.mcp_stdio import run_mcp_wrapper;"
                "store=JSONLStore(%r);"
                "raise SystemExit(run_mcp_wrapper(['--','%s',%r],store=store,label='test'))"
                % (
                    os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"),
                    tmp,
                    sys.executable,
                    server_path,
                )
            )
            proc = subprocess.Popen(
                [sys.executable, "-c", wrapper_code],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            requests = [
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                 "params": {"name": "Read", "arguments": {"path": "x"}}},
                {"jsonrpc": "2.0", "id": 3, "method": "shutdown"},
            ]
            payload = ("".join(json.dumps(r) + "\n" for r in requests)).encode()
            out, err = proc.communicate(input=payload, timeout=15)

            # 透明转发：每个请求都应收到对应 echo 响应。
            out_lines = [l for l in out.decode().splitlines() if l.strip()]
            self.assertEqual(len(out_lines), 3)
            first = json.loads(out_lines[0])
            self.assertEqual(first["result"]["echo"], "tools/list")

            # 落盘：两个方向的帧都应记录。
            sessions = list(store.iter_mcp_sessions())
            self.assertEqual(len(sessions), 1)
            sess = sessions[0]
            self.assertEqual(sess["label"], "test")
            directions = {fr["direction"] for fr in sess["frames"]}
            self.assertIn("client->server", directions)
            self.assertIn("server->client", directions)
            methods = {fr.get("method") for fr in sess["frames"]}
            self.assertIn("tools/call", methods)


if __name__ == "__main__":
    unittest.main()
