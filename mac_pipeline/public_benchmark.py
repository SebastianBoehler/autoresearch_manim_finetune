from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path
from typing import Any

from mac_pipeline.plotting import plot_benchmark_leaderboard
from mac_pipeline.public_benchmark_examples import EXAMPLE_SPECS, build_example_bundle
from mac_pipeline.utils import ensure_parent

CATEGORY_LABELS = {
    "api": "API model",
    "api_skill": "API model + skill",
    "local_finetuned": "Local fine-tune",
    "local_base": "Local base",
}

def _format_metric(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def describe_case_status(case: dict[str, Any]) -> str:
    if case.get("render_ok") is True:
        return "Rendered"
    if not case.get("syntax_ok", True):
        return "Syntax error"
    if not case.get("scene_name"):
        return "No scene detected"
    if case.get("render_ok") is False:
        return "Render failed"
    return "Not attempted"


def render_public_benchmark_markdown(
    *,
    report: dict[str, Any],
    generated_on: str,
    examples: list[dict[str, Any]],
) -> str:
    leaderboard_lines = [
        "| Rank | Model | Category | Case Score | Render Rate | Syntax Rate |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for index, entry in enumerate(report["leaderboard"], start=1):
        summary = entry["summary"]
        leaderboard_lines.append(
            "| "
            f"{index} | {entry['name']} | {CATEGORY_LABELS.get(entry['category'], entry['category'])} | "
            f"{_format_metric(summary.get('mean_case_score'))} | "
            f"{_format_metric(summary.get('render_success_rate'))} | "
            f"{_format_metric(summary.get('syntax_success_rate'))} |"
        )

    top_model = report["leaderboard"][0]
    top_summary = top_model["summary"]
    minimax_summary = next(
        (entry["summary"] for entry in report["leaderboard"] if entry["name"] == "MiniMax M2.7"),
        None,
    )
    ft_summary = next(
        (
            entry["summary"]
            for entry in report["leaderboard"]
            if entry["name"] == "Qwen 2.5 Coder 3B Fine-tuned"
        ),
        None,
    )
    takeaways = [
        (
            f"{top_model['name']} currently leads the held-out benchmark with case score "
            f"`{_format_metric(top_summary.get('mean_case_score'))}` and render rate "
            f"`{_format_metric(top_summary.get('render_success_rate'))}`."
        ),
        "The copied Hermes skill is not a free gain. It rescues isolated prompts, but it lowers Xiaomi's aggregate score and render rate on this split.",
        (
            "MiniMax M2.7 lands near the local fine-tune on mean case score "
            f"(`{_format_metric(minimax_summary.get('mean_case_score') if minimax_summary else None)}` vs "
            f"`{_format_metric(ft_summary.get('mean_case_score') if ft_summary else None)}`), "
            "but it still trails Xiaomi on render reliability."
        ),
        "The local fine-tune still wins select science-story prompts, so continuing fine-tuning only makes sense if local inference cost or offline deployment matters.",
    ]

    sections = [
        "# Public Manim Benchmark",
        "",
        (
            f"Generated on {generated_on} from the current {report.get('num_cases')}-case held-out split. "
            "This page is the public snapshot of the repo's model-comparison benchmark."
        ),
        "",
        "## Leaderboard",
        "",
        "![Held-out Manim model leaderboard](figures/model-benchmark-leaderboard.png)",
        "",
        *leaderboard_lines,
        "",
        "## What This Measures",
        "",
        "- Same held-out prompt set for local base, local fine-tune, and API models.",
        "- Composite score over syntax validity, scene detection, required or forbidden snippet checks, and optional real Manim render success.",
        "- API runs use ADK plus OpenRouter. Local runs use the repo's MLX evaluation pipeline.",
        "",
        "## Current Read",
        "",
        *(f"- {line}" for line in takeaways),
        "",
        "## Rendered Examples",
        "",
    ]
    for example in examples:
        sections.extend(
            [
                f"### {example['title']}",
                "",
                example["summary"],
                "",
                f"Prompt: `{example['prompt']}`",
                "",
            ]
        )
        for row in example["rows"]:
            sections.extend(
                [
                    f"#### {row['name']}",
                    "",
                    (
                        f"<video controls playsinline preload=\"metadata\" poster=\"{row['poster_path']}\" "
                        f"src=\"{row['video_path']}\"></video>"
                    ),
                    "",
                    (
                        f"Status: `{row['status']}`. Score `{row['score']}`. "
                        f"Render `{row['render']}`. Syntax `{row['syntax']}`."
                    ),
                    "",
                ]
            )
    sections.extend(
        [
            "## Public Data Snapshot",
            "",
            "A committed JSON snapshot for this page lives at `docs/data/model-benchmark-public.json`.",
            "",
        ]
    )
    return "\n".join(sections)


def build_public_benchmark_page(
    *,
    report_path: Path,
    output_path: Path,
    public_data_path: Path,
    examples_dir: Path,
    render_cache_dir: Path,
) -> dict[str, Any]:
    report = json.loads(report_path.read_text())
    plot_benchmark_leaderboard(report_path, output_path.parent / "figures" / "model-benchmark-leaderboard.png")
    payloads = {
        entry["name"]: json.loads(Path(entry["path"]).read_text())
        for entry in report["entries"]
        if "summary" in entry
    }
    video_dir = output_path.parent / "videos" / "benchmark_examples"
    _reset_dir(examples_dir)
    _reset_dir(video_dir)
    generated_examples = [
        build_example_bundle(
            spec=spec,
            payloads=payloads,
            docs_root=output_path.parent,
            poster_dir=examples_dir,
            video_dir=video_dir,
            render_cache_dir=render_cache_dir,
            status_fn=describe_case_status,
            format_metric_fn=_format_metric,
        )
        for spec in EXAMPLE_SPECS
    ]
    today = date.today()
    generated_on = f"{today:%B} {today.day}, {today:%Y}"
    markdown = render_public_benchmark_markdown(
        report=report,
        generated_on=generated_on,
        examples=generated_examples,
    )
    ensure_parent(output_path).write_text(markdown)
    public_payload = {
        "generated_on": generated_on,
        "num_cases": report.get("num_cases"),
        "leaderboard": report["leaderboard"],
        "examples": generated_examples,
    }
    ensure_parent(public_data_path).write_text(json.dumps(public_payload, indent=2) + "\n")
    return public_payload


def _reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
