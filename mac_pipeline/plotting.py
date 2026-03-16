from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt


def _winner_text(base_value: float, ft_value: float, lower_is_better: bool) -> str:
    if math.isnan(base_value) or math.isnan(ft_value):
        return "n/a"
    if math.isclose(base_value, ft_value, rel_tol=1e-9, abs_tol=1e-9):
        return "Tie"
    if lower_is_better:
        return "Fine-tuned" if ft_value < base_value else "Base"
    return "Fine-tuned" if ft_value > base_value else "Base"


def _metric_note(base_value: float, ft_value: float) -> str | None:
    missing = []
    if math.isnan(base_value):
        missing.append("Base")
    if math.isnan(ft_value):
        missing.append("Fine-tuned")
    if not missing:
        return None
    return f"{' and '.join(missing)} unavailable"


def plot_eval_comparison(
    baseline_eval_path: Path,
    finetuned_eval_path: Path,
    output_path: Path,
) -> None:
    baseline = json.loads(baseline_eval_path.read_text())["summary"]
    finetuned = json.loads(finetuned_eval_path.read_text())["summary"]

    metrics = [
        ("Test Loss", "test_loss", True),
        ("Syntax Rate", "syntax_success_rate", False),
        ("Render Rate", "render_success_rate", False),
        ("Case Score", "mean_case_score", False),
    ]
    baseline_values = [
        float("nan") if baseline.get(key) is None else float(baseline.get(key))
        for _, key, _ in metrics
    ]
    finetuned_values = [
        float("nan") if finetuned.get(key) is None else float(finetuned.get(key))
        for _, key, _ in metrics
    ]

    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    axes = axes.flatten()
    for ax, (label, _, lower_is_better), base_value, ft_value in zip(
        axes,
        metrics,
        baseline_values,
        finetuned_values,
        strict=True,
    ):
        ax.set_title(label)
        plotted = [
            ("Base", base_value, "#9aa1a9"),
            ("Fine-tuned", ft_value, "#1f77b4"),
        ]
        plotted = [item for item in plotted if not math.isnan(item[1])]
        bars = ax.bar(
            [item[0] for item in plotted],
            [item[1] for item in plotted],
            color=[item[2] for item in plotted],
            width=0.55,
        )
        finite_values = [value for _, value, _ in plotted]
        if lower_is_better and finite_values:
            ax.set_ylim(0, max(finite_values) * 1.08)
        if not lower_is_better and finite_values:
            ax.set_ylim(0, max(1.0, *finite_values) * 1.15)
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                height + max(0.01, height * 0.02),
                f"{height:.3f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )
        ax.text(
            0.5,
            0.92,
            f"Better: {_winner_text(base_value, ft_value, lower_is_better)}",
            transform=ax.transAxes,
            ha="center",
            va="top",
            fontsize=9,
            color="#444",
        )
        note = _metric_note(base_value, ft_value)
        if note is not None:
            ax.text(
                0.5,
                0.84,
                note,
                transform=ax.transAxes,
                ha="center",
                va="top",
                fontsize=8,
                color="#666",
            )

    fig.suptitle("Base Model vs Fine-tuned Model on Held-out Manim Cases", fontsize=14)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
