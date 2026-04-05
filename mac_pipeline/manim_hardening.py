from __future__ import annotations

import re

HARDENING_SENTINEL = "Prefer only built-in, documented Manim Community Edition APIs."
HARDENED_SYSTEM_PROMPT_SUFFIX = (
    f" {HARDENING_SENTINEL} "
    "Do not reference external image, svg, or texture assets. "
    "Do not invent helper methods, classes, or attributes. "
    "Use only simple built-in primitives such as Scene, ThreeDScene, Axes, ThreeDAxes, "
    "NumberLine, NumberPlane, Circle, Dot, Line, Arrow, Graph, Text, MathTex, VGroup, "
    "Rectangle, RoundedRectangle, SurroundingRectangle, ValueTracker, ArrowVectorField, and Surface. "
    "Put run_time only on self.play calls, not on constructors or plot methods. "
    "Use layout='circular' style strings for Graph layouts. "
    "Use PolarPlane.plot_polar_graph for polar plots. "
    "Use only color constants that exist in manim; ORANGE has no A/B/C/D/E variants in this environment. "
    "If you need a panel, build it from Rectangle or RoundedRectangle and move a Text onto it instead of calling custom methods."
)

_LINE_RULES: tuple[tuple[str, callable[[str], str], str], ...] = (
    (
        "replace NumberLine x_length with length",
        lambda line: line.replace("x_length=", "length=")
        if "NumberLine(" in line and "x_length=" in line
        else line,
        "replace NumberLine x_length with length",
    ),
    (
        "upgrade 3d Axes to ThreeDAxes",
        lambda line: re.sub(r"(?<!ThreeD)Axes\(", "ThreeDAxes(", line, count=1)
        if "Axes(" in line and "z_range=" in line
        else line,
        "upgrade 3d Axes to ThreeDAxes",
    ),
    (
        "remove unsupported add_caption calls",
        lambda line: ""
        if re.match(r"^\s*\w+\.add_caption\(", line)
        else line,
        "remove unsupported add_caption calls",
    ),
    (
        "replace bare add_labels() with add_numbers()",
        lambda line: line.replace(".add_labels()", ".add_numbers()")
        if ".add_labels()" in line
        else line,
        "replace bare add_labels() with add_numbers()",
    ),
    (
        "strip non-play run_time kwargs",
        lambda line: re.sub(r",\s*run_time\s*=\s*[^),]+", "", line)
        if "run_time=" in line and "self.play(" not in line
        else line,
        "strip non-play run_time kwargs",
    ),
    (
        "animate become calls inside self.play",
        lambda line: re.sub(r"(\b\w+)\.become\(", r"\1.animate.become(", line)
        if "self.play(" in line and ".become(" in line
        else line,
        "animate become calls inside self.play",
    ),
    (
        "animate set_points_smoothly calls inside self.play",
        lambda line: re.sub(
            r"(\b\w+)\.set_points_smoothly\(",
            r"\1.animate.set_points_smoothly(",
            line,
        )
        if "self.play(" in line and ".set_points_smoothly(" in line
        else line,
        "animate set_points_smoothly calls inside self.play",
    ),
)

_GLOBAL_REGEX_RULES: tuple[tuple[re.Pattern[str], str | callable[[re.Match[str]], str], str], ...] = (
    (
        re.compile(r"\bORANGE_[A-E]\b"),
        "ORANGE",
        "replace unsupported ORANGE shade aliases",
    ),
    (
        re.compile(r"\.move_by\("),
        ".shift(",
        "replace unsupported move_by with shift",
    ),
    (
        re.compile(r"\bPipe\("),
        "Line(",
        "replace unsupported Pipe with Line",
    ),
    (
        re.compile(r"layout\s*=\s*GraphLayout\(([^)]+)\)"),
        r"layout=\1",
        "replace GraphLayout wrapper with layout string",
    ),
    (
        re.compile(r"\.plot_polar\("),
        ".plot_polar_graph(",
        "replace plot_polar with plot_polar_graph",
    ),
    (
        re.compile(r"\.get_axis_range\(\)"),
        ".x_range",
        "replace get_axis_range() with x_range",
    ),
    (
        re.compile(r"\.get_origin\(\)"),
        "ORIGIN",
        "replace get_origin() with ORIGIN",
    ),
    (
        re.compile(r"\.axis_range\b"),
        ".x_range",
        "replace axis_range with x_range",
    ),
    (
        re.compile(r"\bVectorField\("),
        "ArrowVectorField(",
        "replace VectorField with ArrowVectorField",
    ),
    (
        re.compile(r",\s*texture\s*=\s*ImageTexture\([^)]*\)"),
        "",
        "remove unsupported ImageTexture usage",
    ),
    (
        re.compile(r",\s*\*\*{['\"]radius['\"]:\s*[^}]+}"),
        "",
        "remove misplaced VGroup radius kwargs",
    ),
    (
        re.compile(
            r"MoveToTarget\(\s*([A-Za-z_]\w*)\s*,\s*target=([^,\n)]+)(?:,\s*[^)]*)?\)"
        ),
        r"\1.animate.move_to(\2)",
        "replace unsupported MoveToTarget(target=...) usage",
    ),
    (
        re.compile(
            r"SurroundingRectangle\((axes\.c2p\([^)]+\)),\s*([0-9.]+),\s*([0-9.]+),\s*color=([^,]+),\s*fill_opacity=([0-9.]+)\)"
        ),
        r"Rectangle(width=\2, height=\3, color=\4, fill_opacity=\5).move_to(\1)",
        "replace SurroundingRectangle point usage with Rectangle.move_to",
    ),
    (
        re.compile(r"\bcaption_text\b"),
        "phase_caption",
        "replace undefined caption_text reference with phase_caption",
    ),
    (
        re.compile(r"\[\s*(['\"][^'\"]+['\"])\s*,\s*(['\"][^'\"]+['\"])\s*\]"),
        r"(\1, \2)",
        "replace string pair lists with tuples",
    ),
)

_REPAIR_TRIGGER_RULES: tuple[tuple[re.Pattern[str], tuple[tuple[re.Pattern[str], str, str], ...]], ...] = (
    (
        re.compile(r"Unexpected argument .* passed to Scene\.play\(\)", re.IGNORECASE),
        (
            (
                re.compile(r"(\b\w+)\.become\("),
                r"\1.animate.become(",
                "animate become calls after Scene.play failure",
            ),
            (
                re.compile(r"(\b\w+)\.set_points_smoothly\("),
                r"\1.animate.set_points_smoothly(",
                "animate set_points_smoothly calls after Scene.play failure",
            ),
        ),
    ),
)


def harden_system_prompt(system_prompt: str | None) -> str | None:
    if system_prompt is None:
        return None
    if HARDENING_SENTINEL in system_prompt:
        return system_prompt
    return system_prompt.rstrip() + HARDENED_SYSTEM_PROMPT_SUFFIX


def _apply_line_rules(code: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    rewritten_lines: list[str] = []
    for line in code.splitlines(keepends=True):
        updated = line
        for _, rewrite, note in _LINE_RULES:
            next_line = rewrite(updated)
            if next_line != updated:
                if note not in notes:
                    notes.append(note)
                updated = next_line
        if updated:
            rewritten_lines.append(updated)
    return "".join(rewritten_lines), notes


def _apply_regex_rules(
    code: str,
    rules: tuple[tuple[re.Pattern[str], str | callable[[re.Match[str]], str], str], ...],
) -> tuple[str, list[str]]:
    notes: list[str] = []
    updated = code
    for pattern, replacement, note in rules:
        next_code, count = pattern.subn(replacement, updated)
        if count:
            if note not in notes:
                notes.append(note)
            updated = next_code
    return updated, notes


def normalize_generated_code(code: str) -> tuple[str, list[str]]:
    updated, notes = _apply_line_rules(code)
    updated, regex_notes = _apply_regex_rules(updated, _GLOBAL_REGEX_RULES)
    notes.extend(note for note in regex_notes if note not in notes)
    return updated, notes


def repair_generated_code(code: str, render_log_tail: str) -> tuple[str, list[str]]:
    updated = code
    notes: list[str] = []
    for trigger, rules in _REPAIR_TRIGGER_RULES:
        if not trigger.search(render_log_tail):
            continue
        repaired, rule_notes = _apply_regex_rules(updated, rules)
        if repaired != updated:
            updated = repaired
            notes.extend(note for note in rule_notes if note not in notes)
    return updated, notes
