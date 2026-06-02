"""Test eval metric calculations on fixed inputs."""

from __future__ import annotations

import math
import unittest

from ai_obs_lab.eval.metrics import (
    avg_logprob_top1,
    keyword_hit_rate,
    pairwise_similarity_variance,
    schema_compliance_rate,
)


SCHEMA_NAC = {
    "type": "object",
    "required": ["name", "age", "city"],
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
        "city": {"type": "string"},
    },
}


class TestSimilarityVariance(unittest.TestCase):
    def test_identical_outputs_zero_variance(self) -> None:
        outs = ['{"a":1}'] * 5
        self.assertEqual(pairwise_similarity_variance(outs), 0.0)

    def test_completely_different_outputs_high_variance(self) -> None:
        outs = ["aaaaaaaa", "bbbbbbbb", "cccccccc", "dddddddd"]
        v = pairwise_similarity_variance(outs)
        self.assertIsNotNone(v)
        self.assertGreater(v, 0.5)

    def test_single_or_empty_returns_none(self) -> None:
        self.assertIsNone(pairwise_similarity_variance([]))
        self.assertIsNone(pairwise_similarity_variance(["only"]))


class TestSchemaCompliance(unittest.TestCase):
    def test_all_valid(self) -> None:
        outs = [
            '{"name":"John","age":29,"city":"Hangzhou"}',
            '{"name":"Lily","age":34,"city":"Shanghai"}',
        ]
        self.assertEqual(schema_compliance_rate(outs, SCHEMA_NAC), 1.0)

    def test_partial_valid(self) -> None:
        outs = [
            '{"name":"John","age":29,"city":"Hangzhou"}',  # ok
            '{"name":"John"}',                              # missing age, city
            "not json at all",                              # no JSON
            'Here is the result: {"name":"Bob","age":40,"city":"NYC"}',  # extracted
        ]
        rate = schema_compliance_rate(outs, SCHEMA_NAC)
        self.assertAlmostEqual(rate, 0.5, places=2)

    def test_type_mismatch_fails(self) -> None:
        outs = ['{"name":"X","age":"twenty","city":"Y"}']  # age is string
        self.assertEqual(schema_compliance_rate(outs, SCHEMA_NAC), 0.0)

    def test_markdown_fence_stripped(self) -> None:
        outs = ['```json\n{"name":"X","age":1,"city":"Y"}\n```']
        self.assertEqual(schema_compliance_rate(outs, SCHEMA_NAC), 1.0)

    def test_none_schema_returns_none(self) -> None:
        self.assertIsNone(schema_compliance_rate(["{}"], None))


class TestKeywordHitRate(unittest.TestCase):
    def test_case_insensitive_match(self) -> None:
        outs = ["Hangzhou is great", "HANGZHOU at night", "Shanghai is bigger"]
        self.assertAlmostEqual(keyword_hit_rate(outs, ["hangzhou"]), 2 / 3, places=3)

    def test_all_keywords_required(self) -> None:
        outs = [
            "Hangzhou Lily",
            "Hangzhou alone",
            "Lily alone",
        ]
        # Both keywords required.
        self.assertAlmostEqual(keyword_hit_rate(outs, ["hangzhou", "lily"]), 1 / 3, places=3)

    def test_empty_inputs_return_none(self) -> None:
        self.assertIsNone(keyword_hit_rate([], ["x"]))
        self.assertIsNone(keyword_hit_rate(["x"], []))
        self.assertIsNone(keyword_hit_rate(["x"], None))


class TestLogprobTop1(unittest.TestCase):
    def test_average_exponentiated(self) -> None:
        # Two responses; second token has lower probability.
        v = avg_logprob_top1([[math.log(0.9), math.log(0.5)], [math.log(0.8)]])
        # Mean of [0.9, 0.5, 0.8] = 0.733...
        self.assertAlmostEqual(v, (0.9 + 0.5 + 0.8) / 3, places=5)

    def test_none_inputs(self) -> None:
        self.assertIsNone(avg_logprob_top1(None))
        self.assertIsNone(avg_logprob_top1([]))
        self.assertIsNone(avg_logprob_top1([[]]))


if __name__ == "__main__":
    unittest.main()
