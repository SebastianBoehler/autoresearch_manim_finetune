from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from mac_pipeline.case_records import PASSTHROUGH_FIELDS


HF_CASES_CONFIG = "cases"
HF_CHAT_CONFIG = "chat"


def build_dataset_card(metadata: dict[str, Any], output_dir: Path) -> str:
    title = metadata.get("pretty_name") or metadata.get("repo_id") or output_dir.name
    counts = metadata["counts"]
    repo_id = metadata.get("repo_id")
    lines = [
        _build_frontmatter(metadata),
        f"# {title}",
        "",
        "Curated Manim code-generation examples exported from the `autoresearch_manim_finetune` pipeline.",
        "",
    ]
    _append_preview(lines, metadata)
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
            f"- `{HF_CASES_CONFIG}`: {'accepted curated' if metadata.get('curation') else 'canonical unsplit'} cases stored in `cases.jsonl`.",
            f"- `{HF_CHAT_CONFIG}`: train-ready SFT records with `train`, `validation`, and `test` splits stored under `chat/`.",
            "",
            "## Counts",
            "",
            f"- {'Curated accepted' if metadata.get('curation') else 'Canonical'} cases: {counts['cases']}",
            f"- Chat train: {counts['chat']['train']}",
            f"- Chat validation: {counts['chat']['validation']}",
            f"- Chat test: {counts['chat']['test']}",
            "",
        ]
    )
    _append_quality_contract(lines, metadata.get("curation"))
    lines.extend(["## Columns", ""])
    lines.extend(f"- `{column}`" for column in _column_names())
    _append_provenance(lines, metadata)
    curation = metadata.get("curation")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            f"- {'Curation source' if curation else 'Source dataset'}: `{curation['source_path'] if curation else metadata['source_dataset']}`",
            f"- Split seed: `{metadata['split_seed']}`",
        ]
    )
    _append_filters(lines, metadata["dataset_filter"])
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


def validate_dataset_card_asset_paths(card: str, output_dir: Path) -> None:
    for raw_path in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", card):
        parsed = urlparse(raw_path)
        if parsed.scheme or raw_path.startswith("#"):
            continue
        clean_path = Path(unquote(parsed.path))
        if clean_path.is_absolute() or ".." in clean_path.parts:
            raise ValueError(f"Dataset card image path must stay inside export: {raw_path}")
        if not (output_dir / clean_path).exists():
            raise FileNotFoundError(f"Dataset card references missing image: {raw_path}")


def _column_names() -> list[str]:
    return [
        "case_id", "system", "prompt", "completion", "messages", "tags",
        "entry_scene", "must_contain", "must_not_contain", *PASSTHROUGH_FIELDS,
    ]


def _append_preview(lines: list[str], metadata: dict[str, Any]) -> None:
    preview_items = metadata.get("preview_items") or []
    if preview_items:
        lines.extend(["## Preview Gallery", "", *_build_preview_table(preview_items), ""])
    elif metadata.get("preview_image"):
        caption = metadata.get("preview_caption") or "Example rendered sample from the dataset."
        lines.extend(
            [f"![Dataset preview]({metadata['preview_image']})", "", f"*{caption}*", ""]
        )


def _append_quality_contract(lines: list[str], curation: dict[str, Any] | None) -> None:
    if not curation:
        return
    runtime = curation["target_runtime"]
    disposition = curation["counts"]
    coverage = curation["api_coverage"]
    lines.extend(
        [
            "## Quality Contract",
            "",
            f"- Dataset version: `{curation['dataset_version']}`.",
            f"- Runtime: Manim Community Edition `{runtime['manim_version']}`, Python `{runtime['python_version']}`, `{runtime['renderer']}` renderer.",
            "- Every published case is an accepted, exact-scene-render-verified row.",
            f"- Frozen split policy: `{curation['split_policy']}`; validation and test groups are isolated from training.",
            f"- Source dispositions: {disposition['accepted']} accepted, {disposition['quarantine']} quarantined, {disposition['rewrite']} queued for rewrite, from {disposition['source']} source rows.",
            f"- API coverage: {coverage['used_symbols']} of {coverage['public_symbols']} public symbols and {coverage['used_methods']} inferred methods.",
            "",
        ]
    )


def _append_provenance(lines: list[str], metadata: dict[str, Any]) -> None:
    lines.extend(["", "## Provenance And Licensing", ""])
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


def _append_filters(lines: list[str], dataset_filter: dict[str, list[str]]) -> None:
    if dataset_filter["include_tags"]:
        lines.append("- Included tags: `" + "`, `".join(dataset_filter["include_tags"]) + "`")
    if dataset_filter["exclude_tags"]:
        lines.append("- Excluded tags: `" + "`, `".join(dataset_filter["exclude_tags"]) + "`")


def _build_frontmatter(metadata: dict[str, Any]) -> str:
    lines = [
        "---", "configs:", f"- config_name: {HF_CASES_CONFIG}", "  data_files:",
        "  - split: train", "    path: cases.jsonl", f"- config_name: {HF_CHAT_CONFIG}",
        "  data_files:", "  - split: train", "    path: chat/train.jsonl",
        "  - split: validation", "    path: chat/validation.jsonl",
        "  - split: test", "    path: chat/test.jsonl",
    ]
    scalar_fields = (("pretty_name", "pretty_name"), ("license", "license"),
                     ("license_name", "license_name"), ("license_link", "license_link"))
    for key, label in scalar_fields:
        if metadata.get(key):
            value = json.dumps(metadata[key]) if key in {"pretty_name", "license_name"} else metadata[key]
            lines.append(f"{label}: {value}")
    for key, label in (("languages", "language"), ("task_categories", "task_categories"),
                       ("size_categories", "size_categories"), ("tags", "tags")):
        if metadata.get(key):
            lines.append(f"{label}:")
            lines.extend(f"- {value}" for value in metadata[key])
    lines.append("---")
    return "\n".join(lines)


def _build_preview_table(preview_items: list[dict[str, str]]) -> list[str]:
    rows = ["| Preview | Preview | Preview |", "| --- | --- | --- |"]
    for start in range(0, len(preview_items), 3):
        chunk = preview_items[start : start + 3]
        images = [f"![{item['caption']}]({item['path']})" for item in chunk]
        captions = [f"*{item['caption']}*" for item in chunk]
        images.extend([" "] * (3 - len(images)))
        captions.extend([" "] * (3 - len(captions)))
        rows.extend(["| " + " | ".join(images) + " |", "| " + " | ".join(captions) + " |"])
    return rows
