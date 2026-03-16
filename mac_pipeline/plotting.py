from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt


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
        bars = ax.bar(
            ["Base", "Fine-tuned"],
            [base_value, ft_value],
            color=["#9aa1a9", "#1f77b4"],
            width=0.55,
        )
        ax.set_title(label)
        finite_values = [value for value in [base_value, ft_value] if not math.isnan(value)]
        if not lower_is_better and finite_values:
            ax.set_ylim(0, max(1.0, *finite_values) * 1.15)
        for bar in bars:
            height = bar.get_height()
            label_text = "n/a" if math.isnan(height) else f"{height:.3f}"
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                (0.02 if math.isnan(height) else height + max(0.01, height * 0.02)),
                label_text,
                ha="center",
                va="bottom",
                fontsize=9,
            )
        if math.isnan(base_value) or math.isnan(ft_value):
            winner = "n/a"
        elif lower_is_better:
            winner = "Fine-tuned" if ft_value < base_value else "Base"
        else:
            winner = "Fine-tuned" if ft_value > base_value else "Base"
        ax.text(
            0.5,
            0.92,
            f"Better: {winner}",
            transform=ax.transAxes,
            ha="center",
            va="top",
            fontsize=9,
            color="#444",
        )

    fig.suptitle("Base Model vs Fine-tuned Model on Held-out Manim Cases", fontsize=14)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
