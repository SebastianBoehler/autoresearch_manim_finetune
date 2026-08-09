from __future__ import annotations

import ast
import unittest

from mac_pipeline.syntax_repair import repair_syntax_generated_code


class SyntaxRepairTests(unittest.TestCase):
    def test_repairs_invalid_decimal_literal_in_generated_function_panel(self) -> None:
        code = """from manim import *

class Demo(Scene):
    def construct(self):
        functions = VGroup(
            lambda x: x,
            lambda x: 1 / (1 + exp(-x)),
            lambda x: 2 / (1 + exp(-2x)),
        )
        self.play(ShowCreation(VGroup()))
"""
        repaired, notes = repair_syntax_generated_code(
            code,
            "invalid decimal literal (<unknown>, line 7)",
        )

        ast.parse(repaired)
        self.assertIn("np.exp(-x)", repaired)
        self.assertIn("np.exp(-2*x)", repaired)
        self.assertIn("functions = [", repaired)
        self.assertIn("Create(VGroup())", repaired)
        self.assertTrue(notes)

    def test_leaves_other_syntax_errors_unchanged(self) -> None:
        code = "self.play(\n"
        repaired, notes = repair_syntax_generated_code(code, "'(' was never closed")

        self.assertEqual(repaired, code)
        self.assertEqual(notes, [])


if __name__ == "__main__":
    unittest.main()
