from __future__ import annotations

from pathlib import Path
from typing import Any

from mac_pipeline.case_records import case_to_chat_record, prepare_cases, split_cases
from mac_pipeline.dataset_sources import load_source_records
from mac_pipeline.types import DatasetFilterConfig, DatasetSourceConfig, SplitConfig
from mac_pipeline.utils import ensure_dir, write_json, write_jsonl


def build_dataset_from_records(
    source_records: list[dict[str, Any]],
    source_label: str,
    source_spec: dict[str, Any],
    output_dir: Path,
    split_config: SplitConfig,
    dataset_filter: DatasetFilterConfig | None = None,
) -> dict[str, Any]:
    effective_filter = dataset_filter or DatasetFilterConfig()
    filtered_cases = prepare_cases(source_records, effective_filter, source_label)
    split_map = split_cases(filtered_cases, split_config)
    ensure_dir(output_dir)

    counts: dict[str, int] = {}
    for split_name, cases in split_map.items():
        records = [case_to_chat_record(case) for case in cases]
        write_jsonl(output_dir / f"{split_name}.jsonl", records)
        counts[split_name] = len(records)

    manifest = {
        "source_dataset": source_label,
        "source_dataset_spec": source_spec,
        "output_dir": str(output_dir),
        "split_seed": split_config.seed,
        "dataset_filter": {
            "include_tags": effective_filter.include_tags,
            "exclude_tags": effective_filter.exclude_tags,
        },
        "counts": counts,
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def build_dataset(
    source: DatasetSourceConfig | Path,
    output_dir: Path,
    split_config: SplitConfig,
    dataset_filter: DatasetFilterConfig | None = None,
) -> dict[str, Any]:
    source_config = (
        DatasetSourceConfig(kind="local", path=str(source))
        if isinstance(source, Path)
        else source
    )
    source_records, source_label = load_source_records(source_config)
    return build_dataset_from_records(
        source_records=source_records,
        source_label=source_label,
        source_spec=source_config.__dict__,
        output_dir=output_dir,
        split_config=split_config,
        dataset_filter=dataset_filter,
    )
