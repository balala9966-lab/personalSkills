"""Tests for query.parse_request_context —— 上下文拆解的核心逻辑。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ai_obs_lab.dashboard.query import (  # noqa: E402
    parse_request_context,
    _estimate_tokens,
    _guess_tool_origin,
)


class TestEstimateTokens(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_estimate_tokens(""), 0)

    def test_ascii_shorter_than_cjk(self):
        # 同样字符数，中文估算 token 更多（1.5 字符/token vs 4 字符/token）
        ascii_tokens = _estimate_tokens("a" * 40)
        cjk_tokens = _estimate_tokens("中" * 40)
        self.assertGreater(cjk_tokens, ascii_tokens)


class TestGuessToolOrigin(unittest.TestCase):
    def test_mcp_prefix(self):
        self.assertEqual(_guess_tool_origin("mcp__yuque__read_doc", ""), "MCP(yuque)")

    def test_builtin(self):
        self.assertEqual(_guess_tool_origin("Read", ""), "builtin")
        self.assertEqual(_guess_tool_origin("Bash", ""), "builtin")

    def test_other(self):
        self.assertEqual(_guess_tool_origin("custom_thing", ""), "other")


class TestParseAnthropic(unittest.TestCase):
    def setUp(self):
        self.body = {
            "model": "Kimi-K2.6",
            "system": "You are Claude Code, an AI assistant.",
            "tools": [
                {"name": "Read", "description": "Read a file",
                 "input_schema": {"type": "object"}},
                {"name": "mcp__db__query", "description": "Query the DB",
                 "input_schema": {"type": "object"}},
            ],
            "messages": [
                {"role": "user", "content": "看文件"},
                {"role": "assistant",
                 "content": [{"type": "tool_use", "name": "Read", "input": {"p": "/a"}}]},
                {"role": "user",
                 "content": [{"type": "tool_result", "content": "data"}]},
            ],
        }

    def test_available(self):
        ctx = parse_request_context(self.body)
        self.assertTrue(ctx["available"])
        self.assertEqual(ctx["model"], "Kimi-K2.6")

    def test_system_extracted(self):
        ctx = parse_request_context(self.body)
        self.assertIn("Claude Code", ctx["system"]["text"])
        self.assertGreater(ctx["system"]["tokens"], 0)

    def test_tools_origin(self):
        ctx = parse_request_context(self.body)
        self.assertEqual(ctx["tools_count"], 2)
        origins = {t["name"]: t["origin"] for t in ctx["tools"]}
        self.assertEqual(origins["Read"], "builtin")
        self.assertEqual(origins["mcp__db__query"], "MCP(db)")

    def test_message_flags(self):
        ctx = parse_request_context(self.body)
        self.assertEqual(ctx["messages_count"], 3)
        by_idx = {m["index"]: m for m in ctx["messages"]}
        self.assertTrue(by_idx[1]["has_tool_use"])
        self.assertTrue(by_idx[2]["has_tool_result"])

    def test_token_breakdown_sums(self):
        ctx = parse_request_context(self.body)
        tb = ctx["token_breakdown"]
        self.assertEqual(tb["total_estimated"],
                         tb["system"] + tb["tools"] + tb["messages"])
        # 占比合计约等于 100
        pct_sum = tb["system_pct"] + tb["tools_pct"] + tb["messages_pct"]
        self.assertAlmostEqual(pct_sum, 100.0, delta=0.5)


class TestParseOpenAI(unittest.TestCase):
    def test_openai_format(self):
        body = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "hi"},
            ],
            "tools": [
                {"type": "function",
                 "function": {"name": "get_weather",
                              "description": "weather",
                              "parameters": {"type": "object"}}},
            ],
        }
        ctx = parse_request_context(body)
        self.assertTrue(ctx["available"])
        # system 从 messages 里抽出来
        self.assertIn("helpful", ctx["system"]["text"])
        # system 消息不再计入 messages 列表
        roles = [m["role"] for m in ctx["messages"]]
        self.assertNotIn("system", roles)
        self.assertEqual(ctx["tools"][0]["name"], "get_weather")


class TestParseEdgeCases(unittest.TestCase):
    def test_non_dict(self):
        ctx = parse_request_context("not a dict")
        self.assertFalse(ctx["available"])

    def test_empty_dict(self):
        ctx = parse_request_context({})
        self.assertTrue(ctx["available"])
        self.assertEqual(ctx["tools_count"], 0)
        self.assertEqual(ctx["messages_count"], 0)
        # 空请求不应除零崩溃
        self.assertEqual(ctx["token_breakdown"]["total_estimated"], 1)


if __name__ == "__main__":
    unittest.main()
