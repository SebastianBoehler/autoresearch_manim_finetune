from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mac_pipeline.review.render import render_review_candidate
from mac_pipeline.utils import ensure_dir, load_records, slugify, write_json


def build_sample_review_session(
    *,
    input_path: Path,
    output_dir: Path,
    start_index: int = 0,
    limit: int = 0,
    exclude_review_paths: list[Path] | None = None,
    quality: str = "low",
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    all_records = load_records(input_path)
    excluded_case_ids = _load_excluded_case_ids(exclude_review_paths or [])
    available_records = [
        record for record in all_records
        if record["case_id"] not in excluded_case_ids
    ]
    selected_records = available_records[start_index:]
    if limit > 0:
        selected_records = selected_records[:limit]
    ensure_dir(output_dir)
    items: list[dict[str, Any]] = []
    for case in selected_records:
        render_dir = output_dir / "renders" / slugify(case["case_id"])
        render = render_review_candidate(
            code=case["completion"],
            scene_name=case.get("entry_scene"),
            output_dir=render_dir,
            quality=quality,
            timeout_seconds=timeout_seconds,
        )
        items.append(
            {
                "review_id": slugify(case["case_id"]),
                "case_id": case["case_id"],
                "prompt": case.get("prompt", ""),
                "tags": list(case.get("tags", [])),
                "options": [
                    {
                        "slot": "sample",
                        "label": "sample",
                        "scene_name": case.get("entry_scene"),
                        "render_ok": render["render_ok"],
                        "render_log_tail": render["render_log_tail"],
                        "video_relpath": _relpath(render.get("video_path"), output_dir),
                        "script_relpath": _relpath(render.get("script_path"), output_dir),
                        "log_relpath": _relpath(render.get("log_path"), output_dir),
                    }
                ],
            }
        )

    payload = {
        "session_name": output_dir.name,
        "session_type": "sample_review",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_path": str(input_path),
        "source_total": len(all_records),
        "excluded_total": len(excluded_case_ids),
        "available_total": len(available_records),
        "start_index": start_index,
        "limit": limit,
        "items": items,
        "skipped": [],
    }
    write_json(output_dir / "session.json", payload)
    return payload


def _relpath(path: object, root: Path) -> str | None:
    if not isinstance(path, Path):
        return None
    return str(path.relative_to(root))


def _load_excluded_case_ids(paths: list[Path]) -> set[str]:
    excluded_case_ids: set[str] = set()
    for path in paths:
        for record in load_records(path):
            case_id = record.get("case_id")
            if isinstance(case_id, str) and case_id:
                excluded_case_ids.add(case_id)
    return excluded_case_ids
