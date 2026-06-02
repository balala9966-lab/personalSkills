"""End-to-end smoke test for the capture proxy.

Spins up:
  * a tiny MockUpstream HTTP server (replays a recorded OpenAI SSE stream)
  * the proxy in a background thread with `upstreams.openai` pointed at it

Then sends a POST through the proxy, asserts the response is forwarded, and
checks that a TraceSummary + TraceFull were persisted with the expected fields.
"""

from __future__ import annotations

import json
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ai_obs_lab.core.store import JSONLStore
from ai_obs_lab.proxy.server import ProxyConfig, _make_proxy_handler


FIXTURES = Path(__file__).parent / "fixtures"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------------------
# Mock upstream that replays a recorded OpenAI SSE fixture
# ---------------------------------------------------------------------------


def _make_mock_upstream():
    stream_bytes = (FIXTURES / "openai_stream.txt").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_a, **_k):  # silence
            pass

        def do_POST(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            # Stream the recorded events with tiny inter-line delays so the
            # parser sees realistic chunk timestamps.
            for line in stream_bytes.splitlines(keepends=True):
                try:
                    self.wfile.write(line)
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return
                time.sleep(0.002)

    return Handler


# ---------------------------------------------------------------------------
# Helper to start a ThreadingHTTPServer in a background thread
# ---------------------------------------------------------------------------


class _BgServer:
    def __init__(self, handler_cls, port: int):
        self.port = port
        self.srv = ThreadingHTTPServer(("127.0.0.1", port), handler_cls)
        self.srv.daemon_threads = True
        self.thread = threading.Thread(target=self.srv.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        # Wait until the socket actually accepts.
        for _ in range(50):
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.2):
                    return self
            except OSError:
                time.sleep(0.02)
        raise RuntimeError(f"server on :{self.port} did not come up")

    def __exit__(self, *_):
        self.srv.shutdown()
        self.srv.server_close()


class TestProxySmoke(unittest.TestCase):
    def test_proxy_forwards_sse_and_persists_trace(self) -> None:
        upstream_port = _free_port()
        proxy_port = _free_port()
        with tempfile.TemporaryDirectory() as tmp:
            store = JSONLStore(tmp)
            cfg = ProxyConfig(
                listen_host="127.0.0.1",
                listen_port=proxy_port,
                log_dir=tmp,
                redact_headers=("authorization",),
                upstreams={
                    "openai": f"http://127.0.0.1:{upstream_port}",
                    "anthropic": "https://api.anthropic.com",
                },
                profiles={},
            )
            proxy_handler = _make_proxy_handler(cfg, store)

            with _BgServer(_make_mock_upstream(), upstream_port), \
                 _BgServer(proxy_handler, proxy_port):

                url = f"http://127.0.0.1:{proxy_port}/openai/v1/chat/completions"
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": True,
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer sk-test-1234",
                        "User-Agent": "claude-cli-test/0.0",
                    },
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    body = resp.read()
                self.assertIn(b"chat.completion.chunk", body)
                self.assertIn(b"[DONE]", body)

            # Allow the proxy's persistence thread time to flush.
            time.sleep(0.1)

        # ---- assertions about persisted state ----
        # Use a fresh store handle on the same dir.
            store2 = JSONLStore(tmp)
            today = date.today()
            summaries = list(store2.iter_summaries(start=today, end=today))
            self.assertEqual(len(summaries), 1, msg=f"summaries={summaries}")
            s = summaries[0]
            self.assertEqual(s.client_hint, "claude-code")
            self.assertEqual(s.upstream, "openai")
            self.assertEqual(s.status, 200)
            self.assertIsNotNone(s.ttft_ms)
            self.assertGreater(s.tool_call_count, 0)

            # Full trace persisted with redacted header + extracted tool call.
            tf = store2.load_trace(s.trace_id, ts=s.ts_start)
            auth = tf.request_headers.get("Authorization") or tf.request_headers.get("authorization")
            self.assertTrue(auth and auth.startswith("sha256:"),
                            msg=f"auth not redacted: {auth!r}")
            self.assertTrue(any(tc.name == "get_weather" for tc in tf.tool_calls),
                            msg=f"tool_calls={tf.tool_calls}")
            # response_text should contain accumulated "Hello world".
            self.assertIn("Hello world", tf.response_text)
            # At least one streaming chunk recorded.
            self.assertGreater(len(tf.chunks), 0)


if __name__ == "__main__":
    unittest.main()
