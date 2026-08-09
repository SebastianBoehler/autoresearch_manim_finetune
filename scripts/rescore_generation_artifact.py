from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mac_pipeline.eval import score_case
from mac_pipeline.eval_summary import summarize_case_results
from mac_pipeline.types import BenchmarkConfig
from mac_pipeline.utils import load_records, write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    config = BenchmarkConfig.load(Path(args.config))
    records = _records_by_id(ROOT / config.dataset_dir)
    input_payload = json.loads(Path(args.input).read_text())
    cases = [
        _rescore_case(config, records, case)
        for case in input_payload.get("cases", [])
    ]
    payload = {
        "run_name": f"{input_payload.get('run_name', 'generation')}-rescore",
        "source_path": str(Path(args.input).resolve()),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": summarize_case_results(cases),
        "cases": cases,
    }
    write_json(Path(args.output), payload)
    print(json.dumps(payload["summary"], indent=2))


def _records_by_id(dataset_dir: Path) -> dict[str, dict]:
    return {
        record["case_id"]: record
        for record in load_records(dataset_dir / "test.jsonl")
    }


def _rescore_case(
    config: BenchmarkConfig,
    records: dict[str, dict],
    case: dict,
) -> dict:
    case_id = case["case_id"]
    code_fields = (
        ("final_code", "code", "generated_code")
        if config.evaluation.allow_code_repair
        else ("generated_code", "code", "final_code")
    )
    code = next((case.get(field) for field in code_fields if case.get(field)), None)
    if not code:
        raise ValueError(f"Case has no code to rescore: {case_id}")
    rescored = score_case(
        case=records[case_id],
        code=code,
        render_enabled=config.evaluation.run_render,
        weights=config.evaluation.metric_weights,
        quality=config.evaluation.render_quality,
        timeout_seconds=config.evaluation.max_render_seconds,
        allow_code_repair=config.evaluation.allow_code_repair,
    )
    rescored["source_case_id"] = case_id
    rescored["source_weighted_score"] = case.get("weighted_score")
    return rescored


if __name__ == "__main__":
    main()
