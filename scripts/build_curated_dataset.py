from __future__ import annotations

import argparse
from pathlib import Path

from mac_pipeline.curated_export import export_curated_dataset
from mac_pipeline.types import SplitConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the versioned curated Manim dataset.")
    parser.add_argument("--source", type=Path, default=Path("data/manim_dataset.jsonl"))
    parser.add_argument(
        "--curation-manifest",
        type=Path,
        default=Path("data/manim_curation_v1.json"),
    )
    parser.add_argument(
        "--api-surface",
        type=Path,
        default=Path("data/manim_api_surface_v0_20_1.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/curated/manim_v0_20_1"),
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    summary = export_curated_dataset(
        source_path=args.source,
        curation_manifest_path=args.curation_manifest,
        api_surface_path=args.api_surface,
        output_dir=args.output,
        split_config=SplitConfig(seed=args.seed),
    )
    print(summary)


if __name__ == "__main__":
    main()
