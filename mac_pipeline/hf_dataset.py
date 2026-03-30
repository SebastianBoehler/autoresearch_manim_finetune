from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from mac_pipeline.case_records import PASSTHROUGH_FIELDS, case_to_chat_record, prepare_cases, split_cases
from mac_pipeline.dataset_sources import load_source_records
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
) -> dict[str, Any]:
    source_records, source_label = load_source_records(source)
    cases = prepare_cases(source_records, dataset_filter, source_label)
    ensure_records_have_licenses(cases, source_label=source_label)
    split_map = split_cases(cases, split_config)
    effective_license = license_name or DEFAULT_LICENSE_ID
    effective_license_name = license_label or DEFAULT_LICENSE_NAME
    effective_license_link = license_link or DEFAULT_LICENSE_LINK

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
    }
    _copy_preview_items(output_dir, metadata, preview_items or [])
    _copy_preview_image(output_dir, metadata, preview_image)
    _write_license_notice(output_dir, metadata)
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
    ]
    preview_items = metadata.get("preview_items") or []
    if preview_items:
        lines.extend(
            [
                "## Preview Gallery",
                "",
                *_build_preview_table(preview_items),
                "",
            ]
        )
    elif metadata.get("preview_image"):
        caption = metadata.get("preview_caption") or "Example rendered sample from the dataset."
        lines.extend(
            [
                f"![Dataset preview]({metadata['preview_image']})",
                "",
                f"*{caption}*",
                "",
            ]
        )
    lines.extend(
        [
            "## Summary",
            "",
            "- Focus: supervised fine-tuning and evaluation examples for Manim Community Edition code generation.",
            "- Primary modality: text-to-code pairs with optional provenance and duration metadata.",
            "- Export configs: one canonical source config and one train-ready chat config.",
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
    )
    lines.extend(f"- `{column}`" for column in column_names)
    lines.extend(
        [
            "",
            "## Provenance And Licensing",
            "",
        ]
    )
    if metadata["license"] == "other":
        lines.extend(
            [
                "- Repository-level license metadata is `other` because the export uses a custom or mixed license notice.",
                "- Inspect the exported `license`, `source_url`, `source_repo_path`, and `source_ref` fields per row before reuse.",
                "- See the repository-level `LICENSE` file for the packaging notice used on the Hub.",
            ]
        )
    else:
        lines.extend(
            [
                f"- Repository-level license metadata is `{metadata['license']}`.",
                "- Each exported row carries explicit `license` metadata and should retain its row-level provenance fields.",
                "- Inspect the exported `source_url`, `source_repo_path`, and `source_ref` fields for upstream attribution on adapted rows.",
            ]
        )
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
    if metadata.get("license_name"):
        lines.append(f"license_name: {json.dumps(metadata['license_name'])}")
    if metadata.get("license_link"):
        lines.append(f"license_link: {metadata['license_link']}")
    if metadata.get("languages"):
        lines.append("language:")
        lines.extend(f"- {language}" for language in metadata["languages"])
    if metadata.get("task_categories"):
        lines.append("task_categories:")
        lines.extend(f"- {category}" for category in metadata["task_categories"])
    if metadata.get("size_categories"):
        lines.append("size_categories:")
        lines.extend(f"- {size}" for size in metadata["size_categories"])
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
    for index, item in enumerate(preview_items, start=1):
        raw_path = Path(item["path"]).resolve()
        if not raw_path.exists():
            raise FileNotFoundError(f"Preview image does not exist: {raw_path}")
        destination = asset_dir / raw_path.name
        if destination.exists() and destination.resolve() != raw_path:
            destination = asset_dir / f"{raw_path.stem}-{index}{raw_path.suffix}"
        shutil.copy2(raw_path, destination)
        normalized.append(
            {
                "path": str(Path("assets") / destination.name),
                "caption": item["caption"],
            }
        )
    metadata["preview_items"] = normalized


def _build_preview_table(preview_items: list[dict[str, str]]) -> list[str]:
    columns = 3
    rows: list[str] = []
    for start in range(0, len(preview_items), columns):
        chunk = preview_items[start : start + columns]
        image_cells = [f"![{item['caption']}]({item['path']})" for item in chunk]
        caption_cells = [f"*{item['caption']}*" for item in chunk]
        while len(image_cells) < columns:
            image_cells.append(" ")
            caption_cells.append(" ")
        rows.append("| " + " | ".join(image_cells) + " |")
        rows.append("| " + " | ".join(caption_cells) + " |")
    header = "| Preview | Preview | Preview |"
    separator = "| --- | --- | --- |"
    return [header, separator, *rows]


def _write_license_notice(output_dir: Path, metadata: dict[str, Any]) -> None:
    if metadata.get("license") != "other":
        return
    (output_dir / "LICENSE").write_text(CUSTOM_LICENSE_NOTICE)
