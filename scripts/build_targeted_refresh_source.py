from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical", default="data/manim_dataset.jsonl")
    parser.add_argument("--output", required=True)
    parser.add_argument("--extra", nargs=2, action="append", metavar=("PATH", "COPIES"))
    args = parser.parse_args()

    records = _load_records(Path(args.canonical))
    for path_text, copies_text in args.extra or []:
        extra_records = _load_records(Path(path_text))
        records.extend(_copied_records(extra_records, int(copies_text)))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(record) + "\n" for record in records))
    print(json.dumps({"output": str(output), "num_records": len(records)}, indent=2))


def _copied_records(records: list[dict], copies: int) -> list[dict]:
    copied: list[dict] = []
    for copy_index in range(copies):
        for record in records:
            cloned = dict(record)
            cloned["case_id"] = f"{record['case_id']}_copy_{copy_index + 1}"
            copied.append(cloned)
    return copied


def _load_records(path: Path) -> list[dict]:
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    payload = json.loads(path.read_text())
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON array or JSONL records.")
    return payload


if __name__ == "__main__":
    main()
