from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mac_pipeline.case_records import PASSTHROUGH_FIELDS, case_to_chat_record, prepare_cases, split_cases
from mac_pipeline.dataset_sources import load_source_records
from mac_pipeline.types import DatasetFilterConfig, DatasetSourceConfig, SplitConfig
from mac_pipeline.utils import ensure_dir, write_json, write_jsonl

HF_CASES_CONFIG = "cases"
HF_CHAT_CONFIG = "chat"


def export_hf_dataset(
    source: DatasetSourceConfig,
    output_dir: Path,
    split_config: SplitConfig,
    dataset_filter: DatasetFilterConfig | None = None,
    repo_id: str | None = None,
    pretty_name: str | None = None,
    license_name: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    source_records, source_label = load_source_records(source)
    cases = prepare_cases(source_records, dataset_filter, source_label)
    split_map = split_cases(cases, split_config)

    ensure_dir(output_dir)
    write_jsonl(output_dir / "cases.jsonl", [_case_to_hf_case_record(case) for case in cases])

    chat_dir = ensure_dir(output_dir / HF_CHAT_CONFIG)
    split_counts: dict[str, int] = {}
    for split_name, split_cases_payload in split_map.items():
        hf_split_name = "validation" if split_name == "valid" else split_name
        chat_records = [_case_to_hf_chat_record(case) for case in split_cases_payload]
        write_jsonl(chat_dir / f"{hf_split_name}.jsonl", chat_records)
        split_counts[hf_split_name] = len(chat_records)

    metadata = {
        "source_dataset": source.describe(),
        "counts": {
            "cases": len(cases),
            "chat": split_counts,
        },
        "split_seed": split_config.seed,
        "dataset_filter": {
            "include_tags": (dataset_filter or DatasetFilterConfig()).include_tags,
            "exclude_tags": (dataset_filter or DatasetFilterConfig()).exclude_tags,
        },
        "repo_id": repo_id,
        "pretty_name": pretty_name,
        "license": license_name,
        "tags": tags or [],
    }
    write_json(output_dir / "hf_dataset_manifest.json", metadata)
    (output_dir / "README.md").write_text(
        build_dataset_card(
            metadata=metadata,
            output_dir=output_dir,
        )
    )
    return metadata


def build_dataset_card(metadata: dict[str, Any], output_dir: Path) -> str:
    title = metadata.get("pretty_name") or metadata.get("repo_id") or output_dir.name
    counts = metadata["counts"]
    repo_id = metadata.get("repo_id")
    column_names = [
        "case_id",
        "system",
        "prompt",
        "completion",
        "messages",
        "tags",
        "entry_scene",
        "must_contain",
        "must_not_contain",
        *PASSTHROUGH_FIELDS,
    ]
    lines = [
        _build_frontmatter(metadata),
        f"# {title}",
        "",
        "Curated Manim code-generation examples exported from the `autoresearch_manim_finetune` pipeline.",
        "",
        "## Configs",
        "",
        f"- `{HF_CASES_CONFIG}`: canonical unsplit cases stored in `cases.jsonl` and intended as the source-of-truth corpus.",
        f"- `{HF_CHAT_CONFIG}`: train-ready SFT records with `train`, `validation`, and `test` splits stored under `chat/`.",
        "",
        "## Counts",
        "",
        f"- Canonical cases: {counts['cases']}",
        f"- Chat train: {counts['chat']['train']}",
        f"- Chat validation: {counts['chat']['validation']}",
        f"- Chat test: {counts['chat']['test']}",
        "",
        "## Columns",
        "",
    ]
    lines.extend(f"- `{column}`" for column in column_names)
    lines.extend(
        [
            "",
            "## Notes",
            "",
            f"- Source dataset: `{metadata['source_dataset']}`",
            f"- Split seed: `{metadata['split_seed']}`",
        ]
    )
    if metadata["dataset_filter"]["include_tags"]:
        lines.append(
            "- Included tags: `"
            + "`, `".join(metadata["dataset_filter"]["include_tags"])
            + "`"
        )
    if metadata["dataset_filter"]["exclude_tags"]:
        lines.append(
            "- Excluded tags: `"
            + "`, `".join(metadata["dataset_filter"]["exclude_tags"])
            + "`"
        )
    if repo_id:
        lines.extend(
            [
                "",
                "## Loading",
                "",
                "```python",
                "from datasets import load_dataset",
                "",
                f"cases = load_dataset({json.dumps(repo_id)}, {json.dumps(HF_CASES_CONFIG)}, split=\"train\")",
                f"chat = load_dataset({json.dumps(repo_id)}, {json.dumps(HF_CHAT_CONFIG)})",
                "```",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def _build_frontmatter(metadata: dict[str, Any]) -> str:
    lines = ["---", "configs:"]
    lines.extend(
        [
            f"- config_name: {HF_CASES_CONFIG}",
            "  data_files:",
            "  - split: train",
            "    path: cases.jsonl",
            f"- config_name: {HF_CHAT_CONFIG}",
            "  data_files:",
            "  - split: train",
            "    path: chat/train.jsonl",
            "  - split: validation",
            "    path: chat/validation.jsonl",
            "  - split: test",
            "    path: chat/test.jsonl",
        ]
    )
    if metadata.get("pretty_name"):
        lines.append(f"pretty_name: {json.dumps(metadata['pretty_name'])}")
    if metadata.get("license"):
        lines.append(f"license: {metadata['license']}")
    if metadata.get("tags"):
        lines.append("tags:")
        lines.extend(f"- {tag}" for tag in metadata["tags"])
    lines.append("---")
    return "\n".join(lines)


def _case_to_hf_case_record(case: dict[str, Any]) -> dict[str, Any]:
    record = {
        "case_id": case["case_id"],
        "system": case["system"],
        "prompt": case["prompt"],
        "completion": case["completion"],
        "tags": case["tags"],
        "entry_scene": case.get("entry_scene"),
        "must_contain": case["must_contain"],
        "must_not_contain": case["must_not_contain"],
    }
    for field in PASSTHROUGH_FIELDS:
        record[field] = case.get(field)
    return record


def _case_to_hf_chat_record(case: dict[str, Any]) -> dict[str, Any]:
    return case_to_chat_record(case)
