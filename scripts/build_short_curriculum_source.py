from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-duration", type=int, default=10)
    args = parser.parse_args()

    records = [
        record
        for record in _load_records(Path(args.input))
        if _duration(record) <= args.max_duration
    ]
    if len(records) < 3:
        raise ValueError("Need at least three records for a short curriculum.")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(record) + "\n" for record in records))
    print(
        json.dumps(
            {
                "output": str(output),
                "num_records": len(records),
                "max_duration": args.max_duration,
                "targeted_records": sum(_is_targeted(record) for record in records),
            },
            indent=2,
        )
    )


def _duration(record: dict) -> int:
    value = record.get("target_duration_seconds")
    if value is not None:
        return int(value)
    for tag in record.get("tags", []):
        if tag.startswith("duration:") and tag.endswith("s"):
            return int(tag.removeprefix("duration:").removesuffix("s"))
    return 999


def _is_targeted(record: dict) -> bool:
    tags = set(record.get("tags", []))
    return bool(tags & {"raw-failure-refresh", "demo-failure-refresh", "api-error-refresh"})


def _load_records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


if __name__ == "__main__":
    main()
