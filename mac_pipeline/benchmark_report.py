from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mac_pipeline.utils import write_json


def _load_summary(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError(payload.get("error") or f"{path} does not contain a summary payload.")
    return summary


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    path = Path(entry["path"]).resolve()
    if not path.exists():
        return {
            "name": entry["name"],
            "category": entry["category"],
            "path": str(path),
            "error": "artifact missing",
        }
    try:
        summary = _load_summary(path)
    except ValueError as exc:
        return {
            "name": entry["name"],
            "category": entry["category"],
            "path": str(path),
            "error": str(exc),
        }
    return {
        "name": entry["name"],
        "category": entry["category"],
        "path": str(path),
        "summary": {
            "num_cases": summary.get("num_cases"),
            "syntax_success_rate": summary.get("syntax_success_rate"),
            "render_success_rate": summary.get("render_success_rate"),
            "mean_case_score": summary.get("mean_case_score"),
            "test_loss": summary.get("test_loss"),
        },
    }


def build_benchmark_report(
    entries: list[dict[str, Any]],
    output_path: Path,
) -> dict[str, Any]:
    normalized = [_normalize_entry(entry) for entry in entries]
    completed = [entry for entry in normalized if "summary" in entry]
    leaderboard = sorted(
        completed,
        key=lambda item: (
            item["summary"].get("mean_case_score") or 0.0,
            item["summary"].get("render_success_rate") or 0.0,
            item["summary"].get("syntax_success_rate") or 0.0,
        ),
        reverse=True,
    )
    case_counts = sorted(
        {
            item["summary"].get("num_cases")
            for item in completed
            if item["summary"].get("num_cases") is not None
        }
    )
    payload = {
        "entries": normalized,
        "leaderboard": leaderboard,
        "errors": [entry for entry in normalized if "error" in entry],
        "num_cases": case_counts[0] if len(case_counts) == 1 else case_counts,
    }
    write_json(output_path, payload)
    return payload
