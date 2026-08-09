from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mac_pipeline.utils import load_records


SPLIT_FILES = {"train": "train.jsonl", "valid": "valid.jsonl", "test": "test.jsonl"}


def load_frozen_chat_splits(
    cases: list[dict[str, Any]],
    split_dir: Path,
) -> dict[str, list[dict[str, Any]]]:
    case_ids = {str(case["case_id"]) for case in cases}
    split_map: dict[str, list[dict[str, Any]]] = {}
    assigned: dict[str, str] = {}
    for split_name, filename in SPLIT_FILES.items():
        path = split_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Frozen split file does not exist: {path}")
        rows = load_records(path)
        for row in rows:
            case_id = str(row.get("case_id") or "")
            if not case_id or not isinstance(row.get("messages"), list):
                raise ValueError(f"Frozen split row is not a chat record: {path}")
            if case_id in assigned:
                raise ValueError(
                    f"Case {case_id} appears in both {assigned[case_id]} and {split_name}."
                )
            assigned[case_id] = split_name
        split_map[split_name] = rows
    assigned_ids = set(assigned)
    if assigned_ids != case_ids:
        missing = sorted(case_ids - assigned_ids)
        extra = sorted(assigned_ids - case_ids)
        raise ValueError(f"Frozen splits do not match exported cases; missing={missing}, extra={extra}")
    return split_map


def load_curated_publication_metadata(split_dir: Path) -> dict[str, Any] | None:
    manifest_path = split_dir / "manifest.json"
    coverage_path = split_dir / "api_coverage.json"
    if not manifest_path.exists() or not coverage_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text())
    coverage = json.loads(coverage_path.read_text())
    return {
        "dataset_version": manifest.get("dataset_version"),
        "source_path": manifest.get("source_path"),
        "target_runtime": manifest.get("target_runtime"),
        "counts": manifest.get("counts"),
        "split_counts": manifest.get("split_counts"),
        "split_policy": manifest.get("split_policy"),
        "api_coverage": coverage.get("summary"),
    }
