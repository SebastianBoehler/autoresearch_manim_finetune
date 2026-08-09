from __future__ import annotations

import argparse

CONFIG_COMMANDS = {
    "build-dataset",
    "train",
    "eval",
    "run",
    "benchmark",
    "latency-benchmark",
    "export-hf-dataset",
}
SOURCE_OVERRIDE_COMMANDS = {"build-dataset", "run", "export-hf-dataset"}


def configure_main_subparser(name: str, subparser: argparse.ArgumentParser) -> None:
    if name in CONFIG_COMMANDS:
        subparser.add_argument("--config", required=True)
    if name == "import-doc-seeds":
        _add_manifest_output_args(subparser)
    if name == "import-repo-examples":
        _add_manifest_output_args(subparser)
        subparser.add_argument("--metadata")
    if name == "filter-repo-candidates":
        subparser.add_argument("--input", required=True)
        subparser.add_argument("--plain-output", required=True)
        subparser.add_argument("--custom-output")
        subparser.add_argument("--summary")
    if name == "merge-case-files":
        subparser.add_argument("--inputs", nargs="+", required=True)
        subparser.add_argument("--output", required=True)
    if name == "eval":
        subparser.add_argument("--base-only", action="store_true")
        subparser.add_argument("--output")
    if name == "latency-benchmark":
        subparser.add_argument("--max-cases", type=int)
        subparser.add_argument("--max-tokens", type=int)
        subparser.add_argument("--target", action="append")
        subparser.add_argument("--warmup-cases", type=int, default=1)
        subparser.add_argument("--repetitions", type=int, default=1)
    if name in SOURCE_OVERRIDE_COMMANDS:
        _add_source_override_args(subparser)
    if name == "export-hf-dataset":
        _add_hf_export_args(subparser)
    if name == "plot-comparison":
        subparser.add_argument("--baseline", required=True)
        subparser.add_argument("--finetuned", required=True)
        subparser.add_argument("--output", required=True)
    if name == "build-review-session":
        _add_review_session_args(subparser)
    if name == "build-sample-review-session":
        _add_sample_review_session_args(subparser)
    if name == "serve-review-app":
        subparser.add_argument("--session-dir", required=True)
        subparser.add_argument("--host", default="127.0.0.1")
        subparser.add_argument("--port", type=int, default=8765)
    if name == "render-review-candidates":
        subparser.add_argument("--input", required=True)
        subparser.add_argument("--output-dir", required=True)
        subparser.add_argument("--quality", default="low")
        subparser.add_argument("--timeout-seconds", type=int, default=120)
    if name == "promote-review-candidates":
        subparser.add_argument("--input", required=True)
        subparser.add_argument("--review", required=True)
        subparser.add_argument("--promoted-output", default="data/manim_review_promoted.jsonl")
        subparser.add_argument("--promoted-tier", default="tier:silver")
        subparser.add_argument("--keep-promoted-in-input", action="store_true")
    if name == "apply-dataset-review-decisions":
        subparser.add_argument("--input", default="data/manim_dataset.jsonl")
        subparser.add_argument("--review", required=True)
        subparser.add_argument("--decision-log", default="data/manim_review_decisions.jsonl")
        subparser.add_argument("--rejected-output", default="data/manim_review_rejected.jsonl")


def configure_compare_subparser(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("--config", required=True)
    subparser.add_argument("--baseline", required=True)
    subparser.add_argument("--candidate", required=True)
    subparser.add_argument("--output", required=True)


def _add_manifest_output_args(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("--manifest", required=True)
    subparser.add_argument("--output", required=True)


def _add_source_override_args(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("--source")
    subparser.add_argument("--source-kind", choices=["local", "hf"])
    subparser.add_argument("--source-config-name")
    subparser.add_argument("--source-split")
    subparser.add_argument("--source-revision")


def _add_hf_export_args(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("--output-dir", required=True)
    subparser.add_argument("--repo-id")
    subparser.add_argument("--pretty-name")
    subparser.add_argument("--license")
    subparser.add_argument("--license-name")
    subparser.add_argument("--license-link")
    subparser.add_argument("--language", action="append")
    subparser.add_argument("--task-category", action="append")
    subparser.add_argument("--size-category", action="append")
    subparser.add_argument("--tag", action="append")
    subparser.add_argument("--preview-image")
    subparser.add_argument("--preview-caption")
    subparser.add_argument("--preview-item", action="append")
    subparser.add_argument("--frozen-splits-dir")


def _add_review_session_args(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("--left", required=True)
    subparser.add_argument("--right", required=True)
    subparser.add_argument("--output-dir", required=True)
    subparser.add_argument("--left-label")
    subparser.add_argument("--right-label")
    subparser.add_argument("--seed", type=int, default=42)
    subparser.add_argument("--limit", type=int, default=0)
    subparser.add_argument("--quality", default="low")
    subparser.add_argument("--timeout-seconds", type=int, default=120)
    subparser.add_argument("--include-failed-renders", action="store_true")


def _add_sample_review_session_args(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("--input", required=True)
    subparser.add_argument("--output-dir", required=True)
    subparser.add_argument("--start-index", type=int, default=0)
    subparser.add_argument("--limit", type=int, default=0)
    subparser.add_argument("--exclude-review", action="append")
    subparser.add_argument("--quality", default="low")
    subparser.add_argument("--timeout-seconds", type=int, default=120)
