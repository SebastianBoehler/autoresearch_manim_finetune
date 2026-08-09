from __future__ import annotations

import json
from pathlib import Path

SYSTEM = (
    "You write runnable Manim Community Edition Python files. Return only Python code, "
    "use `from manim import *`, and define exactly one scene class."
)


def main() -> None:
    output = Path("data/manim_api_error_refresh.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(record) + "\n" for record in _records()))
    print(json.dumps({"output": str(output), "num_records": len(_records())}, indent=2))


def _record(case_id: str, prompt: str, completion: str, must: list[str]) -> dict:
    return {
        "case_id": case_id,
        "system": SYSTEM,
        "prompt": prompt,
        "completion": completion.strip() + "\n",
        "tags": ["api-error-refresh", "fresh-failure", "duration:10s"],
        "entry_scene": completion.split("class ", 1)[1].split("(", 1)[0],
        "must_contain": must,
        "must_not_contain": [
            "ORANGE_D",
            "Rational(",
            ".background_rectangle",
            "Graph(",
            "get_vertical_line(",
            "resolution_by_sides",
            ", opacity=",
        ],
        "license": "MIT",
        "source_repo_path": "scripts/build_api_error_refresh_cases.py",
        "target_duration_seconds": 10,
        "target_duration_tolerance_seconds": 3,
    }


def _records() -> list[dict]:
    return [
        _record("api_error_attention_safe_colors", "Create a Manim scene showing two vectors and a weighted-average result. Use only valid Manim color constants.", ATTENTION, ["Vector(", "DecimalNumber(", "ORANGE"]),
        _record("api_error_fraction_no_rational", "Create a Manim scene comparing 1/2 and 2/4 on a unit interval without using Rational.", FRACTION, ["NumberLine(", "MathTex(", ".n2p("]),
        _record("api_error_numberline_background_panel", "Create a Manim scene with a NumberLine and a separate background panel behind its explanation label.", NUMBERLINE_PANEL, ["NumberLine(", "BackgroundRectangle(", "VGroup("]),
        _record("api_error_finance_axes_plot_lines", "Create a Manim scene comparing lump sum and DCA with Axes.plot_line_graph rather than Graph constructors.", FINANCE, ["Axes(", "plot_line_graph(", "Text("]),
        _record("api_error_matrix_entries_safe", "Create a Manim scene highlighting entries in a 2x2 Matrix using safe get_entries indexing.", MATRIX, ["Matrix(", "get_entries(", "SurroundingRectangle("]),
        _record("api_error_vertical_line_manual_color", "Create a Manim scene with a plotted curve and a colored vertical threshold line without passing color into get_vertical_line.", VERTICAL_LINE, ["Axes(", "Line(", "set_color("]),
        _record("api_error_surface_single_resolution", "Create a Manim ThreeDScene with a Surface that specifies resolution only once.", SURFACE, ["ThreeDScene", "Surface(", "resolution=("]),
        _record("api_error_compact_complete_scene", "Create a compact complete Manim scene with a title, diagram, label, and wait. Keep the code short and syntactically complete.", COMPACT, ["Text(", "Circle(", "Arrow("]),
    ]


ATTENTION = """
from manim import *

class AttentionSafeColors(Scene):
    def construct(self):
        title = Text("Weighted average of two signals", font_size=32).to_edge(UP)
        left = Vector(RIGHT + UP * 0.5, color=BLUE_D).shift(LEFT * 3)
        right = Vector(RIGHT + DOWN * 0.45, color=ORANGE).shift(LEFT * 3 + DOWN)
        weights = VGroup(DecimalNumber(0.7, color=BLUE_D), DecimalNumber(0.3, color=ORANGE)).arrange(DOWN).next_to(left, LEFT)
        result = Vector(RIGHT + UP * 0.2, color=GREEN).shift(RIGHT * 1.2 + DOWN * 0.45)
        label = MathTex("0.7v_1 + 0.3v_2", color=GREEN).next_to(result, DOWN)
        self.play(FadeIn(title), GrowArrow(left), GrowArrow(right), FadeIn(weights), run_time=2)
        self.play(GrowArrow(result), FadeIn(label), run_time=1.2)
        self.wait(1)
"""

FRACTION = """
from manim import *

class FractionNoImportFractions(Scene):
    def construct(self):
        title = Text("1/2 equals 2/4", font_size=34).to_edge(UP)
        line = NumberLine(x_range=[0, 1, 0.25], length=8, include_numbers=False)
        labels = VGroup(MathTex("0").next_to(line.n2p(0), DOWN), MathTex(r"\\frac{1}{2}").next_to(line.n2p(0.5), DOWN), MathTex(r"\\frac{2}{4}").next_to(line.n2p(0.5), UP), MathTex("1").next_to(line.n2p(1), DOWN))
        half = Line(line.n2p(0), line.n2p(0.5), color=BLUE, stroke_width=8)
        fourths = VGroup(Line(line.n2p(0), line.n2p(0.25), color=YELLOW, stroke_width=5), Line(line.n2p(0.25), line.n2p(0.5), color=YELLOW, stroke_width=5))
        self.play(FadeIn(title), Create(line), FadeIn(labels), run_time=1.6)
        self.play(Create(half), LaggedStart(*[Create(seg) for seg in fourths], lag_ratio=0.2), run_time=1.4)
        self.wait(1)
"""

NUMBERLINE_PANEL = """
from manim import *

class NumberLineBackgroundPanel(Scene):
    def construct(self):
        title = Text("Use a separate panel for explanation", font_size=32).to_edge(UP)
        line = NumberLine(x_range=[0, 8, 1], length=7, include_numbers=True)
        dot = Dot(line.n2p(5), color=YELLOW)
        label = Text("candidate value", font_size=24).next_to(dot, UP)
        panel_content = VGroup(Text("keep the right half", font_size=24), MathTex(r"x \\ge 4")).arrange(DOWN, aligned_edge=LEFT)
        panel = VGroup(BackgroundRectangle(panel_content, fill_opacity=0.18, buff=0.2), panel_content).to_corner(UR)
        self.play(FadeIn(title), Create(line), FadeIn(dot), FadeIn(label), run_time=1.8)
        self.play(FadeIn(panel), run_time=1)
        self.wait(1)
"""

FINANCE = """
from manim import *

class FinanceAxesPlotLines(Scene):
    def construct(self):
        title = Text("Lump sum vs DCA", font_size=34).to_edge(UP)
        axes = Axes(x_range=[0, 6, 1], y_range=[0, 8, 2], x_length=6, y_length=3.5).shift(LEFT * 1.2)
        lump = axes.plot_line_graph(x_values=[0, 1, 2, 3, 4, 5, 6], y_values=[1, 2.6, 3.2, 4.8, 5.6, 6.6, 7.4], line_color=BLUE, add_vertex_dots=False)
        dca = axes.plot_line_graph(x_values=[0, 1, 2, 3, 4, 5, 6], y_values=[0.4, 1.2, 2.1, 3.0, 4.2, 5.2, 6.1], line_color=YELLOW, add_vertex_dots=False)
        legend = VGroup(Text("blue: lump sum", font_size=22, color=BLUE), Text("yellow: DCA", font_size=22, color=YELLOW)).arrange(DOWN, aligned_edge=LEFT).to_corner(UR)
        self.play(FadeIn(title), Create(axes), run_time=1.5)
        self.play(Create(lump), Create(dca), FadeIn(legend), run_time=1.6)
        self.wait(1)
"""

MATRIX = """
from manim import *

class MatrixEntriesSafe(Scene):
    def construct(self):
        title = Text("Safe Matrix entry highlighting", font_size=32).to_edge(UP)
        matrix = Matrix([[2, 1], [1, 4]])
        entries = matrix.get_entries()
        box_a = SurroundingRectangle(entries[0], color=BLUE, buff=0.08)
        box_b = SurroundingRectangle(entries[3], color=YELLOW, buff=0.08)
        note = Text("2x2 matrix has four entries: 0, 1, 2, 3", font_size=22).next_to(matrix, DOWN)
        self.play(FadeIn(title), Write(matrix), run_time=1.6)
        self.play(Create(box_a), Create(box_b), FadeIn(note), run_time=1.2)
        self.wait(1)
"""

VERTICAL_LINE = """
from manim import *

class VerticalLineManualColor(Scene):
    def construct(self):
        title = Text("Threshold line is a normal Line", font_size=32).to_edge(UP)
        axes = Axes(x_range=[0, 10, 2], y_range=[0, 10, 2], x_length=6, y_length=3.5)
        curve = axes.plot(lambda x: 0.08 * (x - 5) ** 2 + 2, x_range=[0, 10], color=BLUE)
        threshold = Line(axes.c2p(5, 0), axes.c2p(5, 5), stroke_width=5).set_color(YELLOW)
        label = Text("threshold", font_size=22, color=YELLOW).next_to(threshold, UP)
        self.play(FadeIn(title), Create(axes), Create(curve), run_time=1.8)
        self.play(Create(threshold), FadeIn(label), run_time=1)
        self.wait(1)
"""

SURFACE = """
from manim import *

class SurfaceSingleResolution(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=60 * DEGREES, theta=-40 * DEGREES)
        axes = ThreeDAxes(x_range=[-2, 2, 1], y_range=[-2, 2, 1], z_range=[-1, 2, 1])
        surface = Surface(lambda u, v: axes.c2p(u, v, 0.25 * (u * u + v * v)), u_range=[-1.5, 1.5], v_range=[-1.5, 1.5], resolution=(12, 12), fill_opacity=0.75, checkerboard_colors=[TEAL_D, TEAL_E])
        label = Text("one resolution argument", font_size=24).to_corner(UL)
        self.add_fixed_in_frame_mobjects(label)
        self.play(FadeIn(label), Create(axes), FadeIn(surface), run_time=3)
        self.wait(1)
"""

COMPACT = """
from manim import *

class CompactCompleteScene(Scene):
    def construct(self):
        title = Text("Complete, short, and closed", font_size=32).to_edge(UP)
        start = Circle(radius=0.45, color=BLUE).shift(LEFT * 2)
        end = Circle(radius=0.45, color=GREEN).shift(RIGHT * 2)
        arrow = Arrow(start.get_right(), end.get_left(), buff=0.1, color=YELLOW)
        label = Text("transform", font_size=24).next_to(arrow, UP)
        self.play(FadeIn(title), Create(start), Create(end), GrowArrow(arrow), FadeIn(label), run_time=2)
        self.wait(1)
"""


if __name__ == "__main__":
    main()
