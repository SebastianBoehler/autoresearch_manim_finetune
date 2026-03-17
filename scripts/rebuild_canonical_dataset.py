from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "data" / "manim_dataset.jsonl"
SOURCE_SPECS = [
    ("data/manim_seed_cases.json", ["tier:gold", "source:local"]),
    ("data/manim_docs_seed_cases.jsonl", ["tier:gold", "source:docs"]),
    ("data/manim_docs_feature_cases.jsonl", ["tier:gold", "source:docs"]),
    ("data/manim_converted_cases.jsonl", ["tier:gold", "source:local"]),
    ("data/manim_converted_cases_round2.jsonl", ["tier:gold", "source:local"]),
    ("data/manim_converted_cases_round3.json", ["tier:gold", "source:local"]),
    ("data/manim_animation_cases.json", ["tier:gold", "source:docs"]),
    ("data/manim_coverage_expansion_cases.json", ["tier:gold", "source:local"]),
    ("data/manim_feature_fusion_cases.json", ["tier:gold", "source:local"]),
    ("data/manim_longform_cases.json", ["tier:gold", "source:local"]),
    ("data/manim_composite_longform_cases.json", ["tier:gold", "source:local"]),
    ("data/manim_targeted_composite_cases.json", ["tier:gold", "source:local"]),
    ("data/manim_targeted_composite_variations.json", ["tier:gold", "source:local"]),
    ("data/manim_underrepresented_longform_cases.json", ["tier:gold", "source:local"]),
    ("data/manim_3b1b_style_cases.json", ["tier:gold", "source:local"]),
    ("data/manim_repo_plain_verified.jsonl", ["tier:silver", "source:repo"]),
]


def _load_records(path: Path) -> list[dict]:
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    payload = json.loads(path.read_text())
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON array.")
    return payload


def _duration_tags(case: dict) -> list[str]:
    duration = case.get("target_duration_seconds")
    if duration is None:
        return []
    if duration <= 6:
        return ["duration:5s"]
    if duration <= 12:
        return ["duration:10s"]
    if duration <= 22:
        return ["duration:20s"]
    if duration <= 40:
        return ["duration:30s"]
    return ["duration:50s"]


def _merge_tags(case: dict, extra_tags: list[str]) -> dict:
    merged = dict(case)
    tags = list(case.get("tags", []))
    for tag in extra_tags + _duration_tags(case):
        if tag not in tags:
            tags.append(tag)
    merged["tags"] = tags
    return merged


def main() -> None:
    cases: list[dict] = []
    seen_case_ids: set[str] = set()
    for relative_path, extra_tags in SOURCE_SPECS:
        path = REPO_ROOT / relative_path
        for case in _load_records(path):
            case_id = case["case_id"]
            if case_id in seen_case_ids:
                raise ValueError(f"Duplicate case_id while rebuilding canonical dataset: {case_id}")
            seen_case_ids.add(case_id)
            cases.append(_merge_tags(case, extra_tags))

    OUTPUT_PATH.write_text("".join(json.dumps(case) + "\n" for case in cases))
    print(f"Wrote {len(cases)} cases to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
