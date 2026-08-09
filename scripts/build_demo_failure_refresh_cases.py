from __future__ import annotations

import json
from pathlib import Path

SYSTEM = (
    "You write runnable Manim Community Edition Python files. Return only Python code, "
    "use `from manim import *`, and define exactly one scene class."
)


def main() -> None:
    output = Path("data/manim_demo_failure_refresh.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(record) + "\n" for record in _records()))
    print(json.dumps({"output": str(output), "num_records": len(_records())}, indent=2))


def _record(case_id: str, prompt: str, completion: str, must: list[str]) -> dict:
    return {
        "case_id": case_id,
        "system": SYSTEM,
        "prompt": prompt,
        "completion": completion.strip() + "\n",
        "tags": ["demo-failure-refresh", "learning-app", "api-safety", "duration:10s"],
        "entry_scene": completion.split("class ", 1)[1].split("(", 1)[0],
        "must_contain": must,
        "must_not_contain": ["axis.c2p(", "tick_frequency=", ", opacity=", "alpha="],
        "license": "MIT",
        "source_repo_path": "scripts/build_demo_failure_refresh_cases.py",
        "target_duration_seconds": 10,
        "target_duration_tolerance_seconds": 3,
    }


def _records() -> list[dict]:
    return [
        _record(
            "demo_failure_binary_search_numberline_n2p",
            "Create a short Manim scene showing binary search shrinking an interval on a NumberLine. Use NumberLine.n2p for positions and translucent bands with fill_opacity.",
            BINARY,
            ["NumberLine(", ".n2p(", "Rectangle(", "fill_opacity="],
        ),
        _record(
            "demo_failure_fraction_unit_interval_no_tick_frequency",
            "Create a Manim scene revealing three fourths on a unit interval. Avoid tick_frequency and place fraction labels manually.",
            FRACTION,
            ["NumberLine(", "MathTex(", "Line(", ".n2p("],
        ),
        _record(
            "demo_failure_confidence_interval_fill_band",
            "Create a Manim scene explaining a confidence interval band. Use a Rectangle with fill_opacity rather than opacity on SurroundingRectangle.",
            CONFIDENCE,
            ["NumberLine(", "Rectangle(", "fill_opacity=", "BraceBetweenPoints("],
        ),
    ]


BINARY = """
from manim import *

class BinarySearchNumberLineN2P(Scene):
    def construct(self):
        title = Text("Binary search narrows the range", font_size=34).to_edge(UP)
        axis = NumberLine(x_range=[0, 10, 1], numbers_to_include=list(range(11)), include_numbers=True, include_tip=False, length=9).shift(DOWN * 0.2)
        intervals = [(0, 10, BLUE_D, "all values"), (5, 10, TEAL_D, "keep right half"), (5, 7, ORANGE, "final window")]
        bands = VGroup()
        labels = VGroup()
        for low, high, color, label in intervals:
            start = axis.n2p(low)
            end = axis.n2p(high)
            band = Rectangle(width=end[0] - start[0], height=0.24, fill_color=color, fill_opacity=0.25, stroke_width=0)
            band.move_to((start + end) / 2 + DOWN * 0.45)
            bands.add(band)
            labels.add(Text(label, font_size=22, color=color).next_to(band, DOWN, buff=0.1))
        target = Dot(axis.n2p(6), color=YELLOW)
        self.play(FadeIn(title), Create(axis), FadeIn(target), run_time=1.6)
        self.play(FadeIn(bands[0]), FadeIn(labels[0]), run_time=0.9)
        self.play(ReplacementTransform(bands[0].copy(), bands[1]), FadeIn(labels[1]), run_time=0.9)
        self.play(ReplacementTransform(bands[1].copy(), bands[2]), FadeIn(labels[2]), run_time=0.9)
        self.wait(0.8)
"""

FRACTION = """
from manim import *

class FractionUnitIntervalNoTickFrequency(Scene):
    def construct(self):
        title = Text("Three fourths on the unit interval", font_size=34).to_edge(UP)
        line = NumberLine(x_range=[0, 1, 0.25], length=8, include_numbers=False, include_tip=True).shift(DOWN * 0.1)
        labels = VGroup(
            MathTex("0").next_to(line.n2p(0), DOWN),
            MathTex(r"\\frac{1}{4}").next_to(line.n2p(0.25), DOWN),
            MathTex(r"\\frac{1}{2}").next_to(line.n2p(0.5), DOWN),
            MathTex(r"\\frac{3}{4}").next_to(line.n2p(0.75), DOWN),
            MathTex("1").next_to(line.n2p(1), DOWN),
        )
        segments = VGroup()
        for index in range(3):
            segments.add(Line(line.n2p(index / 4), line.n2p((index + 1) / 4), color=YELLOW, stroke_width=9))
        brace = BraceBetweenPoints(line.n2p(0), line.n2p(0.75), UP)
        brace_label = MathTex(r"\\frac{3}{4}", color=YELLOW).next_to(brace, UP)
        self.play(FadeIn(title), Create(line), FadeIn(labels), run_time=1.8)
        self.play(LaggedStart(*[Create(segment) for segment in segments], lag_ratio=0.2), run_time=1.4)
        self.play(GrowFromCenter(brace), FadeIn(brace_label), run_time=1)
        self.wait(0.8)
"""

CONFIDENCE = """
from manim import *

class ConfidenceIntervalFillBand(Scene):
    def construct(self):
        title = Text("Confidence interval = estimate plus uncertainty", font_size=32).to_edge(UP)
        axis = NumberLine(x_range=[40, 80, 10], numbers_to_include=[40, 50, 60, 70, 80], include_numbers=True, length=8).shift(DOWN * 0.2)
        low = axis.n2p(52)
        high = axis.n2p(68)
        center = axis.n2p(60)
        band = Rectangle(width=high[0] - low[0], height=0.28, fill_color=GREEN, fill_opacity=0.25, stroke_color=GREEN, stroke_width=2)
        band.move_to((low + high) / 2 + DOWN * 0.42)
        estimate = Dot(center, color=YELLOW, radius=0.08)
        brace = BraceBetweenPoints(low, high, DOWN)
        label = MathTex(r"95\\%\\ interval", color=GREEN).next_to(brace, DOWN)
        note = Text("the band is a filled Rectangle, not opacity on a wrapper", font_size=22).to_edge(DOWN)
        self.play(FadeIn(title), Create(axis), FadeIn(estimate), run_time=1.6)
        self.play(FadeIn(band), GrowFromCenter(brace), FadeIn(label), run_time=1.4)
        self.play(FadeIn(note), run_time=0.8)
        self.wait(0.8)
"""


if __name__ == "__main__":
    main()
