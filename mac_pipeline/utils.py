from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


def resolve_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base_dir / path)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        return [
            json.loads(line)
            for line in path.read_text().splitlines()
            if line.strip()
        ]
    payload = json.loads(path.read_text())
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON array or JSONL records.")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_parent(path).write_text(json.dumps(payload, indent=2) + "\n")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    ensure_parent(path)
    with path.open("w") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def append_tsv(path: Path, row: dict[str, Any], fieldnames: list[str]) -> None:
    ensure_parent(path)
    needs_header = not path.exists()
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        if needs_header:
            writer.writeheader()
        writer.writerow(row)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "run"

