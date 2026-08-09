from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any

from mac_pipeline.types import SplitConfig


_META_TAGS = {
    "composite",
    "converted",
    "coverage",
    "curated",
    "docs",
    "fusion",
    "learning-app",
    "longform",
    "round13",
    "targeted",
    "taste",
}
_PROMPT_STOPWORDS = {
    "a", "an", "and", "animate", "create", "explain", "for", "from", "in",
    "manim", "of", "on", "scene", "show", "that", "the", "then", "to", "use",
    "using", "with",
}


def assign_split_groups(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    parent = list(range(len(cases)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    concept_tags = [_concept_tags(case) for case in cases]
    prompt_tokens = [_prompt_tokens(case.get("prompt", "")) for case in cases]
    provenance = [_repo_provenance(case) for case in cases]
    for left in range(len(cases)):
        for right in range(left + 1, len(cases)):
            if provenance[left] and provenance[left] == provenance[right]:
                union(left, right)
                continue
            if _similar(concept_tags[left], concept_tags[right], minimum_size=2, threshold=0.75):
                union(left, right)
                continue
            if _similar(prompt_tokens[left], prompt_tokens[right], minimum_size=5, threshold=0.5):
                union(left, right)

    members: dict[int, list[str]] = defaultdict(list)
    for index, case in enumerate(cases):
        members[find(index)].append(str(case["case_id"]))
    group_names = {
        root: f"group:{sorted(case_ids)[0]}"
        for root, case_ids in members.items()
    }
    grouped: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        enriched = dict(case)
        enriched["split_group"] = group_names[find(index)]
        grouped.append(enriched)
    return grouped


def split_grouped_cases(
    cases: list[dict[str, Any]],
    split_config: SplitConfig,
) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        group = case.get("split_group")
        if not isinstance(group, str) or not group:
            raise ValueError(f"Case {case.get('case_id')} is missing split_group.")
        groups[group].append(case)
    if len(groups) < 3:
        raise ValueError("Need at least three split groups to create train/valid/test splits.")

    split_names = ("train", "valid", "test")
    targets = {
        "train": len(cases) * split_config.train_fraction,
        "valid": len(cases) * split_config.valid_fraction,
        "test": len(cases) * (1 - split_config.train_fraction - split_config.valid_fraction),
    }
    ordered_groups = sorted(
        groups,
        key=lambda group: _seeded_key(split_config.seed, group),
    )
    output = {name: [] for name in split_names}
    for index, group in enumerate(ordered_groups):
        remaining = len(ordered_groups) - index
        empty = [name for name in split_names if not output[name]]
        if remaining == len(empty):
            chosen = empty[0]
        else:
            chosen = max(
                split_names,
                key=lambda name: (targets[name] - len(output[name]), -split_names.index(name)),
            )
        output[chosen].extend(sorted(groups[group], key=lambda case: case["case_id"]))
    return output


def _concept_tags(case: dict[str, Any]) -> set[str]:
    tags: set[str] = set()
    for raw_tag in case.get("tags", []):
        tag = str(raw_tag).lower()
        if tag in _META_TAGS or ":" in tag or re.fullmatch(r"\d+s", tag):
            continue
        tags.add(tag)
    return tags


def _prompt_tokens(prompt: object) -> set[str]:
    words = re.findall(r"[a-z0-9]+", str(prompt).lower())
    return {word for word in words if word not in _PROMPT_STOPWORDS and not word.isdigit()}


def _repo_provenance(case: dict[str, Any]) -> str:
    tags = set(case.get("tags", []))
    if not ({"repo-import", "source:repo"} & tags):
        return ""
    return str(case.get("source_url") or case.get("source_repo_path") or "")


def _similar(left: set[str], right: set[str], *, minimum_size: int, threshold: float) -> bool:
    if min(len(left), len(right)) < minimum_size:
        return False
    return len(left & right) / len(left | right) >= threshold


def _seeded_key(seed: int, group: str) -> str:
    return hashlib.sha256(f"{seed}:{group}".encode()).hexdigest()
