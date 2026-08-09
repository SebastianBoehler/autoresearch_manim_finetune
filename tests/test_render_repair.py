from __future__ import annotations

import unittest

from mac_pipeline.render_repair import repair_runtime_generated_code


class RenderRepairTests(unittest.TestCase):
    def test_rewrites_point_based_surrounding_rectangle_after_render_failure(self) -> None:
        code = """from manim import *

class Demo(Scene):
    def construct(self):
        line = NumberLine(x_range=[0, 10, 1])
        band = SurroundingRectangle(line.number_to_point(6) + RIGHT, width=2, color=BLUE, buff=0.05, fill_opacity=0.2)
"""
        repaired, notes = repair_runtime_generated_code(
            code,
            "TypeError: Expected all inputs for parameter mobjects to be a Mobjects",
        )

        self.assertIn("Rectangle(width=2, height=0.5, color=BLUE", repaired)
        self.assertIn("fill_opacity=0.2).move_to(line.number_to_point(6) + RIGHT)", repaired)
        self.assertIn("rewrite point-based SurroundingRectangle as moved Rectangle", notes)

    def test_leaves_valid_surrounding_rectangle_without_trigger_unchanged(self) -> None:
        code = "band = SurroundingRectangle(label, color=BLUE)\n"
        repaired, notes = repair_runtime_generated_code(code, "")

        self.assertEqual(repaired, code)
        self.assertEqual(notes, [])

    def test_removes_unsupported_numberline_tick_frequency_kwarg(self) -> None:
        code = (
            "line = NumberLine(x_range=[0, 1, 1/4], "
            "numbers_to_include=[0, 1/4, 1], unit_size=0.8, tick_frequency=0.25)\n"
        )
        repaired, notes = repair_runtime_generated_code(
            code,
            "TypeError: Mobject.__init__() got an unexpected keyword argument 'tick_frequency'",
        )

        self.assertNotIn("tick_frequency", repaired)
        self.assertIn("unit_size=0.8", repaired)
        self.assertIn("remove unsupported NumberLine tick_frequency kwarg", notes)

    def test_rewrites_number_range_between_after_attribute_error(self) -> None:
        code = "interval = number_line.number_range_between(-1.5, 1.5)\n"
        repaired, notes = repair_runtime_generated_code(
            code,
            "AttributeError: NumberLine object has no attribute 'number_range_between'",
        )

        self.assertIn(
            "interval = [number_line.number_to_point(-1.5), number_line.number_to_point(1.5)]",
            repaired,
        )
        self.assertIn("rewrite NumberLine.number_range_between", notes)

    def test_repairs_additional_broad_render_failures(self) -> None:
        code = "\n".join(
            [
                "matrix = Matrix([[1]], include_background_box=True, background_box_style={'color': BLUE})",
                "self.play(matrix.animate.set_matrix([[2]]), matrix.animate.set_opacity(1))",
                "self.play(rotate_surface(surface, angle=PI))",
                "particle = Dot(fieldORIGIN)",
                "table = MathTable([[1]], include_outer_lines=True, include_outer_lines=True)",
                "label = Text('x').next_to(circle, UP, buff=0.1)",
                "start = graph.get_vertices()[0]",
                "rest = graph.get_vertices()[1:]",
                "axis.set_x_range(0, 1)",
                "dot = always_redraw(lambda: Dot(axis.i2gp(tracker.get_value(), axis)))",
                "rect = Rectangle(height=curve.get_y1(i) - curve.get_y0(i))",
                "readout = DecimalNumber(equilibrium_curve.get_y(equilibrium_curve.x_data[0]))",
                "self.play(MoveAlongPath(particle, path))",
                "field = ArrowVectorField(fn, x_range=[-2, 2], y_range=[-2, 2])",
                "path_a = TracedPath(particle_a.get_center)",
                "self.play(Indicate(path_a))",
                "self.play(GrowDot(dot), GrowArrow(brace), run_time=10)",
                "summary = MathTable([[1]], include_first_row=False, include_first_column=False, column_widths=[1], font_size=24)",
                "summary.add_hline(1, color=BLUE)",
            ]
        )
        repaired, notes = repair_runtime_generated_code(
            code,
            "unexpected keyword argument 'include_background_box'\n"
            "unexpected keyword argument 'background_box_style'\n"
            "name 'rotate_surface' is not defined\n"
            "name 'fieldORIGIN' is not defined\n"
            "keyword argument repeated: include_outer_lines\n"
            "name 'circle' is not defined\n"
            "KeyError: 0\n"
            "setter() takes 2 positional arguments but 3 were given\n"
            "getter() takes 1 positional argument but 2 were given\n"
            "name 'equilibrium_curve' is not defined\n"
            "render timed out after 90s\n"
            "name 'GrowDot' is not defined\n"
            "unexpected keyword argument 'include_first_row'\n"
            "unexpected keyword argument 'font_size'",
        )

        self.assertNotIn("include_background_box", repaired)
        self.assertNotIn("background_box_style", repaired)
        self.assertNotIn(".set_matrix", repaired)
        self.assertIn("Rotate(surface, angle=PI)", repaired)
        self.assertIn("Dot(ORIGIN)", repaired)
        self.assertEqual(repaired.count("include_outer_lines"), 1)
        self.assertIn("Text('x').shift(UP * 0.18)", repaired)
        self.assertIn("start = list(graph.vertices.values())[0]", repaired)
        self.assertIn("rest = list(graph.vertices.values())[1:]", repaired)
        self.assertNotIn("axis.set_x_range", repaired)
        self.assertIn("axis.c2p(tracker.get_value(), 0.5)", repaired)
        self.assertIn("height=1.0", repaired)
        self.assertIn("DecimalNumber(2.8)", repaired)
        self.assertIn("particle.animate.shift(RIGHT * 0.6)", repaired)
        self.assertIn("x_range=[-2, 2, 1]", repaired)
        self.assertIn("y_range=[-2, 2, 1]", repaired)
        self.assertNotIn("TracedPath", repaired)
        self.assertIn("Indicate(particle_a)", repaired)
        self.assertIn("GrowFromCenter(dot)", repaired)
        self.assertIn("GrowFromCenter(brace)", repaired)
        self.assertIn("run_time=3", repaired)
        self.assertNotIn("include_first_row", repaired)
        self.assertNotIn("include_first_column", repaired)
        self.assertNotIn("column_widths", repaired)
        self.assertNotIn("font_size=24", repaired)
        self.assertNotIn("add_hline", repaired)
        self.assertTrue(notes)


if __name__ == "__main__":
    unittest.main()
