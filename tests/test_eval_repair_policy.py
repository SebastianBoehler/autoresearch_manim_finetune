from __future__ import annotations

import unittest

from mac_pipeline.eval import score_case
from mac_pipeline.types import MetricWeights


class EvalRepairPolicyTests(unittest.TestCase):
    def test_score_case_does_not_repair_generated_code_by_default(self) -> None:
        code = """from manim import *

class Demo(Scene):
    def construct(self):
        value = 2x
        self.wait(1)
"""
        result = score_case(
            case={"case_id": "demo"},
            code=code,
            render_enabled=False,
            weights=MetricWeights(),
            quality="low",
            timeout_seconds=1,
        )

        self.assertFalse(result["syntax_ok"])
        self.assertIn("2x", result["final_code"])
        self.assertEqual(result["final_code"], code)
        self.assertEqual(result["repair_attempts"], 0)
        self.assertFalse(result["code_repair_enabled"])
        self.assertEqual(result["normalization_notes"], [])

    def test_score_case_can_run_legacy_repairs_when_explicitly_enabled(self) -> None:
        code = """from manim import *

class Demo(Scene):
    def construct(self):
        value = 2x
        self.wait(1)
"""
        result = score_case(
            case={"case_id": "demo"},
            code=code,
            render_enabled=False,
            weights=MetricWeights(),
            quality="low",
            timeout_seconds=1,
            allow_code_repair=True,
        )

        self.assertTrue(result["syntax_ok"])
        self.assertIn("2*x", result["final_code"])
        self.assertTrue(result["code_repair_enabled"])
        self.assertIn("repair invalid numeric expression syntax", result["normalization_notes"])


if __name__ == "__main__":
    unittest.main()
