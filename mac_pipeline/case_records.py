from __future__ import annotations

import random
from typing import Any, Iterable

from mac_pipeline.types import DatasetFilterConfig, SplitConfig

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


def _extract_message_fields(case: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for message in case.get("messages", []):
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        content = message.get("content")
        if role not in {"system", "user", "assistant"} or not isinstance(content, str):
            continue
        values.setdefault(role, content)
    return values


def normalize_case_record(case: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(case)
    message_fields = _extract_message_fields(cleaned)
    if "system" not in cleaned and "system" in message_fields:
        cleaned["system"] = message_fields["system"]
    if "prompt" not in cleaned and "user" in message_fields:
        cleaned["prompt"] = message_fields["user"]
    if "completion" not in cleaned and "assistant" in message_fields:
        cleaned["completion"] = message_fields["assistant"]

    required = {"case_id", "prompt", "completion"}
    missing = sorted(required - cleaned.keys())
    if missing:
        raise ValueError(f"Case {case!r} is missing required keys: {missing}")
    if not str(cleaned["completion"]).strip():
        raise ValueError(f"Case {cleaned['case_id']} has an empty completion.")

    cleaned["system"] = cleaned.get("system", DEFAULT_SYSTEM_PROMPT)
    for key in ("must_contain", "must_not_contain", "tags"):
        value = cleaned.get(key, [])
        if not isinstance(value, list):
            raise ValueError(f"Case {cleaned['case_id']} has non-list field: {key}")
        cleaned[key] = list(value)
    return cleaned


def split_cases(
    cases: list[dict[str, Any]],
    split_config: SplitConfig,
) -> dict[str, list[dict[str, Any]]]:
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


def matches_filter(case: dict[str, Any], dataset_filter: DatasetFilterConfig) -> bool:
    tags = set(case.get("tags", []))
    if dataset_filter.include_tags and not set(dataset_filter.include_tags).issubset(tags):
        return False
    if dataset_filter.exclude_tags and set(dataset_filter.exclude_tags) & tags:
        return False
    return True


def prepare_cases(
    source_records: Iterable[dict[str, Any]],
    dataset_filter: DatasetFilterConfig | None = None,
    source_label: str = "dataset",
) -> list[dict[str, Any]]:
    normalized_cases = [normalize_case_record(case) for case in source_records]
    effective_filter = dataset_filter or DatasetFilterConfig()
    filtered_cases = [
        case for case in normalized_cases if matches_filter(case, effective_filter)
    ]
    if not filtered_cases:
        raise ValueError(f"No dataset cases matched filter for {source_label}.")
    case_ids = [case["case_id"] for case in filtered_cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError(f"Duplicate case_id values found in {source_label}.")
    return filtered_cases


def case_to_chat_record(case: dict[str, Any]) -> dict[str, Any]:
    record = {
        "case_id": case["case_id"],
        "system": case["system"],
        "prompt": case["prompt"],
        "completion": case["completion"],
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
        record[field] = case.get(field)
    return record
