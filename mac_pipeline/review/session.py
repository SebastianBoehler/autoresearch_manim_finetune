from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mac_pipeline.review.render import render_review_candidate
from mac_pipeline.utils import ensure_dir, load_records, slugify, write_json


def build_review_session(
    *,
    left_eval_path: Path,
    right_eval_path: Path,
    output_dir: Path,
    left_label: str | None = None,
    right_label: str | None = None,
    seed: int = 42,
    limit: int = 0,
    quality: str = "low",
    timeout_seconds: int = 120,
    include_failed_renders: bool = False,
) -> dict[str, Any]:
    left_eval = json.loads(left_eval_path.read_text())
    right_eval = json.loads(right_eval_path.read_text())
    ensure_dir(output_dir)
    dataset_dir = Path(left_eval["dataset_dir"])
    prompt_map = _load_prompt_map(dataset_dir / "test.jsonl")
    left_cases = {case["case_id"]: case for case in left_eval["cases"]}
    right_cases = {case["case_id"]: case for case in right_eval["cases"]}
    shared_case_ids = [case["case_id"] for case in left_eval["cases"] if case["case_id"] in right_cases]
    if not shared_case_ids:
        raise ValueError(
            "The selected eval files do not share any case_id values. "
            "Choose outputs produced on the same test split."
        )
    if limit > 0:
        shared_case_ids = shared_case_ids[:limit]

    resolved_left_label = left_label or left_eval.get("run_name") or left_eval_path.stem
    resolved_right_label = right_label or right_eval.get("run_name") or right_eval_path.stem
    if resolved_left_label == resolved_right_label:
        resolved_left_label = left_label or left_eval_path.stem
        resolved_right_label = right_label or right_eval_path.stem
    items: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for case_id in shared_case_ids:
        prompt = left_cases[case_id].get("prompt") or right_cases[case_id].get("prompt") or prompt_map.get(case_id, "")
        left_option = _build_option(
            side="left",
            label=resolved_left_label,
            case=left_cases[case_id],
            output_dir=output_dir,
            case_id=case_id,
            quality=quality,
            timeout_seconds=timeout_seconds,
        )
        right_option = _build_option(
            side="right",
            label=resolved_right_label,
            case=right_cases[case_id],
            output_dir=output_dir,
            case_id=case_id,
            quality=quality,
            timeout_seconds=timeout_seconds,
        )
        options = _blind_order(case_id, seed, [left_option, right_option])
        both_rendered = all(option["render_ok"] for option in options)
        if not both_rendered and not include_failed_renders:
            skipped.append({"case_id": case_id, "reason": "one_or_more_renders_failed"})
            continue
        items.append(
            {
                "review_id": slugify(case_id),
                "case_id": case_id,
                "prompt": prompt,
                "options": options,
            }
        )

    payload = {
        "session_name": output_dir.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "left_eval_path": str(left_eval_path),
        "right_eval_path": str(right_eval_path),
        "left_label": resolved_left_label,
        "right_label": resolved_right_label,
        "items": items,
        "skipped": skipped,
    }
    write_json(output_dir / "session.json", payload)
    return payload


def _build_option(
    *,
    side: str,
    label: str,
    case: dict[str, Any],
    output_dir: Path,
    case_id: str,
    quality: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    render_dir = output_dir / "renders" / slugify(case_id) / side
    render = render_review_candidate(
        code=case["code"],
        scene_name=case.get("scene_name"),
        output_dir=render_dir,
        quality=quality,
        timeout_seconds=timeout_seconds,
    )
    return {
        "label": label,
        "source_side": side,
        "scene_name": case.get("scene_name"),
        "syntax_ok": case.get("syntax_ok"),
        "render_ok": render["render_ok"],
        "weighted_score": case.get("weighted_score"),
        "render_log_tail": render["render_log_tail"],
        "video_relpath": _relpath(render.get("video_path"), output_dir),
        "script_relpath": _relpath(render.get("script_path"), output_dir),
        "log_relpath": _relpath(render.get("log_path"), output_dir),
    }


def _blind_order(case_id: str, seed: int, options: list[dict[str, Any]]) -> list[dict[str, Any]]:
    digest = hashlib.sha256(f"{seed}:{case_id}".encode("utf-8")).hexdigest()
    rng = random.Random(int(digest[:16], 16))
    ordered = list(options)
    rng.shuffle(ordered)
    for slot, option in zip(("A", "B"), ordered, strict=True):
        option["slot"] = slot
    return ordered


def _load_prompt_map(path: Path) -> dict[str, str]:
    records = load_records(path)
    prompt_map: dict[str, str] = {}
    for record in records:
        user_message = next(
            (message["content"] for message in record["messages"] if message["role"] == "user"),
            "",
        )
        prompt_map[record["case_id"]] = user_message
    return prompt_map


def _relpath(path: object, root: Path) -> str | None:
    if not isinstance(path, Path):
        return None
    return str(path.relative_to(root))
