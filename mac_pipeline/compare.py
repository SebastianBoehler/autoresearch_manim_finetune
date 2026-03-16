from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def compare_runs(
    baseline_path: Path,
    candidate_path: Path,
    min_loss_delta: float,
    tie_loss_delta: float,
    allowed_render_regression: float,
) -> dict[str, Any]:
    baseline = _load(baseline_path)
    candidate = _load(candidate_path)
    base_summary = baseline["summary"]
    cand_summary = candidate["summary"]

    base_loss = base_summary.get("test_loss")
    cand_loss = cand_summary.get("test_loss")
    base_render = base_summary.get("render_success_rate")
    cand_render = cand_summary.get("render_success_rate")
    base_case_score = base_summary.get("mean_case_score")
    cand_case_score = cand_summary.get("mean_case_score")

    decision = "tie"
    rationale: list[str] = []
    if base_loss is not None and cand_loss is not None:
        loss_delta = base_loss - cand_loss
        rationale.append(f"loss_delta={loss_delta:.6f}")
        render_delta = None if base_render is None or cand_render is None else cand_render - base_render
        if loss_delta >= min_loss_delta and (render_delta is None or render_delta >= -allowed_render_regression):
            decision = "candidate"
            rationale.append("candidate improves held-out loss without unacceptable render regression")
        elif abs(loss_delta) <= tie_loss_delta:
            if cand_case_score > base_case_score:
                decision = "candidate"
                rationale.append("loss is effectively tied and candidate wins on generation quality")
            elif cand_case_score < base_case_score:
                decision = "baseline"
                rationale.append("loss is effectively tied and baseline wins on generation quality")
        elif loss_delta < 0:
            decision = "baseline"
            rationale.append("candidate regressed on held-out loss")

    if decision == "tie":
        if cand_case_score > base_case_score:
            decision = "candidate"
            rationale.append("candidate wins on mean case score")
        elif cand_case_score < base_case_score:
            decision = "baseline"
            rationale.append("baseline wins on mean case score")

    return {
        "baseline": str(baseline_path),
        "candidate": str(candidate_path),
        "decision": decision,
        "baseline_summary": base_summary,
        "candidate_summary": cand_summary,
        "rationale": rationale,
    }

