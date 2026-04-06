from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mac_pipeline.benchmark_report import build_benchmark_report
from mac_pipeline.plotting import plot_benchmark_leaderboard

REPORT_ENTRIES = [
    {
        "name": "Xiaomi MiMo-V2-Pro",
        "category": "api",
        "path": REPO_ROOT / "artifacts/benchmarks/adk-xiaomi-skill-benchmark/xiaomi-mimo-v2-pro-adk.json",
    },
    {
        "name": "Xiaomi MiMo-V2-Pro + Hermes Skill",
        "category": "api_skill",
        "path": REPO_ROOT / "artifacts/benchmarks/adk-xiaomi-skill-benchmark/xiaomi-mimo-v2-pro-adk-with-hermes-skill.json",
    },
    {
        "name": "Qwen 2.5 Coder 3B Fine-tuned",
        "category": "local_finetuned",
        "path": REPO_ROOT / "artifacts/evals/m4-max-qwen25coder-3b.json",
    },
    {
        "name": "Qwen 2.5 Coder 3B Base",
        "category": "local_base",
        "path": REPO_ROOT / "artifacts/evals/m4-max-qwen25coder-3b-base-current-full.json",
    },
    {
        "name": "Qwen 3.6 Plus Free",
        "category": "api",
        "path": REPO_ROOT / "artifacts/benchmarks/adk-api-model-benchmark/qwen-qwen3-6-plus-free-adk.json",
    },
    {
        "name": "MiniMax M2.7",
        "category": "api",
        "path": REPO_ROOT / "artifacts/benchmarks/adk-api-model-benchmark/minimax-m2-7-adk.json",
    },
    {
        "name": "NVIDIA Nemotron 3 Super 120B A12B Free",
        "category": "api",
        "path": REPO_ROOT / "artifacts/benchmarks/adk-api-model-benchmark/nvidia-nemotron-3-super-120b-a12b-free-openrouter.json",
    },
]


def main() -> None:
    report_path = REPO_ROOT / "artifacts/benchmarks/model-benchmark-report.json"
    plot_path = REPO_ROOT / "docs/figures/model-benchmark-leaderboard.png"
    report = build_benchmark_report(REPORT_ENTRIES, report_path)
    plot_benchmark_leaderboard(report_path, plot_path)
    print(f"Wrote report to {report_path}")
    print(f"Wrote plot to {plot_path}")
    for index, entry in enumerate(report["leaderboard"], start=1):
        summary = entry["summary"]
        print(
            f"{index}. {entry['name']} "
            f"(score={summary.get('mean_case_score'):.3f}, "
            f"render={summary.get('render_success_rate')}, "
            f"syntax={summary.get('syntax_success_rate'):.3f})"
        )
    for entry in report["errors"]:
        print(f"- {entry['name']}: {entry['error']}")


if __name__ == "__main__":
    main()
