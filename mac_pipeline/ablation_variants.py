from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from mac_pipeline.utils import ensure_dir, write_json, write_jsonl


def write_ablation_variants(
    split_map: dict[str, list[dict[str, Any]]],
    output_dir: Path,
) -> dict[str, Any]:
    predicates: dict[str, Callable[[dict[str, Any]], bool]] = {
        "pedagogical_only": lambda row: "pedagogical" in row.get("corpus_roles", []),
        "api_reference_only": lambda row: "api_reference" in row.get("corpus_roles", []),
        "without_composite": lambda row: "composite" not in row.get("corpus_roles", []),
    }
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "holdout_policy": "shared-valid-and-test-from-full-curated-split",
        "variants": {},
    }
    for name, predicate in predicates.items():
        variant_dir = ensure_dir(output_dir / name)
        train_rows = sorted(filter(predicate, split_map["train"]), key=lambda row: row["case_id"])
        if not train_rows:
            raise ValueError(f"Ablation variant {name} has no training rows.")
        write_jsonl(variant_dir / "train.jsonl", train_rows)
        for split_name in ("valid", "test"):
            write_jsonl(
                variant_dir / f"{split_name}.jsonl",
                sorted(split_map[split_name], key=lambda row: row["case_id"]),
            )
        manifest["variants"][name] = {
            "train": len(train_rows),
            "valid": len(split_map["valid"]),
            "test": len(split_map["test"]),
        }
    write_json(output_dir / "manifest.json", manifest)
    return manifest
