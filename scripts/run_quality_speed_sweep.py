from __future__ import annotations

import json
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mac_pipeline.benchmark import run_benchmark
from mac_pipeline.latency_benchmark import run_latency_benchmark
from mac_pipeline.types import BenchmarkConfig

BASE_CONFIG = ROOT / "configs" / "local_mlx_learning_app_taste_benchmark.json"
OUTPUT_ROOT = ROOT / "artifacts" / "benchmarks" / "local-mlx-quality-speed-sweep"
TARGET_NAME = "local-finetuned-qwen25coder-3b"
TOKEN_CAPS = [700, 900, 1100, 1400]


def _target_only(config: BenchmarkConfig) -> BenchmarkConfig:
    targets = [target for target in config.targets if target.name == TARGET_NAME]
    if len(targets) != 1:
        raise ValueError(f"Expected exactly one target named {TARGET_NAME}.")
    return replace(config, targets=targets)


def _config_for_tokens(config: BenchmarkConfig, max_tokens: int) -> BenchmarkConfig:
    return replace(
        config,
        name=f"local-mlx-quality-speed-sweep-{max_tokens}",
        output_dir=f"artifacts/benchmarks/local-mlx-quality-speed-sweep/tokens-{max_tokens}",
        generation=replace(config.generation, max_tokens=max_tokens),
    )


def _summary_row(max_tokens: int, quality: dict, latency: dict) -> dict[str, object]:
    quality_target = quality["leaderboard"][0]
    latency_target = latency["leaderboard"][0]
    return {
        "max_tokens": max_tokens,
        "quality": quality_target["summary"],
        "quality_output_path": quality_target["output_path"],
        "latency": latency_target["summary"],
        "latency_output_path": latency_target["output_path"],
    }


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    base = _target_only(BenchmarkConfig.load(BASE_CONFIG))
    rows: list[dict[str, object]] = []
    for max_tokens in TOKEN_CAPS:
        config = _config_for_tokens(base, max_tokens)
        quality = run_benchmark(config, ROOT)
        latency = run_latency_benchmark(
            config,
            ROOT,
            max_cases=1,
            max_tokens=max_tokens,
            warmup_cases=0,
            repetitions=1,
        )
        rows.append(_summary_row(max_tokens, quality, latency))
        (OUTPUT_ROOT / "summary.json").write_text(
            json.dumps(
                {
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                    "target": TARGET_NAME,
                    "rows": rows,
                },
                indent=2,
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
