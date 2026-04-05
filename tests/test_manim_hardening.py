from __future__ import annotations

import unittest

from mac_pipeline.manim_hardening import (
    HARDENING_SENTINEL,
    harden_system_prompt,
    normalize_generated_code,
    repair_generated_code,
)


class ManimHardeningTests(unittest.TestCase):
    def test_harden_system_prompt_is_idempotent(self) -> None:
        prompt = "Return runnable Manim code."
        hardened_once = harden_system_prompt(prompt)
        hardened_twice = harden_system_prompt(hardened_once)
        self.assertIn(HARDENING_SENTINEL, hardened_once)
        self.assertEqual(hardened_once, hardened_twice)

    def test_normalize_generated_code_rewrites_known_invalid_api_patterns(self) -> None:
        code = """from manim import *

class Demo(Scene):
    def construct(self):
        number_line = NumberLine(x_range=[0, 4, 1], x_length=8)
        graph = Graph(["A", "B"], [("A", "B")], layout=GraphLayout("circular"))
        polar = PolarPlane()
        curve = polar.plot_polar(lambda t: 1 + t)
        caption = Text("x").move_by(RIGHT)
        arrow = Pipe(LEFT, RIGHT, color=ORANGE_D)
        panel.add_caption(caption)
"""
        normalized, notes = normalize_generated_code(code)
        self.assertIn("length=8", normalized)
        self.assertIn("layout=\"circular\"", normalized)
        self.assertIn(".plot_polar_graph(", normalized)
        self.assertIn(".shift(RIGHT)", normalized)
        self.assertIn("Line(LEFT, RIGHT, color=ORANGE)", normalized)
        self.assertNotIn("add_caption", normalized)
        self.assertTrue(notes)

    def test_normalize_generated_code_handles_residual_runtime_failure_patterns(self) -> None:
        code = """from manim import *

class Demo(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes(x_range=[-1, 1, 1], y_range=[-1, 1, 1], z_range=[-1, 1, 1])
        marker = Dot(vector_field.get_origin())
        self.play(Indicate(caption_text))
        graph = Graph(["A", "B"], [["A", "B"]], layout=GraphLayout("circular"))
        mover = MoveToTarget(dot, target=shell, run_time=1)
"""
        normalized, notes = normalize_generated_code(code)
        self.assertIn("ThreeDAxes(", normalized)
        self.assertNotIn("ThreeDThreeDAxes", normalized)
        self.assertIn("ORIGIN", normalized)
        self.assertIn("phase_caption", normalized)
        self.assertIn('("A", "B")', normalized)
        self.assertIn("dot.animate.move_to(shell)", normalized)
        self.assertTrue(notes)

    def test_repair_generated_code_rewrites_scene_play_specific_failures(self) -> None:
        code = """from manim import *

class Demo(Scene):
    def construct(self):
        frontier = VMobject()
        highlight = Square()
        self.play(frontier.set_points_smoothly([LEFT, RIGHT]), highlight.become(Circle()), run_time=2)
"""
        repaired, notes = repair_generated_code(
            code,
            "TypeError: Unexpected argument VMobject passed to Scene.play().",
        )
        self.assertIn("frontier.animate.set_points_smoothly", repaired)
        self.assertIn("highlight.animate.become", repaired)
        self.assertTrue(notes)


if __name__ == "__main__":
    unittest.main()
