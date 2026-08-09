from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mac_pipeline.eval import extract_code, score_case
from mac_pipeline.eval_summary import summarize_case_results
from mac_pipeline.local_inference import generate_completion_result
from mac_pipeline.types import BenchmarkConfig
from mac_pipeline.utils import load_records, write_json

CONFIG_PATH = ROOT / "configs" / "local_mlx_learning_app_taste_benchmark.json"
OUTPUT_PATH = ROOT / "artifacts" / "benchmarks" / "local-mlx-adaptive-cap" / "current-qwen-lora.json"
TARGET_NAME = "local-finetuned-qwen25coder-3b"


def choose_cap(record: dict) -> int:
    text = f"{record['case_id']} {record['prompt']}".lower()
    if any(marker in text for marker in ["attention", "matrix", "weighted average"]):
        return 1400
    return 700


def main() -> None:
    config = BenchmarkConfig.load(CONFIG_PATH)
    target = next(target for target in config.targets if target.name == TARGET_NAME)
    dataset_dir = ROOT / config.dataset_dir
    adapter_path = ROOT / target.adapter_path if target.adapter_path else None
    records = load_records(dataset_dir / "test.jsonl")[: config.evaluation.max_cases]
    cases: list[dict] = []
    for record in records:
        max_tokens = choose_cap(record)
        generation = config.generation
        generation.max_tokens = max_tokens
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
            generation=generation,
        )
        score = score_case(
            case=record,
            code=extract_code(result.text),
            render_enabled=config.evaluation.run_render,
            weights=config.evaluation.metric_weights,
            quality=config.evaluation.render_quality,
            timeout_seconds=config.evaluation.max_render_seconds,
        )
        score["max_tokens"] = max_tokens
        score["latency"] = result.metrics.to_dict()
        score["response_chars"] = len(result.text)
        cases.append(score)

    summary = summarize_case_results(cases)
    summary.update(
        {
            "total_wall_seconds": sum(case["latency"]["wall_seconds"] for case in cases),
            "mean_wall_seconds": sum(case["latency"]["wall_seconds"] for case in cases)
            / len(cases),
        }
    )
    payload = {
        "run_name": "current-qwen-lora-adaptive-cap",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": summary,
        "cases": cases,
    }
    write_json(OUTPUT_PATH, payload)
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()
