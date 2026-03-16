from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def _filter_records(records: list[dict], exclude_tags: set[str]) -> list[dict]:
    if not exclude_tags:
        return records
    filtered = []
    for record in records:
        tags = set(record.get("tags", []))
        if tags & exclude_tags:
            continue
        filtered.append(record)
    return filtered


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a filtered dataset split variant.")
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--exclude-tags", nargs="*", default=[])
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    exclude_tags = set(args.exclude_tags)

    for split in ("train", "valid"):
        records = _load_jsonl(source_dir / f"{split}.jsonl")
        _write_jsonl(output_dir / f"{split}.jsonl", _filter_records(records, exclude_tags))

    shutil.copy2(source_dir / "test.jsonl", output_dir / "test.jsonl")
    manifest = json.loads((source_dir / "manifest.json").read_text())
    manifest["output_dir"] = str(output_dir)
    manifest["variant_exclude_tags"] = sorted(exclude_tags)
    manifest["counts"] = {
        "train": len(_load_jsonl(output_dir / "train.jsonl")),
        "valid": len(_load_jsonl(output_dir / "valid.jsonl")),
        "test": len(_load_jsonl(output_dir / "test.jsonl")),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
