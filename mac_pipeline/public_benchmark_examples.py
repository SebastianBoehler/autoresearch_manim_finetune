from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from mac_pipeline.eval import detect_scene_class
from mac_pipeline.review.render import render_review_candidate
from mac_pipeline.utils import ensure_parent, slugify

EXAMPLE_SPECS = [
    {
        "case_id": "anim_matching_shapes_word_morph",
        "title": "Transform Matching Shapes",
        "summary": "All compared models render this prompt, which makes it a clean side-by-side quality comparison instead of an error showcase.",
        "models": [
            "Xiaomi MiMo-V2-Pro",
            "Xiaomi MiMo-V2-Pro + Hermes Skill",
            "MiniMax M2.7",
            "Qwen 2.5 Coder 3B Fine-tuned",
        ],
    },
    {
        "case_id": "docs_square_to_circle",
        "title": "Square-To-Circle Primitive",
        "summary": "A canonical docs-style scene where every shown model completes the same basic animation successfully.",
        "models": [
            "Xiaomi MiMo-V2-Pro",
            "Xiaomi MiMo-V2-Pro + Hermes Skill",
            "MiniMax M2.7",
            "Qwen 2.5 Coder 3B Fine-tuned",
        ],
    },
    {
        "case_id": "docs_create_circle",
        "title": "Create Circle Primitive",
        "summary": "A very small primitive scene that every shown model can render, making style and pacing differences easy to inspect.",
        "models": [
            "Xiaomi MiMo-V2-Pro",
            "Xiaomi MiMo-V2-Pro + Hermes Skill",
            "MiniMax M2.7",
            "Qwen 2.5 Coder 3B Fine-tuned",
        ],
    },
    {
        "case_id": "chem_bohr_carbon_diagram",
        "title": "Labeled Bohr Diagram",
        "summary": "A richer chemistry diagram where every shown model still produces a valid end-to-end render.",
        "models": [
            "Xiaomi MiMo-V2-Pro",
            "Xiaomi MiMo-V2-Pro + Hermes Skill",
            "MiniMax M2.7",
            "Qwen 2.5 Coder 3B Fine-tuned",
        ],
    },
]

MODEL_SHORT_LABELS = {
    "Xiaomi MiMo-V2-Pro": "Xiaomi",
    "Xiaomi MiMo-V2-Pro + Hermes Skill": "Xiaomi + Hermes",
    "Qwen 2.5 Coder 3B Fine-tuned": "Qwen 3B FT",
    "Qwen 2.5 Coder 3B Base": "Qwen 3B Base",
    "MiniMax M2.7": "MiniMax",
}


def build_example_bundle(
    *,
    spec: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
    docs_root: Path,
    poster_dir: Path,
    video_dir: Path,
    render_cache_dir: Path,
    status_fn,
    format_metric_fn,
) -> dict[str, Any]:
    rows = []
    prompt = ""
    for model_name in spec["models"]:
        payload = payloads[model_name]
        case = next(item for item in payload["cases"] if item["case_id"] == spec["case_id"])
        if case.get("render_ok") is not True:
            raise RuntimeError(f"{spec['case_id']} is not a valid all-rendered example for {model_name}.")
        prompt = prompt or case.get("prompt", "")
        poster_path, video_path = _ensure_media_assets(
            case=case,
            model_name=model_name,
            poster_dir=poster_dir,
            video_dir=video_dir,
            render_cache_dir=render_cache_dir / spec["case_id"],
        )
        rows.append(
            {
                "name": model_name,
                "short": MODEL_SHORT_LABELS.get(model_name, model_name),
                "status": status_fn(case),
                "score": format_metric_fn(case.get("weighted_score")),
                "render": format_metric_fn(1.0),
                "syntax": format_metric_fn(1.0 if case.get("syntax_ok") else 0.0),
                "poster_path": str(poster_path.relative_to(docs_root)),
                "video_path": str(video_path.relative_to(docs_root)),
            }
        )

    return {
        "case_id": spec["case_id"],
        "title": spec["title"],
        "summary": spec["summary"],
        "prompt": prompt,
        "rows": rows,
    }


def _ensure_media_assets(
    *,
    case: dict[str, Any],
    model_name: str,
    poster_dir: Path,
    video_dir: Path,
    render_cache_dir: Path,
) -> tuple[Path, Path]:
    stem = f"{slugify(case['case_id'])}-{slugify(model_name)}"
    poster_path = poster_dir / f"{stem}.png"
    video_path = video_dir / f"{stem}.mp4"
    if poster_path.exists() and video_path.exists():
        return poster_path, video_path

    code = case.get("final_code") or case.get("code") or case.get("generated_code")
    if not isinstance(code, str) or not code.strip():
        raise RuntimeError(f"Missing code for {case['case_id']} from {model_name}.")
    scene_name = case.get("scene_name") or detect_scene_class(code)
    render = render_review_candidate(
        code=code,
        scene_name=scene_name,
        output_dir=render_cache_dir / slugify(model_name),
        quality="low",
        timeout_seconds=120,
    )
    if not render["render_ok"] or render["video_path"] is None:
        raise RuntimeError(f"Failed to render {case['case_id']} for {model_name}.")

    ensure_parent(video_path)
    shutil.copy2(Path(render["video_path"]), video_path)
    _extract_thumbnail(video_path, poster_path)
    return poster_path, video_path


def _extract_thumbnail(video_path: Path, output_path: Path) -> None:
    ensure_parent(output_path)
    timestamp = _thumbnail_timestamp(video_path)
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        timestamp,
        "-i",
        str(video_path),
        "-vf",
        "scale=960:-1",
        "-frames:v",
        "1",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"ffmpeg failed for {video_path}.")


def _thumbnail_timestamp(video_path: Path) -> str:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return "2.00"
    try:
        duration = float(result.stdout.strip())
    except ValueError:
        return "0.50"
    if duration <= 0.2:
        return "0.10"
    return f"{min(max(0.1, duration * 0.45), duration - 0.05):.2f}"
