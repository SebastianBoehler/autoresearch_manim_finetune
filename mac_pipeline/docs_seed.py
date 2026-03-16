from __future__ import annotations

import json
import re
from pathlib import Path
from textwrap import dedent
from typing import Any

import requests
from bs4 import BeautifulSoup

from mac_pipeline.utils import ensure_parent
from mac_pipeline.utils import load_records
from mac_pipeline.utils import write_jsonl

CLASS_PATTERN = re.compile(r"class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
DEFAULT_LICENSE = "MIT"


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    records = load_records(path)
    for record in records:
        missing = {"case_id", "source_url", "source_anchor", "prompt"} - record.keys()
        if missing:
            raise ValueError(f"Manifest entry {record!r} is missing keys: {sorted(missing)}")
    return records


def _fetch_soup(url: str, cache: dict[str, BeautifulSoup]) -> BeautifulSoup:
    if url not in cache:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        cache[url] = BeautifulSoup(response.text, "html.parser")
    return cache[url]


def _extract_code_block(soup: BeautifulSoup, anchor: str) -> str:
    node = soup.find(id=anchor)
    if node is None:
        raise ValueError(f"Could not find docs anchor: {anchor}")
    code_block = node.find_next("pre")
    if code_block is None:
        raise ValueError(f"No code block found after docs anchor: {anchor}")
    code = dedent(code_block.get_text()).strip()
    if not code.startswith("from manim import *"):
        code = f"from manim import *\n\n{code}"
    return code


def _extract_scene_name(code: str) -> str:
    match = CLASS_PATTERN.search(code)
    if not match:
        raise ValueError("Could not detect a scene class in imported code.")
    return match.group(1)


def import_doc_examples(manifest_path: Path, output_path: Path) -> list[dict[str, Any]]:
    manifest = _load_manifest(manifest_path)
    soup_cache: dict[str, BeautifulSoup] = {}
    cases: list[dict[str, Any]] = []
    for record in manifest:
        code = _extract_code_block(_fetch_soup(record["source_url"], soup_cache), record["source_anchor"])
        case = {
            "case_id": record["case_id"],
            "prompt": record["prompt"],
            "completion": code,
            "entry_scene": record.get("entry_scene") or _extract_scene_name(code),
            "tags": list(record.get("tags", [])),
            "must_contain": list(record.get("must_contain", [])),
            "must_not_contain": list(record.get("must_not_contain", [])),
            "source_name": record.get("source_name", record["case_id"]),
            "source_url": record["source_url"],
            "source_anchor": record["source_anchor"],
            "license": record.get("license", DEFAULT_LICENSE),
        }
        if "target_duration_seconds" in record:
            case["target_duration_seconds"] = record["target_duration_seconds"]
        if "target_duration_tolerance_seconds" in record:
            case["target_duration_tolerance_seconds"] = record["target_duration_tolerance_seconds"]
        cases.append(case)
    ensure_parent(output_path)
    if output_path.suffix == ".jsonl":
        write_jsonl(output_path, cases)
    else:
        output_path.write_text(json.dumps(cases, indent=2) + "\n")
    return cases


def merge_case_files(input_paths: list[Path], output_path: Path) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_case_ids: set[str] = set()
    for input_path in input_paths:
        for case in load_records(input_path):
            case_id = case["case_id"]
            if case_id in seen_case_ids:
                raise ValueError(f"Duplicate case_id while merging: {case_id}")
            seen_case_ids.add(case_id)
            merged.append(case)
    ensure_parent(output_path)
    if output_path.suffix == ".jsonl":
        write_jsonl(output_path, merged)
    else:
        output_path.write_text(json.dumps(merged, indent=2) + "\n")
    return merged
