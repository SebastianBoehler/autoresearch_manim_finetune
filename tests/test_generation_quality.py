from __future__ import annotations

import unittest

from mac_pipeline.eval_summary import summarize_case_results
from mac_pipeline.generation_quality import analyze_generation_quality, is_generation_quality_ok


class GenerationQualityTests(unittest.TestCase):
    def test_flags_repetitive_long_scene(self) -> None:
        code = """from manim import *

class Demo(Scene):
    def construct(self):
        label = Text("x")
        self.play(FadeIn(label), run_time=2)
        self.wait(1)
        self.play(label.animate.set_color(YELLOW), run_time=1)
        self.wait(1)
        self.play(label.animate.set_color(YELLOW), run_time=1)
        self.wait(1)
        self.play(label.animate.set_color(YELLOW), run_time=1)
        self.wait(1)
        self.play(label.animate.set_color(YELLOW), run_time=1)
        self.wait(20)
"""
        report = analyze_generation_quality(code)
        self.assertGreater(report.estimated_duration_seconds, 20)
        self.assertIn("estimated-duration-over-20s", report.warnings)
        self.assertIn("repeated-play-patterns", report.warnings)
        self.assertEqual(report.max_repeated_play_count, 4)
        self.assertFalse(is_generation_quality_ok(report))

    def test_compact_scene_has_no_warnings(self) -> None:
        code = """from manim import *

class Demo(Scene):
    def construct(self):
        title = Text("x")
        circle = Circle()
        self.play(FadeIn(title), Create(circle), run_time=2)
        self.play(circle.animate.shift(RIGHT), run_time=2)
        self.wait(1)
"""
        report = analyze_generation_quality(code)
        self.assertLess(report.estimated_duration_seconds, 20)
        self.assertEqual(report.warnings, [])
        self.assertTrue(is_generation_quality_ok(report))
        self.assertFalse(is_generation_quality_ok({}))

    def test_summary_tracks_quality_and_production_rates(self) -> None:
        summary = summarize_case_results(
            [
                {
                    "syntax_ok": True,
                    "render_ok": True,
                    "weighted_score": 1.0,
                    "generation_quality_ok": True,
                },
                {
                    "syntax_ok": True,
                    "render_ok": True,
                    "weighted_score": 0.8,
                    "generation_quality": {"warnings": ["too-many-waits"]},
                },
                {
                    "syntax_ok": False,
                    "render_ok": None,
                    "weighted_score": 0.2,
                    "generation_quality": {"warnings": []},
                },
            ]
        )
        self.assertEqual(summary["quality_success_rate"], 2 / 3)
        self.assertEqual(summary["production_success_rate"], 1 / 3)
        self.assertEqual(summary["render_success_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
