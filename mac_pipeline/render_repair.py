from __future__ import annotations

import re

from mac_pipeline.render_repair_rules import (
    remove_constructor_kwarg,
    remove_repeated_kwarg,
    repair_curve_getters,
    repair_equilibrium_readouts,
    repair_matrix_set_matrix,
    repair_number_range_between,
    repair_surrounding_rectangle_point_line,
)
_NON_MOBJECT_SURROUNDING_RECT_TRIGGER = re.compile(
    r"Expected all inputs for parameter mobjects to be a Mobjects"
)
_UNSUPPORTED_TICK_FREQUENCY_TRIGGER = re.compile(
    r"unexpected keyword argument\s+'tick_frequency'"
)
_NUMBER_RANGE_BETWEEN_TRIGGER = re.compile(r"number_range_between")
_UNSUPPORTED_INCLUDE_BACKGROUND_TRIGGER = re.compile(
    r"unexpected keyword argument\s+'(?:include_background_box|background_box_style)'"
)
_ROTATE_SURFACE_TRIGGER = re.compile(r"name 'rotate_surface' is not defined")
_FIELD_ORIGIN_TRIGGER = re.compile(r"name '[A-Za-z_]\w*ORIGIN' is not defined")
_REPEATED_KEYWORD_TRIGGER = re.compile(r"keyword argument repeated:\s*([A-Za-z_]\w*)")
_UNDEFINED_CIRCLE_TRIGGER = re.compile(r"name 'circle' is not defined")
_GRAPH_VERTEX_INDEX_TRIGGER = re.compile(r"KeyError:\s*0")
_AXES_SETTER_TRIGGER = re.compile(r"set_[xy]_range|set_axis_labels|setter\(\) takes 2 positional")
_CURVE_GETTER_TRIGGER = re.compile(r"get_y[01]|getter\(\) takes 1 positional")
_UNDEFINED_EQUILIBRIUM_TRIGGER = re.compile(r"name 'equilibrium_curve' is not defined")
_RENDER_TIMEOUT_TRIGGER = re.compile(r"render timed out")
_GROWDOT_TRIGGER = re.compile(r"name 'GrowDot' is not defined")
_MATHTABLE_KWARG_TRIGGER = re.compile(
    r"unexpected keyword argument\s+'(?:include_first_row|include_first_column|column_widths|font_size)'"
)


def repair_runtime_generated_code(code: str, render_log_tail: str) -> tuple[str, list[str]]:
    repair_surrounding_rect = _NON_MOBJECT_SURROUNDING_RECT_TRIGGER.search(render_log_tail)
    remove_tick_frequency = _UNSUPPORTED_TICK_FREQUENCY_TRIGGER.search(render_log_tail)
    repair_number_range = _NUMBER_RANGE_BETWEEN_TRIGGER.search(render_log_tail)
    remove_background = _UNSUPPORTED_INCLUDE_BACKGROUND_TRIGGER.search(render_log_tail)
    repair_rotate_surface = _ROTATE_SURFACE_TRIGGER.search(render_log_tail)
    repair_field_origin = _FIELD_ORIGIN_TRIGGER.search(render_log_tail)
    repeated_keyword = _REPEATED_KEYWORD_TRIGGER.search(render_log_tail)
    repair_circle_ref = _UNDEFINED_CIRCLE_TRIGGER.search(render_log_tail)
    repair_graph_index = _GRAPH_VERTEX_INDEX_TRIGGER.search(render_log_tail)
    repair_axes_setter = _AXES_SETTER_TRIGGER.search(render_log_tail)
    repair_curve_getter = _CURVE_GETTER_TRIGGER.search(render_log_tail)
    repair_equilibrium = _UNDEFINED_EQUILIBRIUM_TRIGGER.search(render_log_tail)
    repair_timeout = _RENDER_TIMEOUT_TRIGGER.search(render_log_tail)
    repair_growdot = _GROWDOT_TRIGGER.search(render_log_tail)
    repair_mathtable_kwargs = _MATHTABLE_KWARG_TRIGGER.search(render_log_tail)
    if not any(
        [
            repair_surrounding_rect,
            remove_tick_frequency,
            repair_number_range,
            remove_background,
            repair_rotate_surface,
            repair_field_origin,
            repeated_keyword,
            repair_circle_ref,
            repair_graph_index,
            repair_axes_setter,
            repair_curve_getter,
            repair_equilibrium,
            repair_timeout,
            repair_growdot,
            repair_mathtable_kwargs,
        ]
    ):
        return code, []

    lines: list[str] = []
    notes: list[str] = []
    for line in code.splitlines(keepends=True):
        repaired = line
        if repair_surrounding_rect:
            repaired = repair_surrounding_rectangle_point_line(repaired)
        if repaired != line:
            _add_note(notes, "rewrite point-based SurroundingRectangle as moved Rectangle")
        if remove_tick_frequency:
            next_repaired = remove_constructor_kwarg(repaired, "NumberLine", "tick_frequency")
            if next_repaired != repaired:
                _add_note(notes, "remove unsupported NumberLine tick_frequency kwarg")
            repaired = next_repaired
        if repair_number_range:
            next_repaired = repair_number_range_between(repaired)
            if next_repaired != repaired:
                _add_note(notes, "rewrite NumberLine.number_range_between")
            repaired = next_repaired
        if remove_background:
            next_repaired = remove_constructor_kwarg(repaired, "Matrix", "include_background_box")
            if next_repaired != repaired:
                _add_note(notes, "remove unsupported Matrix include_background_box kwarg")
            repaired = next_repaired
            next_repaired = remove_constructor_kwarg(repaired, "Matrix", "background_box_style")
            if next_repaired != repaired:
                _add_note(notes, "remove unsupported Matrix background_box_style kwarg")
            repaired = repair_matrix_set_matrix(next_repaired)
            if repaired != next_repaired:
                _add_note(notes, "replace unsupported Matrix.set_matrix animation")
        if repair_rotate_surface:
            next_repaired = repaired.replace("rotate_surface(", "Rotate(")
            if next_repaired != repaired:
                _add_note(notes, "replace invented rotate_surface helper with Rotate")
            repaired = next_repaired
        if repair_field_origin:
            next_repaired = re.sub(r"\b[A-Za-z_]\w*ORIGIN\b", "ORIGIN", repaired)
            if next_repaired != repaired:
                _add_note(notes, "repair malformed get_origin replacement")
            repaired = next_repaired
        if repeated_keyword:
            keyword = repeated_keyword.group(1)
            next_repaired = remove_repeated_kwarg(repaired, keyword)
            if next_repaired != repaired:
                _add_note(notes, f"remove repeated {keyword} kwarg")
            repaired = next_repaired
        if repair_circle_ref:
            next_repaired = re.sub(r"\.next_to\(circle,\s*[^)]+\)", ".shift(UP * 0.18)", repaired)
            if next_repaired != repaired:
                _add_note(notes, "replace undefined circle-relative labels with local shifts")
            repaired = next_repaired
        if repair_graph_index:
            next_repaired = re.sub(
                r"(\b[A-Za-z_]\w*)\.get_vertices\(\)\[(0|1:)\]",
                lambda match: f"list({match.group(1)}.vertices.values())[{match.group(2)}]",
                repaired,
            )
            if next_repaired != repaired:
                _add_note(notes, "rewrite Graph.get_vertices indexing to vertices values")
            repaired = next_repaired
        if repair_axes_setter:
            if re.match(r"^\s*\w+\.set_(?:x_range|y_range|axis_labels)\(", repaired):
                _add_note(notes, "drop unsupported Axes setter calls")
                repaired = ""
            next_repaired = re.sub(
                r"(\b[A-Za-z_]\w*)\.i2gp\(([^,]+),\s*\1\)",
                r"\1.c2p(\2, 0.5)",
                repaired,
            )
            if next_repaired != repaired:
                _add_note(notes, "rewrite Axes.i2gp self-reference to c2p")
            repaired = next_repaired
        if repair_curve_getter:
            next_repaired = repair_curve_getters(repaired)
            if next_repaired != repaired:
                _add_note(notes, "replace invented curve get_y0/get_y1 accessors")
            repaired = next_repaired
        if repair_equilibrium:
            next_repaired = repair_equilibrium_readouts(repaired)
            if next_repaired != repaired:
                _add_note(notes, "replace undefined curve readouts with numeric readouts")
            repaired = next_repaired
        if repair_growdot:
            next_repaired = repaired.replace("GrowDot(", "GrowFromCenter(")
            if next_repaired != repaired:
                _add_note(notes, "replace unsupported GrowDot animation")
            repaired = next_repaired
        if repair_mathtable_kwargs:
            for kwarg in ("include_first_row", "include_first_column", "column_widths", "font_size"):
                next_repaired = remove_constructor_kwarg(repaired, "MathTable", kwarg)
                if next_repaired != repaired:
                    _add_note(notes, f"remove unsupported MathTable {kwarg} kwarg")
                repaired = next_repaired
            if re.match(r"^\s*\w+\.add_[hv]line\(", repaired):
                _add_note(notes, "drop unsupported MathTable line styling calls")
                repaired = ""
        if repair_timeout:
            if "TracedPath(" in repaired:
                _add_note(notes, "drop timeout-prone TracedPath helpers")
                repaired = ""
            if "ArrowVectorField(" in repaired:
                next_repaired = _coarsen_vector_field_line(repaired)
                if next_repaired != repaired:
                    _add_note(notes, "coarsen timeout-prone ArrowVectorField grid")
                repaired = next_repaired
            next_repaired = re.sub(
                r"MoveAlongPath\(\s*([A-Za-z_]\w*)\s*,\s*[^)]+\)",
                r"\1.animate.shift(RIGHT * 0.6)",
                repaired,
            )
            if next_repaired != repaired:
                _add_note(notes, "replace timeout-prone traced MoveAlongPath calls")
            repaired = next_repaired
            next_repaired = re.sub(r"Indicate\(path_([A-Za-z_]\w*)\)", r"Indicate(particle_\1)", repaired)
            if next_repaired != repaired:
                _add_note(notes, "retarget path indications to particles")
            repaired = next_repaired
            next_repaired = re.sub(r"GrowArrow\((brace\w*)\)", r"GrowFromCenter(\1)", repaired)
            next_repaired = next_repaired.replace("run_time=10", "run_time=3")
            if next_repaired != repaired:
                _add_note(notes, "shorten timeout-prone render path")
            repaired = next_repaired
        lines.append(repaired)
    return "".join(lines), notes


def _coarsen_vector_field_line(line: str) -> str:
    updated = re.sub(r"([xy]_range=\[-?[0-9.]+,\s*-?[0-9.]+)\]", r"\1, 1]", line)
    return updated

def _add_note(notes: list[str], note: str) -> None:
    if note not in notes:
        notes.append(note)
