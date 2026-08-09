from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from mac_pipeline.case_records import PASSTHROUGH_FIELDS, case_to_chat_record, prepare_cases, split_cases
from mac_pipeline.dataset_sources import load_source_records
from mac_pipeline.hf_frozen_splits import (
    load_curated_publication_metadata,
    load_frozen_chat_splits,
)
from mac_pipeline.hf_dataset_card import (
    build_dataset_card,
    validate_dataset_card_asset_paths as _validate_dataset_card_asset_paths,
)
from mac_pipeline.license_metadata import DEFAULT_DATASET_LICENSE_ID, ensure_records_have_licenses
from mac_pipeline.types import DatasetFilterConfig, DatasetSourceConfig, SplitConfig
from mac_pipeline.utils import ensure_dir, write_json, write_jsonl

HF_CASES_CONFIG = "cases"
HF_CHAT_CONFIG = "chat"
DEFAULT_LICENSE_ID = DEFAULT_DATASET_LICENSE_ID
DEFAULT_LICENSE_NAME = None
DEFAULT_LICENSE_LINK = None
CUSTOM_LICENSE_NOTICE = """Mixed-provenance dataset notice

This repository does not grant a single blanket license over every row in the dataset.

Each sample should be evaluated using its row-level provenance fields, especially:
- `license`
- `source_url`
- `source_repo_path`
- `source_ref`

Rows without explicit license metadata in the exported files should be treated as requiring
independent provenance verification before redistribution or downstream commercial use.

The dataset card and README describe the repository-level packaging only. They do not override
any row-level source licensing terms.
"""


def export_hf_dataset(
    source: DatasetSourceConfig,
    output_dir: Path,
    split_config: SplitConfig,
    dataset_filter: DatasetFilterConfig | None = None,
    repo_id: str | None = None,
    pretty_name: str | None = None,
    license_name: str | None = None,
    license_label: str | None = None,
    license_link: str | None = None,
    languages: list[str] | None = None,
    task_categories: list[str] | None = None,
    size_categories: list[str] | None = None,
    tags: list[str] | None = None,
    preview_image: Path | None = None,
    preview_caption: str | None = None,
    preview_items: list[dict[str, str]] | None = None,
    frozen_splits_dir: Path | None = None,
) -> dict[str, Any]:
    source_records, source_label = load_source_records(source)
    cases = prepare_cases(source_records, dataset_filter, source_label)
    ensure_records_have_licenses(cases, source_label=source_label)
    split_map = split_cases(cases, split_config) if frozen_splits_dir is None else None
    effective_license = license_name or DEFAULT_LICENSE_ID
    effective_license_name = license_label or DEFAULT_LICENSE_NAME
    effective_license_link = license_link or DEFAULT_LICENSE_LINK

    ensure_dir(output_dir)
    write_jsonl(output_dir / "cases.jsonl", [_case_to_hf_case_record(case) for case in cases])

    chat_dir = ensure_dir(output_dir / HF_CHAT_CONFIG)
    split_counts: dict[str, int] = {}
    chat_split_map = (
        {
            split_name: [_case_to_hf_chat_record(case) for case in split_cases_payload]
            for split_name, split_cases_payload in split_map.items()
        }
        if split_map is not None
        else load_frozen_chat_splits(cases, frozen_splits_dir)
    )
    for split_name, chat_records in chat_split_map.items():
        hf_split_name = "validation" if split_name == "valid" else split_name
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
        "license": effective_license,
        "license_name": effective_license_name,
        "license_link": effective_license_link,
        "languages": languages or [],
        "task_categories": task_categories or [],
        "size_categories": size_categories or [],
        "tags": tags or [],
        "preview_image": None,
        "preview_caption": preview_caption,
        "preview_items": [],
        "split_policy": "random-seed" if frozen_splits_dir is None else "frozen-precomputed",
        "curation": (
            load_curated_publication_metadata(frozen_splits_dir)
            if frozen_splits_dir is not None
            else None
        ),
    }
    _copy_preview_items(output_dir, metadata, preview_items or [])
    _copy_preview_image(output_dir, metadata, preview_image)
    _write_license_notice(output_dir, metadata)
    write_json(output_dir / "hf_dataset_manifest.json", metadata)
    dataset_card = build_dataset_card(
        metadata=metadata,
        output_dir=output_dir,
    )
    _validate_dataset_card_asset_paths(dataset_card, output_dir)
    (output_dir / "README.md").write_text(dataset_card)
    return metadata


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


def _copy_preview_image(
    output_dir: Path,
    metadata: dict[str, Any],
    preview_image: Path | None,
) -> None:
    if preview_image is None:
        return
    preview_path = preview_image.resolve()
    if not preview_path.exists():
        raise FileNotFoundError(f"Preview image does not exist: {preview_path}")
    asset_dir = ensure_dir(output_dir / "assets")
    destination = asset_dir / preview_path.name
    shutil.copy2(preview_path, destination)
    metadata["preview_image"] = str(Path("assets") / preview_path.name)


def _copy_preview_items(
    output_dir: Path,
    metadata: dict[str, Any],
    preview_items: list[dict[str, str]],
) -> None:
    if not preview_items:
        return
    asset_dir = ensure_dir(output_dir / "assets")
    normalized: list[dict[str, str]] = []
    used_names: set[str] = set()
    for index, item in enumerate(preview_items, start=1):
        raw_path = Path(item["path"]).resolve()
        if not raw_path.exists():
            raise FileNotFoundError(f"Preview image does not exist: {raw_path}")
        destination_name = raw_path.name
        if destination_name in used_names:
            destination_name = f"{raw_path.stem}-{index}{raw_path.suffix}"
        used_names.add(destination_name)
        destination = asset_dir / destination_name
        _copy_file_if_different(raw_path, destination)
        normalized.append(
            {
                "path": str(Path("assets") / destination.name),
                "caption": item["caption"],
            }
        )
    metadata["preview_items"] = normalized


def _copy_file_if_different(source: Path, destination: Path) -> None:
    if destination.exists() and destination.resolve() == source.resolve():
        return
    shutil.copy2(source, destination)


def _write_license_notice(output_dir: Path, metadata: dict[str, Any]) -> None:
    if metadata.get("license") != "other":
        return
    (output_dir / "LICENSE").write_text(CUSTOM_LICENSE_NOTICE)
