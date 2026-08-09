from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mac_pipeline.eval import extract_code, score_case
from mac_pipeline.eval_summary import summarize_case_results
from mac_pipeline.local_inference import clear_model_cache, generate_completion_result
from mac_pipeline.types import BenchmarkConfig, BenchmarkTargetConfig
from mac_pipeline.utils import ensure_dir, load_records, slugify, write_json

CONFIG_PATH = ROOT / "configs" / "local_mlx_chat_eos_stop_benchmark.json"


def main() -> None:
    config = BenchmarkConfig.load(CONFIG_PATH)
    output_dir = ensure_dir(ROOT / config.output_dir)
    records = load_records(ROOT / config.dataset_dir / "test.jsonl")
    selected = records[: config.evaluation.max_cases or len(records)]

    targets = [_run_target(config, target, selected, output_dir) for target in config.targets]
    payload = {
        "name": config.name,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset_dir": str((ROOT / config.dataset_dir).resolve()),
        "num_cases": len(selected),
        "targets": targets,
        "leaderboard": sorted(
            targets,
            key=lambda item: (
                item["summary"].get("model_eos_rate") or 0.0,
                item["summary"].get("production_success_rate") or 0.0,
                -1.0 * (item["summary"].get("mean_wall_seconds") or 0.0),
            ),
            reverse=True,
        ),
    }
    write_json(output_dir / "stop-reason-leaderboard.json", payload)
    print(json.dumps(payload["leaderboard"], indent=2))


def _run_target(
    config: BenchmarkConfig,
    target: BenchmarkTargetConfig,
    records: list[dict],
    output_dir: Path,
) -> dict:
    adapter_path = ROOT / target.adapter_path if target.adapter_path else None
    cases = []
    clear_model_cache()
    for record in records:
        system_prompt = next(
            (message["content"] for message in record["messages"] if message["role"] == "system"),
            None,
        )
        user_prompt = next(
            message["content"] for message in record["messages"] if message["role"] == "user"
        )
        result = generate_completion_result(
            base_model=target.model,
            adapter_path=adapter_path,
            prompt=user_prompt,
            system_prompt=system_prompt,
            generation=config.generation,
            transport=target.local_transport or config.generation.local_transport,
        )
        scored = score_case(
            case=record,
            code=extract_code(result.text),
            render_enabled=config.evaluation.run_render,
            weights=config.evaluation.metric_weights,
            quality=config.evaluation.render_quality,
            timeout_seconds=config.evaluation.max_render_seconds,
        )
        scored["raw_response"] = result.text
        scored["latency"] = result.metrics.to_dict()
        cases.append(scored)

    payload = {
        "run_name": target.name,
        "model": target.model,
        "adapter_path": target.adapter_path,
        "summary": _summarize(cases),
        "cases": cases,
    }
    output_path = output_dir / f"{slugify(target.name)}.json"
    write_json(output_path, payload)
    return {
        "name": target.name,
        "model": target.model,
        "adapter_path": target.adapter_path,
        "output_path": str(output_path),
        "summary": payload["summary"],
    }


def _summarize(cases: list[dict]) -> dict:
    summary = summarize_case_results(cases)
    latencies = [case["latency"] for case in cases]
    stop_reasons = [latency.get("stop_reason") for latency in latencies]
    summary.update(
        {
            "model_eos_rate": _share(stop_reasons, "model_eos"),
            "token_ceiling_rate": _share(stop_reasons, "token_ceiling"),
            "mean_generation_tokens": mean(
                latency["generation_tokens"] for latency in latencies
                if latency.get("generation_tokens") is not None
            ),
            "mean_wall_seconds": mean(latency["wall_seconds"] for latency in latencies),
        }
    )
    return summary


def _share(values: list[str | None], target: str) -> float:
    return sum(value == target for value in values) / len(values) if values else 0.0


if __name__ == "__main__":
    main()
