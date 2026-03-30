from __future__ import annotations

from typing import Any

DEFAULT_ROW_LICENSE = "MIT"
DEFAULT_DATASET_LICENSE_ID = "mit"


def apply_default_row_license(
    record: dict[str, Any],
    *,
    default_license: str = DEFAULT_ROW_LICENSE,
) -> dict[str, Any]:
    if isinstance(record.get("license"), str) and record["license"].strip():
        return dict(record)
    updated = dict(record)
    updated["license"] = default_license
    return updated


def ensure_records_have_licenses(
    records: list[dict[str, Any]],
    *,
    source_label: str,
) -> None:
    missing_case_ids = [
        str(record.get("case_id", "<missing-case-id>"))
        for record in records
        if not isinstance(record.get("license"), str) or not record["license"].strip()
    ]
    if not missing_case_ids:
        return
    preview = ", ".join(missing_case_ids[:10])
    if len(missing_case_ids) > 10:
        preview += ", ..."
    raise ValueError(
        f"Missing row-level license metadata in {source_label}: {preview}"
    )
