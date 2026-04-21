#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {
    "case_id": str,
    "prompt": str,
    "completion": str,
    "entry_scene": str,
    "tags": list,
    "must_contain": list,
    "must_not_contain": list,
}
CASE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_]*$")
SCENE_BASES = {"Scene", "ThreeDScene", "MovingCameraScene", "ZoomedScene"}


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


def base_name(base: ast.expr) -> str:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    if isinstance(base, ast.Subscript):
        return base_name(base.value)
    return ""


def scene_classes(source: str) -> tuple[list[str], str | None]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [], f"{exc.msg} at line {exc.lineno}"

    classes: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        bases = {base_name(base) for base in node.bases}
        if bases & SCENE_BASES:
            classes.append(node.name)
    return classes, None


def normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def check_list_field(record: dict[str, Any], field: str, label: str) -> list[str]:
    issues: list[str] = []
    values = record.get(field)
    if not isinstance(values, list):
        return [f"{label}: {field} must be a list"]
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            issues.append(f"{label}: {field}[{index}] must be a non-empty string")
    return issues


def audit_record(
    record: dict[str, Any],
    index: int,
    canonical_ids: set[str],
    min_tags: int,
) -> dict[str, Any]:
    label = f"record[{index}]"
    errors: list[str] = []
    warnings: list[str] = []

    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in record:
            errors.append(f"{label}: missing required field {field}")
            continue
        if not isinstance(record[field], expected_type):
            errors.append(
                f"{label}: {field} must be {expected_type.__name__}, "
                f"got {type(record[field]).__name__}"
            )

    errors.extend(check_list_field(record, "tags", label))
    errors.extend(check_list_field(record, "must_contain", label))
    errors.extend(check_list_field(record, "must_not_contain", label))

    case_id = record.get("case_id")
    if isinstance(case_id, str):
        if not CASE_ID_PATTERN.match(case_id):
            errors.append(f"{label}: case_id should be lowercase snake_case")
        if case_id in canonical_ids:
            errors.append(f"{case_id}: duplicate case_id already in canonical dataset")

    tags = record.get("tags", [])
    if isinstance(tags, list):
        if len(tags) < min_tags:
            warnings.append(f"{case_id}: has only {len(tags)} tags")
        for expected in ("review-candidate", "tier:candidate", "status:unreviewed"):
            if expected not in tags:
                warnings.append(f"{case_id}: missing staging tag {expected}")

    prompt = record.get("prompt")
    if isinstance(prompt, str) and len(prompt.strip()) < 80:
        warnings.append(f"{case_id}: prompt is short for a training sample")

    license_name = record.get("license")
    if not isinstance(license_name, str) or not license_name.strip():
        warnings.append(f"{case_id}: missing license")

    completion = record.get("completion")
    entry_scene = record.get("entry_scene")
    classes: list[str] = []
    syntax_error = None
    if isinstance(completion, str):
        classes, syntax_error = scene_classes(completion)
        if syntax_error:
            errors.append(f"{case_id}: completion syntax error: {syntax_error}")
        if "from manim import *" not in completion:
            warnings.append(f"{case_id}: completion should use from manim import *")
        if isinstance(entry_scene, str) and entry_scene not in classes:
            errors.append(f"{case_id}: entry_scene {entry_scene!r} not found")
        if len(classes) != 1:
            warnings.append(f"{case_id}: expected one intended scene class, found {classes}")
        for snippet in record.get("must_contain", []):
            if isinstance(snippet, str) and snippet not in completion:
                errors.append(f"{case_id}: missing must_contain snippet {snippet!r}")
        for snippet in record.get("must_not_contain", []):
            if isinstance(snippet, str) and snippet and snippet in completion:
                errors.append(f"{case_id}: contains forbidden snippet {snippet!r}")

    return {
        "case_id": case_id,
        "errors": errors,
        "warnings": warnings,
        "scene_classes": classes,
        "syntax_error": syntax_error,
    }


def audit_shard(
    input_path: Path,
    canonical_path: Path | None,
    min_tags: int,
) -> dict[str, Any]:
    records = load_records(input_path)
    canonical_ids = set()
    if canonical_path is not None and canonical_path.exists():
        canonical_ids = {
            record["case_id"]
            for record in load_records(canonical_path)
            if isinstance(record.get("case_id"), str)
        }

    ids = [record.get("case_id") for record in records]
    duplicate_ids = sorted(
        case_id
        for case_id, count in Counter(ids).items()
        if isinstance(case_id, str) and count > 1
    )
    prompt_counts = Counter(
        normalized_text(record.get("prompt", ""))
        for record in records
        if isinstance(record.get("prompt"), str)
    )
    duplicate_prompts = sorted(
        prompt
        for prompt, count in prompt_counts.items()
        if prompt and count > 1
    )

    record_results = [
        audit_record(record, index, canonical_ids, min_tags)
        for index, record in enumerate(records)
    ]
    for case_id in duplicate_ids:
        for result in record_results:
            if result["case_id"] == case_id:
                result["errors"].append(f"{case_id}: duplicate case_id in shard")
    if duplicate_prompts:
        duplicate_prompt_set = set(duplicate_prompts)
        for record, result in zip(records, record_results, strict=True):
            prompt = record.get("prompt")
            if isinstance(prompt, str) and normalized_text(prompt) in duplicate_prompt_set:
                result["warnings"].append(f"{result['case_id']}: duplicate prompt text")

    tag_counts = Counter(
        tag
        for record in records
        for tag in record.get("tags", [])
        if isinstance(tag, str)
    )
    must_contain_counts = Counter(
        snippet
        for record in records
        for snippet in record.get("must_contain", [])
        if isinstance(snippet, str)
    )

    errors = [error for result in record_results for error in result["errors"]]
    warnings = [warning for result in record_results for warning in result["warnings"]]
    return {
        "input_path": str(input_path),
        "canonical_path": str(canonical_path) if canonical_path else None,
        "num_records": len(records),
        "num_errors": len(errors),
        "num_warnings": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "tag_counts": dict(sorted(tag_counts.items())),
        "must_contain_counts": dict(sorted(must_contain_counts.items())),
        "records": record_results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit a Manim candidate shard.")
    parser.add_argument("--input", required=True, type=Path, help="Candidate JSON/JSONL path.")
    parser.add_argument("--canonical", type=Path, help="Canonical dataset JSONL path.")
    parser.add_argument("--summary", type=Path, help="Optional JSON summary output path.")
    parser.add_argument("--min-tags", type=int, default=5, help="Warn below this tag count.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = audit_shard(args.input, args.canonical, args.min_tags)
    output = json.dumps(summary, indent=2)
    print(output)
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(output + "\n")
    return 1 if summary["num_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
