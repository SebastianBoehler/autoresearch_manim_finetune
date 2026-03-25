from __future__ import annotations

from pathlib import Path
from typing import Any

from mac_pipeline.canonical_dataset import rebuild_canonical_dataset
from mac_pipeline.review.render import render_review_candidate
from mac_pipeline.utils import ensure_dir, load_records, write_json, write_records

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMOTION_DECISIONS = {"promote", "approved", "approve", "keep", "good", "winner"}


def render_candidate_cases(
    *,
    input_path: Path,
    output_dir: Path,
    quality: str = "low",
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    records = load_records(input_path)
    ensure_dir(output_dir)
    results: list[dict[str, Any]] = []
    for case in records:
        render_dir = output_dir / case["case_id"]
        render = render_review_candidate(
            code=case["completion"],
            scene_name=case.get("entry_scene"),
            output_dir=render_dir,
            quality=quality,
            timeout_seconds=timeout_seconds,
        )
        results.append(
            {
                "case_id": case["case_id"],
                "entry_scene": case.get("entry_scene"),
                "prompt": case["prompt"],
                "render_ok": render["render_ok"],
                "video_path": str(render["video_path"]) if render["video_path"] else None,
                "log_path": str(render["log_path"]) if render["log_path"] else None,
            }
        )

    summary = {
        "input_path": str(input_path),
        "output_dir": str(output_dir),
        "num_cases": len(results),
        "num_rendered": sum(1 for item in results if item["render_ok"]),
        "results": results,
    }
    write_json(output_dir / "summary.json", summary)
    return summary


def promote_candidate_cases(
    *,
    input_path: Path,
    review_path: Path,
    promoted_path: Path,
    remove_promoted: bool = True,
    promoted_tier: str = "tier:silver",
) -> dict[str, Any]:
    canonical_promoted_path = REPO_ROOT / "data" / "manim_review_promoted.jsonl"
    if promoted_path.resolve() != canonical_promoted_path.resolve():
        raise ValueError(
            "Promotion output must be data/manim_review_promoted.jsonl so canonical rebuilds stay reproducible."
        )
    candidate_records = load_records(input_path)
    review_records = load_records(review_path)
    promoted_records = load_records(promoted_path) if promoted_path.exists() else []

    candidate_map = {record["case_id"]: record for record in candidate_records}
    promoted_ids = {record["case_id"] for record in promoted_records}
    selected_case_ids = _selected_case_ids(review_records)
    missing_case_ids = [case_id for case_id in selected_case_ids if case_id not in candidate_map]
    if missing_case_ids:
        raise ValueError(f"Review file references unknown candidate case_ids: {missing_case_ids}")

    duplicate_ids = [case_id for case_id in selected_case_ids if case_id in promoted_ids]
    if duplicate_ids:
        raise ValueError(f"Candidate case_ids are already promoted: {duplicate_ids}")

    promoted_batch = [
        _promoted_record(candidate_map[case_id], promoted_tier)
        for case_id in selected_case_ids
    ]
    write_records(promoted_path, [*promoted_records, *promoted_batch])

    remaining_candidates = [
        record for record in candidate_records if record["case_id"] not in set(selected_case_ids)
    ]
    if remove_promoted:
        write_records(input_path, remaining_candidates)

    canonical_path = rebuild_canonical_dataset(REPO_ROOT)
    summary = {
        "input_path": str(input_path),
        "review_path": str(review_path),
        "promoted_path": str(promoted_path),
        "canonical_dataset_path": str(canonical_path),
        "promoted_case_ids": selected_case_ids,
        "num_promoted": len(selected_case_ids),
        "num_remaining_candidates": len(remaining_candidates) if remove_promoted else len(candidate_records),
    }
    write_json(promoted_path.parent / "promotion_summary.json", summary)
    return summary


def _selected_case_ids(review_records: list[dict[str, Any]]) -> list[str]:
    selected_case_ids: list[str] = []
    for record in review_records:
        case_id = record.get("case_id")
        if not isinstance(case_id, str):
            raise ValueError("Each review record must include a string case_id.")
        decision = str(
            record.get("decision")
            or record.get("label")
            or record.get("verdict")
            or record.get("rating")
            or ""
        ).strip().lower()
        if decision in PROMOTION_DECISIONS:
            selected_case_ids.append(case_id)
    if not selected_case_ids:
        raise ValueError("No promotable review decisions found in the review file.")
    return selected_case_ids


def _promoted_record(case: dict[str, Any], promoted_tier: str) -> dict[str, Any]:
    promoted = dict(case)
    tags = [
        tag
        for tag in case.get("tags", [])
        if tag not in {"review-candidate", "status:unreviewed", "tier:candidate"}
    ]
    for tag in [promoted_tier, "status:approved", "source:review-promotion"]:
        if tag not in tags:
            tags.append(tag)
    promoted["tags"] = tags
    return promoted
