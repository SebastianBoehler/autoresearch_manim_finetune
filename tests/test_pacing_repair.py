from __future__ import annotations

import unittest

from mac_pipeline.generation_quality import analyze_generation_quality
from mac_pipeline.pacing_repair import compact_repetitive_pacing


class PacingRepairTests(unittest.TestCase):
    def test_compacts_repeated_play_wait_pairs(self) -> None:
        repeated = "\n".join(
            [
                "        self.play(dot.animate.shift(UP * 0.2))",
                "        self.wait(1)",
            ]
            * 9
        )
        code = f"""from manim import *

class Demo(Scene):
    def construct(self):
        dot = Dot()
{repeated}
"""
        repaired, notes = compact_repetitive_pacing(code)
        report = analyze_generation_quality(repaired)

        self.assertEqual(report.play_call_count, 3)
        self.assertEqual(report.wait_call_count, 3)
        self.assertEqual(report.warnings, [])
        self.assertIn("drop repeated self.play calls after three repeats", notes)

    def test_caps_nonpaired_waits(self) -> None:
        waits = "\n".join(["        self.wait(1)"] * 12)
        code = f"""from manim import *

class Demo(Scene):
    def construct(self):
{waits}
"""
        repaired, notes = compact_repetitive_pacing(code)
        report = analyze_generation_quality(repaired)

        self.assertEqual(report.wait_call_count, 8)
        self.assertIn("drop waits beyond eight-call pacing budget", notes)

    def test_drops_dangling_bare_scene_method_references(self) -> None:
        code = """from manim import *

class Demo(Scene):
    def construct(self):
        dot = Dot()
        self.play(FadeIn(dot))
        self.wait
"""
        repaired, notes = compact_repetitive_pacing(code)

        self.assertIn("self.play(FadeIn(dot))", repaired)
        self.assertNotIn("self.wait\n", repaired)
        self.assertIn("drop dangling bare scene method references", notes)

    def test_caps_repeated_tracker_value_animation_sequences(self) -> None:
        tracker_steps = "\n".join(
            f"        self.play(tracker.animate.set_value({value}), run_time=2)"
            for value in [4, 6, 8, 0, 4, 6, 8, 0, 4, 6]
        )
        code = f"""from manim import *

class Demo(Scene):
    def construct(self):
        tracker = ValueTracker(0)
{tracker_steps}
"""
        repaired, notes = compact_repetitive_pacing(code)
        report = analyze_generation_quality(repaired)

        self.assertEqual(report.play_call_count, 6)
        self.assertLessEqual(report.estimated_duration_seconds, 12)
        self.assertIn("drop tracker value animations beyond six-step pacing budget", notes)


if __name__ == "__main__":
    unittest.main()
