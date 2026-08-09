from __future__ import annotations

import json
from pathlib import Path

SYSTEM = (
    "You write runnable Manim Community Edition Python files. Return only Python code, "
    "use `from manim import *`, and define exactly one scene class."
)


def main() -> None:
    output = Path("data/manim_raw_failure_refresh.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(record) + "\n" for record in _records()))
    print(json.dumps({"output": str(output), "num_records": len(_records())}, indent=2))


def _record(
    case_id: str,
    prompt: str,
    completion: str,
    tags: list[str],
    must_contain: list[str],
    duration: int,
) -> dict:
    return {
        "case_id": case_id,
        "system": SYSTEM,
        "prompt": prompt,
        "completion": completion.strip() + "\n",
        "tags": ["raw-failure-refresh", *tags, f"duration:{duration}s"],
        "entry_scene": _scene_name(completion),
        "must_contain": must_contain,
        "must_not_contain": [
            ", opacity=",
            "alpha=",
            "numbers_with_labels",
            "add_numbers_to_tips",
            "background_color=",
        ],
        "license": "MIT",
        "source_repo_path": "scripts/build_raw_failure_refresh_cases.py",
        "target_duration_seconds": duration,
        "target_duration_tolerance_seconds": max(2, duration // 5),
    }


def _scene_name(code: str) -> str:
    for line in code.splitlines():
        stripped = line.strip()
        if stripped.startswith("class ") and "(Scene)" in stripped:
            return stripped.split()[1].split("(")[0]
        if stripped.startswith("class ") and "(ThreeDScene)" in stripped:
            return stripped.split()[1].split("(")[0]
    raise ValueError("completion has no Scene class")


def _records() -> list[dict]:
    return [
        _record(
            "raw_failure_binary_search_fill_opacity",
            "Create a short Manim scene showing binary search shrinking an interval. Use translucent interval bands safely and avoid bare opacity keyword arguments.",
            BINARY_SEARCH,
            ["math", "algorithm", "binary-search", "opacity", "5s"],
            ["NumberLine(", "Rectangle(", "fill_opacity=", "BraceBetweenPoints("],
            5,
        ),
        _record(
            "raw_failure_surrounding_rectangle_geometry",
            "Create a Manim scene that highlights an algebra step and a number-line interval using valid SurroundingRectangle geometry.",
            SURROUNDING_RECTANGLE,
            ["math", "geometry", "highlight", "5s"],
            ["SurroundingRectangle(", "VGroup(", "NumberLine("],
            5,
        ),
        _record(
            "raw_failure_matrix_background_highlight",
            "Create a Manim scene explaining a 2x2 matrix update with a safe background panel and highlighted entries. Do not pass background kwargs into Matrix.",
            MATRIX_HIGHLIGHT,
            ["math", "matrix", "highlight", "5s"],
            ["Matrix(", "BackgroundRectangle(", "SurroundingRectangle("],
            5,
        ),
        _record(
            "raw_failure_fast_riemann_refinement",
            "Create a fast-rendering Manim scene that compares coarse and fine Riemann rectangles under one curve.",
            RIEMANN_REFINEMENT,
            ["math", "calculus", "riemann-sum", "10s"],
            ["Axes(", "get_riemann_rectangles(", "Transform("],
            10,
        ),
        _record(
            "raw_failure_coordinate_labels_manual",
            "Create a Manim scene on a NumberPlane with points, labels, and a vector, using manual labels instead of invented axis helper arguments.",
            COORDINATE_LABELS,
            ["math", "coordinate-plane", "labels", "5s"],
            ["NumberPlane(", "Dot(", "Arrow(", "Text("],
            5,
        ),
        _record(
            "raw_failure_tracker_table_bounded_rows",
            "Create a Manim scene with a small tracker table that updates through three rows without any out-of-range indexing.",
            TRACKER_TABLE,
            ["data", "tracker", "table", "10s"],
            ["ValueTracker(", "VGroup(", "SurroundingRectangle("],
            10,
        ),
        _record(
            "raw_failure_vector_field_manual_arrows",
            "Create a Manim scene comparing a simple vector field with a few manual arrows and particle dots, avoiding invented vector-field helper functions.",
            VECTOR_FIELD,
            ["physics", "vector-field", "particles", "10s"],
            ["NumberPlane(", "Arrow(", "Dot("],
            10,
        ),
        _record(
            "raw_failure_safe_3d_surface_camera",
            "Create a Manim ThreeDScene with axes, a smooth surface, and a clear camera angle using standard ManimCE 3D APIs.",
            SURFACE_3D,
            ["docs", "3d", "surface", "10s"],
            ["ThreeDScene", "ThreeDAxes(", "Surface(", "set_camera_orientation("],
            10,
        ),
    ]


BINARY_SEARCH = """
from manim import *

class BinarySearchFillOpacitySafe(Scene):
    def construct(self):
        title = Text("Binary search: shrink the possible interval", font_size=32).to_edge(UP)
        line = NumberLine(x_range=[0, 16, 2], length=10, include_numbers=True).shift(DOWN * 0.3)
        stages = [(0, 16, BLUE_D, "start"), (0, 8, TEAL_D, "left half"), (4, 8, ORANGE, "answer band")]
        bands = VGroup()
        labels = VGroup()
        for low, high, color, label in stages:
            width = line.n2p(high)[0] - line.n2p(low)[0]
            center = (line.n2p(low) + line.n2p(high)) / 2 + DOWN * 0.45
            band = Rectangle(width=width, height=0.24, stroke_width=0, fill_color=color, fill_opacity=0.28).move_to(center)
            bands.add(band)
            labels.add(Text(label, font_size=22, color=color).next_to(band, DOWN, buff=0.12))
        brace = BraceBetweenPoints(line.n2p(4), line.n2p(8), DOWN)
        brace_label = MathTex(r"4\\ candidates").next_to(brace, DOWN)
        self.play(FadeIn(title), Create(line), run_time=1.5)
        self.play(FadeIn(bands[0]), FadeIn(labels[0]), run_time=1.2)
        self.play(ReplacementTransform(bands[0].copy(), bands[1]), FadeIn(labels[1]), run_time=1.2)
        self.play(ReplacementTransform(bands[1].copy(), bands[2]), FadeIn(labels[2]), run_time=1.2)
        self.play(GrowFromCenter(brace), FadeIn(brace_label), run_time=1)
        self.wait(0.8)
"""

SURROUNDING_RECTANGLE = """
from manim import *

class SurroundingRectangleGeometrySafe(Scene):
    def construct(self):
        title = Text("Highlight objects, not raw coordinates", font_size=32).to_edge(UP)
        eq1 = MathTex("2x + 6 = 14")
        eq2 = MathTex("2x = 8")
        eq3 = MathTex("x = 4")
        equations = VGroup(eq1, eq2, eq3).arrange(DOWN, aligned_edge=LEFT, buff=0.28).shift(LEFT * 2)
        box = SurroundingRectangle(eq2, color=YELLOW, buff=0.14)
        line = NumberLine(x_range=[0, 8, 1], length=5, include_numbers=True).shift(RIGHT * 2.2 + DOWN * 0.25)
        left_dot = Dot(line.n2p(0), color=BLUE_D)
        answer_dot = Dot(line.n2p(4), color=YELLOW)
        interval = Line(left_dot.get_center(), answer_dot.get_center(), color=YELLOW, stroke_width=8)
        interval_box = SurroundingRectangle(VGroup(left_dot, answer_dot, interval), color=TEAL, buff=0.18)
        label = Text("valid: rectangle wraps a VGroup", font_size=22, color=TEAL).next_to(interval_box, DOWN)
        self.play(FadeIn(title), Write(equations), run_time=2)
        self.play(Create(box), run_time=1)
        self.play(Create(line), FadeIn(left_dot), FadeIn(answer_dot), Create(interval), run_time=1.5)
        self.play(Create(interval_box), FadeIn(label), run_time=1)
        self.wait(0.8)
"""

MATRIX_HIGHLIGHT = """
from manim import *

class MatrixBackgroundHighlight(Scene):
    def construct(self):
        title = Text("Update one matrix entry", font_size=34).to_edge(UP)
        matrix = Matrix([[2, 1], [1, 3]]).scale(0.9)
        panel = BackgroundRectangle(matrix, fill_opacity=0.12, buff=0.28)
        entry = matrix.get_entries()[3]
        highlight = SurroundingRectangle(entry, color=ORANGE, buff=0.08)
        note = Text("background is a separate mobject", font_size=24, color=TEAL).next_to(matrix, DOWN)
        update = MathTex("a_{22}: 3 \\rightarrow 4", color=ORANGE).next_to(note, DOWN)
        self.play(FadeIn(title), FadeIn(panel), Write(matrix), run_time=2)
        self.play(Create(highlight), FadeIn(note), run_time=1)
        self.play(Write(update), entry.animate.set_color(ORANGE), run_time=1)
        self.wait(1)
"""

RIEMANN_REFINEMENT = """
from manim import *

class FastRiemannRefinement(Scene):
    def construct(self):
        title = Text("Finer rectangles reduce area error", font_size=32).to_edge(UP)
        axes = Axes(x_range=[0, 4, 1], y_range=[0, 5, 1], x_length=7, y_length=4).shift(DOWN * 0.4)
        graph = axes.plot(lambda x: 0.25 * x * x + 0.7, x_range=[0, 4], color=YELLOW)
        coarse = axes.get_riemann_rectangles(graph, x_range=[0, 4], dx=0.8, input_sample_type="center", fill_opacity=0.55, stroke_width=1)
        fine = axes.get_riemann_rectangles(graph, x_range=[0, 4], dx=0.4, input_sample_type="center", fill_opacity=0.55, stroke_width=1)
        coarse_label = Text("coarse", font_size=24, color=BLUE).next_to(axes, LEFT)
        fine_label = Text("fine", font_size=24, color=GREEN).move_to(coarse_label)
        self.play(FadeIn(title), Create(axes), Create(graph), run_time=2)
        self.play(FadeIn(coarse), FadeIn(coarse_label), run_time=1.5)
        self.play(Transform(coarse, fine), ReplacementTransform(coarse_label, fine_label), run_time=1.5)
        self.wait(1)
"""

COORDINATE_LABELS = """
from manim import *

class CoordinateLabelsManual(Scene):
    def construct(self):
        title = Text("Manual labels keep coordinate scenes explicit", font_size=30).to_edge(UP)
        plane = NumberPlane(x_range=[-3, 4, 1], y_range=[-2, 3, 1], x_length=7, y_length=4)
        x_label = Text("x", font_size=24).next_to(plane.x_axis.get_end(), RIGHT)
        y_label = Text("y", font_size=24).next_to(plane.y_axis.get_end(), UP)
        start = Dot(plane.c2p(0, 0), color=BLUE)
        end = Dot(plane.c2p(2, 1), color=YELLOW)
        vector = Arrow(start.get_center(), end.get_center(), buff=0.08, color=YELLOW)
        coord = MathTex("(2,1)", color=YELLOW).next_to(end, UR, buff=0.12)
        self.play(FadeIn(title), Create(plane), FadeIn(x_label), FadeIn(y_label), run_time=2)
        self.play(FadeIn(start), GrowArrow(vector), FadeIn(end), Write(coord), run_time=1.6)
        self.wait(1)
"""

TRACKER_TABLE = """
from manim import *

class TrackerTableBoundedRows(Scene):
    def construct(self):
        title = Text("Each tracker step has one safe table row", font_size=31).to_edge(UP)
        tracker = ValueTracker(0)
        rows = [("start", "0.20"), ("mid", "0.55"), ("final", "0.82")]
        table_rows = VGroup()
        for index, (name, value) in enumerate(rows):
            cells = VGroup(Text(name, font_size=24), Text(value, font_size=24, color=YELLOW)).arrange(RIGHT, buff=0.8)
            table_rows.add(cells.shift(DOWN * 0.45 * index))
        table = VGroup(*table_rows).arrange(DOWN, aligned_edge=LEFT, buff=0.18).shift(LEFT * 2)
        pointer = SurroundingRectangle(table_rows[0], color=TEAL, buff=0.12)
        bar_back = Rectangle(width=3.2, height=0.22, fill_color=GRAY, fill_opacity=0.25, stroke_width=0).shift(RIGHT * 2)
        bar = always_redraw(lambda: Rectangle(width=3.2 * tracker.get_value(), height=0.22, fill_color=YELLOW, fill_opacity=0.8, stroke_width=0).align_to(bar_back, LEFT).move_to(bar_back, aligned_edge=LEFT))
        self.play(FadeIn(title), FadeIn(table), FadeIn(pointer), FadeIn(bar_back), FadeIn(bar), run_time=2)
        for index, (_, value) in enumerate(rows[1:], start=1):
            self.play(tracker.animate.set_value(float(value)), pointer.animate.move_to(table_rows[index]), run_time=1.2)
        self.wait(0.8)
"""

VECTOR_FIELD = """
from manim import *

class ManualVectorFieldArrows(Scene):
    def construct(self):
        title = Text("Manual arrows: simple, stable vector-field comparison", font_size=29).to_edge(UP)
        plane = NumberPlane(x_range=[-3, 4, 1], y_range=[-2, 3, 1], x_length=7, y_length=4).shift(DOWN * 0.2)
        arrows = VGroup()
        for x in [-2, 0, 2]:
            for y in [-1, 1]:
                start = plane.c2p(x, y)
                end = plane.c2p(x + 0.45, y + 0.25 * (1 if x <= 0 else -1))
                arrows.add(Arrow(start, end, buff=0, stroke_width=4, max_tip_length_to_length_ratio=0.22, color=BLUE_D))
        particles = VGroup(Dot(plane.c2p(-2, -1), color=YELLOW), Dot(plane.c2p(0, 1), color=YELLOW), Dot(plane.c2p(2, -1), color=YELLOW))
        caption = Text("No hidden helpers: every arrow has explicit start and end points.", font_size=22).to_edge(DOWN)
        self.play(FadeIn(title), Create(plane), run_time=1.5)
        self.play(LaggedStart(*[GrowArrow(arrow) for arrow in arrows], lag_ratio=0.08), FadeIn(particles), run_time=2)
        self.play(*[dot.animate.shift(RIGHT * 0.45) for dot in particles], FadeIn(caption), run_time=1.5)
        self.wait(1)
"""

SURFACE_3D = """
from manim import *

class SafeSurfaceCamera3D(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=62 * DEGREES, theta=-45 * DEGREES, zoom=0.85)
        axes = ThreeDAxes(x_range=[-2, 2, 1], y_range=[-2, 2, 1], z_range=[-1, 2, 1])
        surface = Surface(lambda u, v: axes.c2p(u, v, 0.35 * (u * u - v * v)), u_range=[-1.6, 1.6], v_range=[-1.6, 1.6], resolution=(14, 14), checkerboard_colors=[BLUE_D, BLUE_E], fill_opacity=0.78)
        label = Text("standard ThreeDScene camera + Surface", font_size=24).to_corner(UL)
        self.add_fixed_in_frame_mobjects(label)
        self.play(FadeIn(label), Create(axes), run_time=2)
        self.play(FadeIn(surface), run_time=2)
        self.begin_ambient_camera_rotation(rate=0.12)
        self.wait(2)
        self.stop_ambient_camera_rotation()
"""


if __name__ == "__main__":
    main()
