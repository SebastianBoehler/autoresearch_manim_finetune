from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mac_pipeline.case_records import case_to_chat_record, prepare_cases
from mac_pipeline.curation import apply_curation, records_digest
from mac_pipeline.grouped_split import split_grouped_cases
from mac_pipeline.types import SplitConfig
from mac_pipeline.utils import ensure_dir, load_records, write_json, write_jsonl
from mac_pipeline.versioned_api import build_api_coverage


def export_curated_dataset(
    *,
    source_path: Path,
    curation_manifest_path: Path,
    api_surface_path: Path,
    output_dir: Path,
    split_config: SplitConfig,
) -> dict[str, Any]:
    source_records = load_records(source_path)
    curation_manifest = json.loads(curation_manifest_path.read_text())
    api_surface = json.loads(api_surface_path.read_text())
    runtime = curation_manifest["target_runtime"]
    if api_surface.get("manim_version") != runtime["manim_version"]:
        raise ValueError("API surface version does not match curation target runtime.")
    public_symbols = set(api_surface.get("public_symbols", []))
    result = apply_curation(source_records, curation_manifest, public_symbols=public_symbols)
    accepted = prepare_cases(result.accepted, source_label=f"curated:{source_path}")
    split_map = split_grouped_cases(accepted, split_config)

    ensure_dir(output_dir)
    write_jsonl(output_dir / "cases.jsonl", accepted)
    write_jsonl(
        output_dir / "api_reference.jsonl",
        [row for row in accepted if "api_reference" in row["corpus_roles"]],
    )
    write_jsonl(output_dir / "quarantine.jsonl", result.quarantine)
    write_jsonl(output_dir / "rewrite.jsonl", result.rewrite)
    chat_split_map = {
        split_name: [case_to_chat_record(row) for row in rows]
        for split_name, rows in split_map.items()
    }
    for split_name, rows in chat_split_map.items():
        write_jsonl(output_dir / f"{split_name}.jsonl", rows)
    ablations = write_ablation_variants(chat_split_map, output_dir / "ablations")

    coverage = build_api_coverage(accepted, public_symbols=public_symbols)
    coverage["manim_version"] = runtime["manim_version"]
    (output_dir / "api_coverage.json").write_text(
        json.dumps(coverage, sort_keys=True, separators=(",", ":")) + "\n"
    )
    summary = {
        "schema_version": 1,
        "dataset_version": curation_manifest["dataset_version"],
        "source_path": str(source_path),
        "curation_manifest_path": str(curation_manifest_path),
        "api_surface_path": str(api_surface_path),
        "target_runtime": runtime,
        "source_sha256": records_digest(source_records),
        "curated_sha256": records_digest(accepted),
        "counts": result.summary,
        "split_counts": {name: len(rows) for name, rows in split_map.items()},
        "split_seed": split_config.seed,
        "split_policy": "concept-and-source-grouped-v1",
        "ablation_variants": ablations["variants"],
    }
    write_json(output_dir / "manifest.json", summary)
    return summary
from mac_pipeline.ablation_variants import write_ablation_variants
