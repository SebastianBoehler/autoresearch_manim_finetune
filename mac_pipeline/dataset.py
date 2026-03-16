from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from mac_pipeline.types import SplitConfig
from mac_pipeline.utils import ensure_dir, load_records, write_json
from mac_pipeline.utils import write_jsonl

DEFAULT_SYSTEM_PROMPT = (
    "You write runnable Manim Community Edition Python files. "
    "Return only Python code, use `from manim import *`, and define exactly one scene class."
)
PASSTHROUGH_FIELDS = [
    "source_name",
    "source_url",
    "source_anchor",
    "license",
    "source_domain",
    "source_repo_path",
    "source_ref",
    "imports",
    "local_imports",
    "custom_imports",
    "uses_custom_library",
    "is_plain_manim_candidate",
    "requires_manual_conversion",
    "target_duration_seconds",
    "target_duration_tolerance_seconds",
]


def _validate_case(case: dict[str, Any]) -> dict[str, Any]:
    required = {"case_id", "prompt", "completion"}
    missing = sorted(required - case.keys())
    if missing:
        raise ValueError(f"Case {case!r} is missing required keys: {missing}")
    if not case["completion"].strip():
        raise ValueError(f"Case {case['case_id']} has an empty completion.")
    cleaned = dict(case)
    cleaned["system"] = case.get("system", DEFAULT_SYSTEM_PROMPT)
    cleaned["must_contain"] = list(case.get("must_contain", []))
    cleaned["must_not_contain"] = list(case.get("must_not_contain", []))
    cleaned["tags"] = list(case.get("tags", []))
    return cleaned


def _split_cases(cases: list[dict[str, Any]], split_config: SplitConfig) -> dict[str, list[dict[str, Any]]]:
    if len(cases) < 3:
        raise ValueError("Need at least three Manim examples to create train/valid/test splits.")
    shuffled = list(cases)
    random.Random(split_config.seed).shuffle(shuffled)
    train_count = max(1, int(len(shuffled) * split_config.train_fraction))
    valid_count = max(1, int(len(shuffled) * split_config.valid_fraction))
    train_count = min(train_count, len(shuffled) - 2)
    valid_count = min(valid_count, len(shuffled) - train_count - 1)
    return {
        "train": shuffled[:train_count],
        "valid": shuffled[train_count : train_count + valid_count],
        "test": shuffled[train_count + valid_count :],
    }


def _to_record(case: dict[str, Any]) -> dict[str, Any]:
    record = {
        "case_id": case["case_id"],
        "tags": case["tags"],
        "entry_scene": case.get("entry_scene"),
        "must_contain": case["must_contain"],
        "must_not_contain": case["must_not_contain"],
        "messages": [
            {"role": "system", "content": case["system"]},
            {"role": "user", "content": case["prompt"]},
            {"role": "assistant", "content": case["completion"]},
        ],
    }
    for field in PASSTHROUGH_FIELDS:
        if field in case:
            record[field] = case[field]
    return record


def build_dataset(source_path: Path, output_dir: Path, split_config: SplitConfig) -> dict[str, Any]:
    source_cases = [_validate_case(case) for case in load_records(source_path)]
    case_ids = [case["case_id"] for case in source_cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError(f"Duplicate case_id values found in {source_path}.")
    split_map = _split_cases(source_cases, split_config)
    ensure_dir(output_dir)
    counts: dict[str, int] = {}
    for split_name, cases in split_map.items():
        records = [_to_record(case) for case in cases]
        write_jsonl(output_dir / f"{split_name}.jsonl", records)
        counts[split_name] = len(records)
    manifest = {
        "source_dataset": str(source_path),
        "output_dir": str(output_dir),
        "split_seed": split_config.seed,
        "counts": counts,
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest
