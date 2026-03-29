from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mac_pipeline.utils import load_records, write_json, write_records


def apply_dataset_review_decisions(
    *,
    input_path: Path,
    review_path: Path,
    decision_log_path: Path,
    rejected_output_path: Path,
) -> dict[str, Any]:
    dataset_records = load_records(input_path)
    review_records = load_records(review_path)
    decision_log = load_records(decision_log_path) if decision_log_path.exists() else []
    rejected_records = load_records(rejected_output_path) if rejected_output_path.exists() else []

    dataset_map = {record["case_id"]: record for record in dataset_records}
    prior_logged_ids = {record["case_id"] for record in decision_log}
    rejected_ids = {record["case_id"] for record in rejected_records}
    actionable = [record for record in review_records if record.get("decision") in {"promote", "reject"}]
    if not actionable:
        raise ValueError("No promote/reject decisions found in the review file.")

    decided_case_ids = [record["case_id"] for record in actionable]
    unknown_case_ids = [case_id for case_id in decided_case_ids if case_id not in dataset_map]
    if unknown_case_ids:
        raise ValueError(f"Review file references unknown dataset case_ids: {unknown_case_ids}")

    duplicate_case_ids = [case_id for case_id in decided_case_ids if case_id in prior_logged_ids]
    if duplicate_case_ids:
        raise ValueError(f"Review decisions already applied for case_ids: {duplicate_case_ids}")

    rejected_batch = [dataset_map[record["case_id"]] for record in actionable if record["decision"] == "reject"]
    duplicate_rejected = [record["case_id"] for record in rejected_batch if record["case_id"] in rejected_ids]
    if duplicate_rejected:
        raise ValueError(f"Rejected cases already archived: {duplicate_rejected}")

    timestamp = datetime.now(timezone.utc).isoformat()
    decision_entries = [
        {
            "case_id": record["case_id"],
            "decision": record["decision"],
            "confidence": record.get("confidence"),
            "notes": record.get("notes", ""),
            "source_review_path": str(review_path),
            "applied_at": timestamp,
        }
        for record in actionable
    ]
    kept_dataset = [
        record for record in dataset_records
        if record["case_id"] not in {entry["case_id"] for entry in rejected_batch}
    ]

    write_records(input_path, kept_dataset)
    write_records(decision_log_path, [*decision_log, *decision_entries])
    write_records(rejected_output_path, [*rejected_records, *rejected_batch])

    summary = {
        "input_path": str(input_path),
        "review_path": str(review_path),
        "decision_log_path": str(decision_log_path),
        "rejected_output_path": str(rejected_output_path),
        "num_decisions_applied": len(decision_entries),
        "num_promoted": sum(1 for entry in decision_entries if entry["decision"] == "promote"),
        "num_rejected": sum(1 for entry in decision_entries if entry["decision"] == "reject"),
        "num_remaining_dataset_cases": len(kept_dataset),
    }
    write_json(review_path.parent / "apply_summary.json", summary)
    return summary
