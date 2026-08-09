from __future__ import annotations

import json
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mac_pipeline.eval import extract_code, score_case
from mac_pipeline.local_inference import generate_completion_result
from mac_pipeline.types import BenchmarkConfig
from mac_pipeline.utils import load_records, write_json

CONFIG_PATH = ROOT / "configs" / "local_mlx_learning_app_taste_benchmark.json"
OUTPUT_PATH = ROOT / "artifacts" / "benchmarks" / "local-mlx-adaptive-cap" / "attention-cap-sweep.json"
TARGET_NAME = "local-finetuned-qwen25coder-3b"
CASE_ID = "attention_weighted_average_micro"
TOKEN_CAPS = [1150, 1200, 1250, 1300, 1350]


def main() -> None:
    config = BenchmarkConfig.load(CONFIG_PATH)
    target = next(target for target in config.targets if target.name == TARGET_NAME)
    record = next(
        record
        for record in load_records(ROOT / config.dataset_dir / "test.jsonl")
        if record["case_id"] == CASE_ID
    )
    adapter_path = ROOT / target.adapter_path if target.adapter_path else None
    rows = [
        _run_cap(config, target.model, adapter_path, record, max_tokens)
        for max_tokens in TOKEN_CAPS
    ]
    payload = {
        "run_name": "attention-cap-sweep",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "case_id": CASE_ID,
        "rows": rows,
    }
    write_json(OUTPUT_PATH, payload)
    print(json.dumps(rows, indent=2))


def _run_cap(
    config: BenchmarkConfig,
    model: str,
    adapter_path: Path | None,
    record: dict,
    max_tokens: int,
) -> dict:
    system_prompt = next(
        (message["content"] for message in record["messages"] if message["role"] == "system"),
        None,
    )
    user_prompt = next(
        message["content"] for message in record["messages"] if message["role"] == "user"
    )
    result = generate_completion_result(
        base_model=model,
        adapter_path=adapter_path,
        prompt=user_prompt,
        system_prompt=system_prompt,
        generation=replace(config.generation, max_tokens=max_tokens),
    )
    score = score_case(
        case=record,
        code=extract_code(result.text),
        render_enabled=config.evaluation.run_render,
        weights=config.evaluation.metric_weights,
        quality=config.evaluation.render_quality,
        timeout_seconds=config.evaluation.max_render_seconds,
    )
    return {
        "max_tokens": max_tokens,
        "syntax_ok": score["syntax_ok"],
        "render_ok": score["render_ok"],
        "generation_quality_ok": score["generation_quality_ok"],
        "production_ok": bool(
            score["syntax_ok"] and score["render_ok"] is True and score["generation_quality_ok"]
        ),
        "weighted_score": score["weighted_score"],
        "quality": score["generation_quality"],
        "latency": result.metrics.to_dict(),
        "notes": score["normalization_notes"],
    }


if __name__ == "__main__":
    main()
