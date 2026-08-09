from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from mac_pipeline.generation_quality import is_generation_quality_ok


def summarize_case_results(cases: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not cases:
        raise ValueError("Cannot summarize zero evaluation cases.")

    render_attempts = [case for case in cases if case["render_ok"] is not None]
    quality_rate = sum(_case_quality_ok(case) for case in cases) / len(cases)
    production_rate = (
        sum(_case_production_ready(case) for case in cases) / len(cases)
        if render_attempts
        else None
    )

    return {
        "num_cases": len(cases),
        "syntax_success_rate": sum(case["syntax_ok"] for case in cases) / len(cases),
        "render_success_rate": (
            sum(case["render_ok"] for case in render_attempts) / len(render_attempts)
            if render_attempts
            else None
        ),
        "quality_success_rate": quality_rate,
        "production_success_rate": production_rate,
        "mean_case_score": sum(case["weighted_score"] for case in cases) / len(cases),
    }


def _case_quality_ok(case: dict[str, Any]) -> bool:
    if "generation_quality_ok" in case:
        return bool(case["generation_quality_ok"])
    return is_generation_quality_ok(case.get("generation_quality", {}))


def _case_production_ready(case: dict[str, Any]) -> bool:
    return bool(case["syntax_ok"] and case["render_ok"] is True and _case_quality_ok(case))
