from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class GenerationQualityReport:
    estimated_duration_seconds: float
    play_call_count: int
    wait_call_count: int
    max_repeated_play_count: int
    repeated_play_samples: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def analyze_generation_quality(code: str) -> GenerationQualityReport:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return GenerationQualityReport(0.0, 0, 0, 0, [], ["syntax-invalid"])

    duration = 0.0
    play_calls: list[str] = []
    wait_count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if name == "self.play":
            duration += _numeric_kwarg(node, "run_time", 1.0)
            play_calls.append(_canonical_call(node))
        if name == "self.wait":
            wait_count += 1
            duration += _first_numeric_arg(node, 1.0)

    repeated = _repeated_play_calls(play_calls)
    warnings = _quality_warnings(duration, len(play_calls), wait_count, repeated)
    return GenerationQualityReport(
        estimated_duration_seconds=round(duration, 3),
        play_call_count=len(play_calls),
        wait_call_count=wait_count,
        max_repeated_play_count=max(repeated.values(), default=0),
        repeated_play_samples=list(repeated)[:5],
        warnings=warnings,
    )


def is_generation_quality_ok(report: GenerationQualityReport | Mapping[str, Any]) -> bool:
    if isinstance(report, GenerationQualityReport):
        warnings = report.warnings
    else:
        if "warnings" not in report:
            return False
        warnings = report["warnings"]
    return not warnings


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Attribute):
        owner = _call_name(node.value)
        return f"{owner}.{node.attr}" if owner else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _numeric_kwarg(node: ast.Call, name: str, default: float) -> float:
    for keyword in node.keywords:
        if keyword.arg == name:
            return _literal_number(keyword.value, default)
    return default


def _first_numeric_arg(node: ast.Call, default: float) -> float:
    if not node.args:
        return default
    return _literal_number(node.args[0], default)


def _literal_number(node: ast.AST, default: float) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    return default


def _canonical_call(node: ast.Call) -> str:
    try:
        text = ast.unparse(node)
    except Exception:
        text = repr(node)
    return " ".join(text.split())


def _repeated_play_calls(play_calls: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for call in play_calls:
        counts[call] = counts.get(call, 0) + 1
    return {call: count for call, count in counts.items() if count >= 4}


def _quality_warnings(
    duration: float,
    play_count: int,
    wait_count: int,
    repeated: dict[str, int],
) -> list[str]:
    warnings: list[str] = []
    if duration > 20:
        warnings.append("estimated-duration-over-20s")
    if play_count > 18:
        warnings.append("too-many-play-calls")
    if wait_count > 8:
        warnings.append("too-many-waits")
    if repeated:
        warnings.append("repeated-play-patterns")
    return warnings
