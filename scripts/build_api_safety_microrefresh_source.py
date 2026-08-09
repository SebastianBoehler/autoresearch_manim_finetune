from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical", default="data/manim_dataset.jsonl")
    parser.add_argument("--safety", default="data/manim_api_safety_microrefresh.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--safety-copies", type=int, default=4)
    args = parser.parse_args()

    canonical = _load_records(Path(args.canonical))
    safety = _load_records(Path(args.safety))
    records = list(canonical)
    for copy_index in range(args.safety_copies):
        for record in safety:
            cloned = dict(record)
            cloned["case_id"] = f"{record['case_id']}_copy_{copy_index + 1}"
            records.append(cloned)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(record) + "\n" for record in records))
    print(json.dumps({"output": str(output), "num_records": len(records)}, indent=2))


def _load_records(path: Path) -> list[dict]:
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    payload = json.loads(path.read_text())
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON array or JSONL records.")
    return payload


if __name__ == "__main__":
    main()
