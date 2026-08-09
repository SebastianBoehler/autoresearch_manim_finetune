from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "artifacts" / "overnight" / "round12"
LOG_PATH = RUN_DIR / "run.log"
SUMMARY_PATH = RUN_DIR / "summary.json"

COMMANDS = [
    [
        "uv",
        "run",
        "python",
        "-m",
        "mac_pipeline.cli",
        "run",
        "--config",
        "configs/m4_max_qwen25coder_3b_round12.json",
    ],
    [
        "uv",
        "run",
        "python",
        "-m",
        "mac_pipeline.cli",
        "benchmark",
        "--config",
        "configs/local_mlx_learning_app_taste_benchmark_round12.json",
    ],
    [
        "uv",
        "run",
        "python",
        "-m",
        "mac_pipeline.cli",
        "latency-benchmark",
        "--config",
        "configs/local_mlx_trending_latency_benchmark.json",
        "--target",
        "ternary-bonsai-4b-2bit",
        "--target",
        "ternary-bonsai-8b-2bit",
        "--max-cases",
        "1",
        "--max-tokens",
        "256",
        "--warmup-cases",
        "0",
        "--repetitions",
        "1",
    ],
    [
        "uv",
        "run",
        "python",
        "-m",
        "mac_pipeline.cli",
        "benchmark",
        "--config",
        "configs/local_mlx_trending_taste_benchmark.json",
    ],
]


def run_command(command: list[str]) -> dict[str, object]:
    started = datetime.now().isoformat(timespec="seconds")
    with LOG_PATH.open("a") as log:
        log.write(f"\n[{started}] $ {' '.join(command)}\n")
        log.flush()
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    finished = datetime.now().isoformat(timespec="seconds")
    return {
        "command": command,
        "started_at": started,
        "finished_at": finished,
        "returncode": result.returncode,
    }


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    summary = {"started_at": datetime.now().isoformat(timespec="seconds"), "runs": []}
    LOG_PATH.write_text(f"round12 overnight run started at {summary['started_at']}\n")
    for command in COMMANDS:
        result = run_command(command)
        summary["runs"].append(result)
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n")
    summary["finished_at"] = datetime.now().isoformat(timespec="seconds")
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
