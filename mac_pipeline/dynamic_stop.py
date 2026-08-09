from __future__ import annotations

import ast
import re

from mac_pipeline.generation_quality import analyze_generation_quality

_CODE_BLOCK = re.compile(r"```(?:python)?\s*(.*?)(?:```|$)", re.DOTALL | re.IGNORECASE)
_NUMERIC_DURATION = re.compile(
    r"\b([0-9]+(?:\.[0-9]+)?)\s*-?\s*(seconds?|secs?|s|minutes?|mins?)\b",
    re.IGNORECASE,
)
_WORD_DURATION = re.compile(
    r"\b(one|two|three|four|five|ten|fifteen|thirty)\s*-?\s*(seconds?|minutes?|mins?)\b",
    re.IGNORECASE,
)
_WORD_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "ten": 10,
    "fifteen": 15,
    "thirty": 30,
}
_SCENE_BASES = {"Scene", "ThreeDScene", "MovingCameraScene", "ZoomedScene"}


def should_stop_manim_generation(
    text: str,
    prompt: str,
    *,
    target_ratio: float,
    default_duration_seconds: float,
) -> bool:
    code = extract_streamed_code(text)
    if not _has_scene_construct(code):
        return False
    report = analyze_generation_quality(code)
    if report.warnings == ["syntax-invalid"]:
        return False

    target = infer_target_duration_seconds(prompt) or default_duration_seconds
    required_duration = max(4.0, target * target_ratio)
    return (
        report.play_call_count >= 3
        and report.estimated_duration_seconds >= required_duration
        and _last_line_can_end_scene(code)
    )


def infer_target_duration_seconds(prompt: str) -> float | None:
    match = _NUMERIC_DURATION.search(prompt)
    if match:
        value = float(match.group(1))
        return _scale_duration(value, match.group(2))
    match = _WORD_DURATION.search(prompt)
    if match:
        value = float(_WORD_NUMBERS[match.group(1).lower()])
        return _scale_duration(value, match.group(2))
    return None


def extract_streamed_code(text: str) -> str:
    match = _CODE_BLOCK.search(text)
    return match.group(1).strip() if match else text.strip()


def _scale_duration(value: float, unit: str) -> float:
    return value * 60.0 if unit.lower().startswith(("min", "minute")) else value


def _has_scene_construct(code: str) -> bool:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(_base_name(base) in _SCENE_BASES for base in node.bases):
            continue
        if any(_is_construct_method(item) for item in node.body):
            return True
    return False


def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _is_construct_method(node: ast.stmt) -> bool:
    return isinstance(node, ast.FunctionDef) and node.name == "construct"


def _last_line_can_end_scene(code: str) -> bool:
    lines = [line.strip() for line in code.splitlines() if line.strip()]
    if not lines:
        return False
    line = lines[-1]
    return line.startswith(("self.play(", "self.wait(", "self.add(", "return"))
