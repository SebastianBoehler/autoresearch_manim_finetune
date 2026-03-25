from __future__ import annotations

from pathlib import Path
from typing import Any

from mac_pipeline.review.render import render_review_candidate
from mac_pipeline.utils import ensure_dir, load_records, write_json


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
