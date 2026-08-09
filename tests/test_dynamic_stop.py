from __future__ import annotations

import unittest

from mac_pipeline.dynamic_stop import (
    infer_target_duration_seconds,
    should_stop_manim_generation,
)


class DynamicStopTests(unittest.TestCase):
    def test_infers_numeric_and_word_durations(self) -> None:
        self.assertEqual(infer_target_duration_seconds("Create a 30-second scene."), 30)
        self.assertEqual(infer_target_duration_seconds("Create a one-minute scene."), 60)

    def test_stops_when_scene_is_complete_and_target_duration_is_met(self) -> None:
        code = """from manim import *

class Demo(Scene):
    def construct(self):
        dot = Dot()
        self.play(FadeIn(dot), run_time=4)
        self.play(dot.animate.shift(RIGHT), run_time=4)
        self.play(dot.animate.shift(LEFT), run_time=4)
        self.wait(2)
"""
        should_stop = should_stop_manim_generation(
            code,
            "Create a 15-second Manim scene.",
            target_ratio=0.85,
            default_duration_seconds=15,
        )
        self.assertTrue(should_stop)

    def test_does_not_stop_before_requested_duration(self) -> None:
        code = """from manim import *

class Demo(Scene):
    def construct(self):
        dot = Dot()
        self.play(FadeIn(dot), run_time=2)
        self.play(dot.animate.shift(RIGHT), run_time=2)
        self.play(dot.animate.shift(LEFT), run_time=2)
"""
        should_stop = should_stop_manim_generation(
            code,
            "Create a one-minute Manim scene.",
            target_ratio=0.85,
            default_duration_seconds=15,
        )
        self.assertFalse(should_stop)


if __name__ == "__main__":
    unittest.main()
