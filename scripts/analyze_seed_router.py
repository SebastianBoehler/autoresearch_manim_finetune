from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mac_pipeline.eval_summary import summarize_case_results
from mac_pipeline.utils import load_records, write_json

STOPWORDS = {
    "about",
    "create",
    "explain",
    "explains",
    "include",
    "includes",
    "into",
    "keep",
    "make",
    "manim",
    "scene",
    "short",
    "show",
    "shows",
    "that",
    "then",
    "uses",
    "using",
    "with",
    "without",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-feature-cases", type=int, default=2)
    parser.add_argument(
        "--feature-source",
        choices=["tags", "tags-and-keywords"],
        default="tags",
    )
    args = parser.parse_args()

    records = load_records(ROOT / args.dataset)
    baseline = _cases_by_id(ROOT / args.baseline)
    candidate = _cases_by_id(ROOT / args.candidate)
    _validate(records, baseline, candidate)

    route = _greedy_route(
        records=records,
        baseline=baseline,
        candidate=candidate,
        min_feature_cases=args.min_feature_cases,
        feature_source=args.feature_source,
    )
    loo = _leave_one_out(records, baseline, candidate, args)
    oracle_candidate_ids = _oracle_candidate_ids(records, baseline, candidate)
    payload = {
        "dataset": args.dataset,
        "baseline_artifact": args.baseline,
        "candidate_artifact": args.candidate,
        "baseline_summary": summarize_case_results(
            [baseline[record["case_id"]] for record in records]
        ),
        "candidate_summary": summarize_case_results(
            [candidate[record["case_id"]] for record in records]
        ),
        "routed_summary": _summary_for(records, baseline, candidate, route["case_ids"]),
        "oracle_summary": _summary_for(records, baseline, candidate, oracle_candidate_ids),
        "leave_one_out_summary": loo["summary"],
        "selected_features": route["features"],
        "feature_source": args.feature_source,
        "routed_candidate_case_ids": sorted(route["case_ids"]),
        "oracle_candidate_case_ids": sorted(oracle_candidate_ids),
        "cases": _case_rows(records, baseline, candidate, route["case_ids"]),
        "leave_one_out_cases": loo["cases"],
        "notes": [
            "Offline analysis only: no new generation, no code repair, no re-render.",
            "Route objective is production rate, then mean score, render rate, syntax rate.",
            "Leave-one-out is a small-data overfit check, not a replacement for fresh generation.",
        ],
    }
    write_json(ROOT / args.output, payload)
    print(json.dumps(payload["routed_summary"], indent=2))


def _cases_by_id(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text())
    return {case["case_id"]: case for case in payload["cases"]}


def _validate(
    records: list[dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
) -> None:
    missing = [
        record["case_id"]
        for record in records
        if record["case_id"] not in baseline or record["case_id"] not in candidate
    ]
    if missing:
        raise ValueError(f"Artifacts missing dataset cases: {', '.join(missing)}")


def _greedy_route(
    records: list[dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
    min_feature_cases: int,
    feature_source: str,
) -> dict[str, Any]:
    features = _feature_index(records, min_feature_cases, feature_source)
    chosen_features: list[str] = []
    chosen_ids: set[str] = set()
    best_objective = _objective(_select_cases(records, baseline, candidate, chosen_ids))

    while True:
        best_step: tuple[tuple[float, ...], str, set[str]] | None = None
        for feature, feature_ids in features.items():
            if feature in chosen_features:
                continue
            next_ids = chosen_ids | feature_ids
            objective = _objective(_select_cases(records, baseline, candidate, next_ids))
            if objective <= best_objective:
                continue
            if best_step is None or (objective, feature) > (best_step[0], best_step[1]):
                best_step = (objective, feature, next_ids)
        if best_step is None:
            break
        best_objective, feature, chosen_ids = best_step
        chosen_features.append(feature)

    return {"features": chosen_features, "case_ids": chosen_ids}


def _feature_index(
    records: list[dict[str, Any]],
    min_feature_cases: int,
    feature_source: str,
) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for record in records:
        case_id = record["case_id"]
        for feature in _record_features(record, feature_source):
            index.setdefault(feature, set()).add(case_id)
    return {
        feature: case_ids
        for feature, case_ids in index.items()
        if len(case_ids) >= min_feature_cases
    }


def _record_features(record: dict[str, Any], feature_source: str) -> set[str]:
    features = {f"tag:{tag.lower()}" for tag in record.get("tags", [])}
    if feature_source == "tags":
        return features
    words = re.findall(r"[a-z][a-z0-9_]{3,}", record["prompt"].lower())
    features.update(f"kw:{word}" for word in words if word not in STOPWORDS)
    return features


def _leave_one_out(
    records: list[dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    selected_cases: list[dict[str, Any]] = []
    for held in records:
        train = [record for record in records if record["case_id"] != held["case_id"]]
        route = _greedy_route(
            records=train,
            baseline=baseline,
            candidate=candidate,
            min_feature_cases=args.min_feature_cases,
            feature_source=args.feature_source,
        )
        matched = sorted(
            set(route["features"]) & _record_features(held, args.feature_source)
        )
        case_id = held["case_id"]
        choice = "candidate" if matched else "baseline"
        selected_cases.append(candidate[case_id] if matched else baseline[case_id])
        rows.append(
            {
                "case_id": case_id,
                "route_choice": choice,
                "matched_features": matched,
            }
        )
    return {"summary": summarize_case_results(selected_cases), "cases": rows}


def _objective(cases: list[dict[str, Any]]) -> tuple[float, ...]:
    summary = summarize_case_results(cases)
    return (
        summary["production_success_rate"] or 0.0,
        summary["mean_case_score"],
        summary["render_success_rate"] or 0.0,
        summary["syntax_success_rate"],
    )


def _select_cases(
    records: list[dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
    candidate_ids: set[str],
) -> list[dict[str, Any]]:
    return [
        candidate[record["case_id"]]
        if record["case_id"] in candidate_ids
        else baseline[record["case_id"]]
        for record in records
    ]


def _summary_for(
    records: list[dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
    candidate_ids: set[str],
) -> dict[str, Any]:
    return summarize_case_results(_select_cases(records, baseline, candidate, candidate_ids))


def _oracle_candidate_ids(
    records: list[dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
) -> set[str]:
    return {
        record["case_id"]
        for record in records
        if _case_objective(candidate[record["case_id"]])
        > _case_objective(baseline[record["case_id"]])
    }


def _case_objective(case: dict[str, Any]) -> tuple[bool, float, bool, bool]:
    return (
        _production_ready(case),
        case["weighted_score"],
        case["render_ok"] is True,
        bool(case["syntax_ok"]),
    )


def _production_ready(case: dict[str, Any]) -> bool:
    return bool(
        case["syntax_ok"]
        and case["render_ok"] is True
        and case.get("generation_quality_ok", False)
    )


def _case_rows(
    records: list[dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
    candidate_ids: set[str],
) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        case_id = record["case_id"]
        rows.append(
            {
                "case_id": case_id,
                "route_choice": "candidate" if case_id in candidate_ids else "baseline",
                "baseline_production_ready": _production_ready(baseline[case_id]),
                "candidate_production_ready": _production_ready(candidate[case_id]),
                "baseline_score": baseline[case_id]["weighted_score"],
                "candidate_score": candidate[case_id]["weighted_score"],
                "tags": record.get("tags", []),
            }
        )
    return rows


if __name__ == "__main__":
    main()
