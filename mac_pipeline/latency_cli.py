from __future__ import annotations

import argparse
from pathlib import Path

from mac_pipeline.latency_benchmark import run_latency_benchmark
from mac_pipeline.types import BenchmarkConfig
from mac_pipeline.utils import resolve_path


def cmd_latency_benchmark(args: argparse.Namespace) -> None:
    config_path = Path(args.config).resolve()
    benchmark = BenchmarkConfig.load(config_path)
    repo_root = config_path.parent.parent
    payload = run_latency_benchmark(
        benchmark,
        repo_root,
        max_cases=args.max_cases,
        max_tokens=args.max_tokens,
        target_names=set(args.target) if args.target else None,
        warmup_cases=args.warmup_cases,
        repetitions=args.repetitions,
    )
    output_path = resolve_path(repo_root, benchmark.output_dir) / "latency-leaderboard.json"
    print(f"Latency benchmark written to {output_path}")
    for index, entry in enumerate(payload["leaderboard"], start=1):
        summary = entry["summary"]
        print(
            f"{index}. {entry['name']} "
            f"(transport={entry['local_transport']}, "
            f"draft={entry.get('draft_model') or 'none'}, "
            f"mean_wall={summary.get('mean_wall_seconds'):.3f}s, "
            f"mean_ttft={summary.get('mean_ttft_seconds')}, "
            f"gen_tps={summary.get('mean_generation_tokens_per_second')})"
        )
