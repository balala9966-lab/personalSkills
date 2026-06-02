"""Test the SSE parser against recorded Anthropic / OpenAI fixtures."""

from __future__ import annotations

import time
import unittest
from pathlib import Path

from ai_obs_lab.proxy.sse_parser import parse_sse_lines

FIXTURES = Path(__file__).parent / "fixtures"


def _feed_lines(path: Path, base_ts: float, gap_s: float = 0.0):
    """Yield (timestamp, line_bytes) for every line of an SSE fixture.

    `gap_s` advances the timestamp between successive lines; set to a value
    >0.8 to force pause detection.
    """
    ts = base_ts
    for raw in path.read_text(encoding="utf-8").splitlines():
        yield (ts, raw.encode("utf-8"))
        ts += gap_s


class TestAnthropicStream(unittest.TestCase):
    def test_anthropic_text_and_tool_use(self) -> None:
        t0 = time.time()
        state = parse_sse_lines(
            _feed_lines(FIXTURES / "anthropic_stream.txt", t0, gap_s=0.001),
            ts_start=t0,
        )

        # Text accumulation
        self.assertEqual("".join(state.text_parts), "Hello world")

        # Tokens extracted from message_start + message_delta
        self.assertEqual(state.tokens_in, 42)
        self.assertEqual(state.tokens_out, 17)
        self.assertEqual(state.model, "claude-3-5-sonnet")
        self.assertEqual(state.finish_reason, "end_turn")

        # Tool call aggregation: name + concatenated partial_json args
        calls = state.finalized_tool_calls()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].name, "Read")
        self.assertEqual(calls[0].tool_id, "toolu_01")
        self.assertIn("/tmp/a", calls[0].arguments_json)
        self.assertTrue(calls[0].parsed_ok, msg=f"args={calls[0].arguments_json!r}")

        # Chunk kinds emitted
        kinds = [c.kind for c in state.chunks]
        self.assertIn("text", kinds)
        self.assertIn("tool_use", kinds)
        self.assertIn("tool_args", kinds)
        self.assertIn("stop", kinds)

    def test_pause_detection(self) -> None:
        t0 = time.time()
        # Inject 1.0s gap between EVERY line — this will create lots of pauses.
        state = parse_sse_lines(
            _feed_lines(FIXTURES / "anthropic_stream.txt", t0, gap_s=1.0),
            ts_start=t0,
        )
        # We should have detected at least one pause (between text deltas).
        self.assertGreaterEqual(len(state.pauses_ms), 1)
        # Pause events must be in the chunk stream too.
        pause_chunks = [c for c in state.chunks if c.kind == "pause"]
        self.assertEqual(len(pause_chunks), len(state.pauses_ms))


class TestOpenAIStream(unittest.TestCase):
    def test_openai_text_and_tool_call(self) -> None:
        t0 = time.time()
        state = parse_sse_lines(
            _feed_lines(FIXTURES / "openai_stream.txt", t0, gap_s=0.001),
            ts_start=t0,
        )
        self.assertEqual("".join(state.text_parts), "Hello world")
        self.assertEqual(state.tokens_in, 18)
        self.assertEqual(state.tokens_out, 12)
        self.assertEqual(state.model, "gpt-4o-mini")
        self.assertEqual(state.finish_reason, "tool_calls")

        calls = state.finalized_tool_calls()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].name, "get_weather")
        self.assertEqual(calls[0].tool_id, "call_1")
        self.assertIn("Hangzhou", calls[0].arguments_json)
        self.assertTrue(calls[0].parsed_ok)

    def test_done_marker_emits_stop(self) -> None:
        t0 = time.time()
        state = parse_sse_lines(
            _feed_lines(FIXTURES / "openai_stream.txt", t0, gap_s=0.001),
            ts_start=t0,
        )
        stops = [c for c in state.chunks if c.kind == "stop"]
        self.assertGreaterEqual(len(stops), 1)


if __name__ == "__main__":
    unittest.main()
