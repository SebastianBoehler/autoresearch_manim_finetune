from __future__ import annotations

import math
import subprocess
import textwrap
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from mac_pipeline.eval import detect_scene_class
from mac_pipeline.review.render import render_review_candidate
from mac_pipeline.utils import ensure_parent, slugify

EXAMPLE_SPECS = [
    {
        "case_id": "ml_cnn_pipeline_blocks",
        "title": "Structured Pipeline Prompt",
        "summary": "A hard held-out explainer where only the leading API model produced a clean render.",
        "models": [
            "Xiaomi MiMo-V2-Pro",
            "Qwen 2.5 Coder 3B Fine-tuned",
            "Qwen 2.5 Coder 3B Base",
            "MiniMax M2.7",
        ],
    },
    {
        "case_id": "control_feedback_loop_story",
        "title": "Classical Control Diagram",
        "summary": "The base model can still match on some simple block-diagram prompts, while the Hermes skill hurt Xiaomi here.",
        "models": [
            "Xiaomi MiMo-V2-Pro",
            "Xiaomi MiMo-V2-Pro + Hermes Skill",
            "Qwen 2.5 Coder 3B Fine-tuned",
            "Qwen 2.5 Coder 3B Base",
        ],
    },
    {
        "case_id": "neuroscience_synapse_strength_story",
        "title": "Narrative Science Prompt",
        "summary": "The local fine-tune still wins some prompts, which means the specialization path still has real signal.",
        "models": [
            "Qwen 2.5 Coder 3B Fine-tuned",
            "Xiaomi MiMo-V2-Pro",
            "Xiaomi MiMo-V2-Pro + Hermes Skill",
            "MiniMax M2.7",
        ],
    },
    {
        "case_id": "chem_bohr_carbon_diagram",
        "title": "Low-Complexity Canonical Diagram",
        "summary": "Simple canonical prompts are now close to solved across the stack, with only small quality differences.",
        "models": [
            "Xiaomi MiMo-V2-Pro",
            "MiniMax M2.7",
            "Qwen 2.5 Coder 3B Fine-tuned",
            "Qwen 2.5 Coder 3B Base",
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


def build_example_panel(
    *,
    spec: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
    docs_root: Path,
    output_dir: Path,
    render_cache_dir: Path,
    status_fn,
    format_metric_fn,
) -> dict[str, Any]:
    cards = []
    prompt = ""
    for model_name in spec["models"]:
        payload = payloads[model_name]
        case = next(item for item in payload["cases"] if item["case_id"] == spec["case_id"])
        prompt = prompt or case.get("prompt", "")
        preview_path = None
        if case.get("render_ok") is True:
            preview_path = _ensure_preview(
                case=case,
                model_name=model_name,
                render_cache_dir=render_cache_dir / spec["case_id"],
                preview_dir=output_dir,
            )
        cards.append(
            {
                "name": model_name,
                "short": MODEL_SHORT_LABELS.get(model_name, model_name),
                "status": status_fn(case),
                "score": format_metric_fn(case.get("weighted_score")),
                "render": format_metric_fn(1.0 if case.get("render_ok") is True else 0.0 if case.get("render_ok") is False else None),
                "syntax": format_metric_fn(1.0 if case.get("syntax_ok") else 0.0),
                "preview_path": preview_path,
            }
        )

    panel_path = output_dir / f"{slugify(spec['case_id'])}.png"
    _write_example_panel(panel_path, spec["title"], prompt, cards)
    return {
        "case_id": spec["case_id"],
        "title": spec["title"],
        "summary": spec["summary"],
        "prompt": prompt,
        "panel_path": str(panel_path.relative_to(docs_root)),
        "rows": [
            {
                "name": card["name"],
                "status": card["status"],
                "score": card["score"],
                "render": card["render"],
                "syntax": card["syntax"],
            }
            for card in cards
        ],
    }


def _ensure_preview(
    *,
    case: dict[str, Any],
    model_name: str,
    render_cache_dir: Path,
    preview_dir: Path,
) -> Path:
    preview_path = preview_dir / f"{slugify(case['case_id'])}-{slugify(model_name)}.png"
    if preview_path.exists():
        return preview_path
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
    _extract_thumbnail(Path(render["video_path"]), preview_path)
    return preview_path


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
        return "00:00:02.0"
    try:
        duration = float(result.stdout.strip())
    except ValueError:
        return "00:00:02.0"
    seconds = max(1.5, duration * 0.45)
    return f"{seconds:.2f}"


def _write_example_panel(
    output_path: Path,
    title: str,
    prompt: str,
    cards: list[dict[str, Any]],
) -> None:
    columns = 2
    rows = math.ceil(len(cards) / columns)
    fig, axes = plt.subplots(rows, columns, figsize=(10, max(4.8, rows * 3.4)))
    axes_list = list(axes.flat) if hasattr(axes, "flat") else [axes]
    for ax, card in zip(axes_list, cards, strict=False):
        preview_path = card["preview_path"]
        if preview_path and preview_path.exists():
            ax.imshow(plt.imread(preview_path))
        else:
            ax.set_facecolor("#eef1f5")
            ax.text(0.5, 0.58, card["status"], ha="center", va="center", fontsize=12, weight="bold")
            ax.text(0.5, 0.38, f"score {card['score']}", ha="center", va="center", fontsize=10)
        ax.set_title(f"{card['short']}\nscore {card['score']} | {card['status']}", fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
    for ax in axes_list[len(cards):]:
        ax.axis("off")
    fig.suptitle(title, fontsize=15, weight="bold")
    fig.text(0.5, 0.03, textwrap.fill(prompt, 110), ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.08, 1, 0.92))
    ensure_parent(output_path)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
