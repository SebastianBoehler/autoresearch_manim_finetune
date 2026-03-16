from __future__ import annotations

import argparse
from pathlib import Path

from mac_pipeline.compare import compare_runs
from mac_pipeline.dataset import build_dataset
from mac_pipeline.docs_seed import import_doc_examples, merge_case_files
from mac_pipeline.eval import evaluate_adapter
from mac_pipeline.mlx import train_adapter
from mac_pipeline.types import ExperimentConfig
from mac_pipeline.utils import append_tsv, resolve_path, write_json

RESULT_FIELDS = [
    "run_name",
    "base_model",
    "test_loss",
    "test_perplexity",
    "syntax_success_rate",
    "render_success_rate",
    "mean_case_score",
    "adapter_path",
    "eval_output_path",
]


def _load_config(config_path: Path) -> tuple[ExperimentConfig, Path]:
    resolved = config_path.resolve()
    return ExperimentConfig.load(resolved), resolved.parent.parent


def _require_path(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{description} does not exist: {path}")


def cmd_build_dataset(args: argparse.Namespace) -> None:
    config, repo_root = _load_config(Path(args.config))
    source_path = resolve_path(repo_root, args.source or config.source_dataset)
    dataset_dir = resolve_path(repo_root, config.dataset_dir)
    manifest = build_dataset(source_path, dataset_dir, config.splits)
    print(f"Built dataset at {dataset_dir}")
    print(manifest)


def cmd_import_doc_seeds(args: argparse.Namespace) -> None:
    manifest_path = Path(args.manifest).resolve()
    output_path = Path(args.output).resolve()
    cases = import_doc_examples(manifest_path, output_path)
    print(f"Imported {len(cases)} official docs examples into {output_path}")


def cmd_merge_case_files(args: argparse.Namespace) -> None:
    input_paths = [Path(path).resolve() for path in args.inputs]
    output_path = Path(args.output).resolve()
    merged = merge_case_files(input_paths, output_path)
    print(f"Merged {len(merged)} cases into {output_path}")


def cmd_train(args: argparse.Namespace) -> None:
    config, repo_root = _load_config(Path(args.config))
    dataset_dir = resolve_path(repo_root, config.dataset_dir)
    _require_path(dataset_dir / "train.jsonl", "Training split")
    _require_path(dataset_dir / "valid.jsonl", "Validation split")
    adapter_path = resolve_path(repo_root, config.adapter_path)
    log_path = adapter_path.parent / f"{adapter_path.name}.train.log"
    train_adapter(config, dataset_dir, adapter_path, log_path)
    print(f"Training complete. Adapter saved to {adapter_path}")
    print(f"Training log: {log_path}")


def _append_results(config: ExperimentConfig, repo_root: Path, payload: dict) -> None:
    summary = payload["summary"]
    append_tsv(
        resolve_path(repo_root, config.results_tsv),
        {
            "run_name": config.name,
            "base_model": config.base_model,
            "test_loss": summary.get("test_loss"),
            "test_perplexity": summary.get("test_perplexity"),
            "syntax_success_rate": summary.get("syntax_success_rate"),
            "render_success_rate": summary.get("render_success_rate"),
            "mean_case_score": summary.get("mean_case_score"),
            "adapter_path": payload["adapter_path"],
            "eval_output_path": str(resolve_path(repo_root, config.eval_output_path)),
        },
        RESULT_FIELDS,
    )


def cmd_eval(args: argparse.Namespace) -> None:
    config, repo_root = _load_config(Path(args.config))
    dataset_dir = resolve_path(repo_root, config.dataset_dir)
    _require_path(dataset_dir / "test.jsonl", "Test split")
    adapter_path = resolve_path(repo_root, config.adapter_path)
    _require_path(adapter_path, "Adapter path")
    output_path = resolve_path(repo_root, config.eval_output_path)
    payload = evaluate_adapter(config, dataset_dir, adapter_path, output_path)
    _append_results(config, repo_root, payload)
    print(f"Evaluation written to {output_path}")
    print(payload["summary"])


def cmd_run(args: argparse.Namespace) -> None:
    config, repo_root = _load_config(Path(args.config))
    source_path = resolve_path(repo_root, args.source or config.source_dataset)
    _require_path(source_path, "Source dataset")
    dataset_dir = resolve_path(repo_root, config.dataset_dir)
    adapter_path = resolve_path(repo_root, config.adapter_path)
    output_path = resolve_path(repo_root, config.eval_output_path)
    build_dataset(source_path, dataset_dir, config.splits)
    train_adapter(
        config,
        dataset_dir,
        adapter_path,
        adapter_path.parent / f"{adapter_path.name}.train.log",
    )
    payload = evaluate_adapter(config, dataset_dir, adapter_path, output_path)
    _append_results(config, repo_root, payload)
    print(f"Full run complete for {config.name}")
    print(payload["summary"])


def cmd_compare(args: argparse.Namespace) -> None:
    config, repo_root = _load_config(Path(args.config))
    result = compare_runs(
        baseline_path=resolve_path(repo_root, args.baseline),
        candidate_path=resolve_path(repo_root, args.candidate),
        min_loss_delta=config.evaluation.min_loss_delta,
        tie_loss_delta=config.evaluation.tie_loss_delta,
        allowed_render_regression=config.evaluation.allowed_render_regression,
    )
    output_path = resolve_path(repo_root, args.output)
    write_json(output_path, result)
    print(f"Comparison written to {output_path}")
    print(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MLX Manim fine-tuning pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, handler in {
        "import-doc-seeds": cmd_import_doc_seeds,
        "merge-case-files": cmd_merge_case_files,
        "build-dataset": cmd_build_dataset,
        "train": cmd_train,
        "eval": cmd_eval,
        "run": cmd_run,
    }.items():
        subparser = subparsers.add_parser(name)
        if name in {"build-dataset", "train", "eval", "run"}:
            subparser.add_argument("--config", required=True)
        if name == "import-doc-seeds":
            subparser.add_argument("--manifest", required=True)
            subparser.add_argument("--output", required=True)
        if name == "merge-case-files":
            subparser.add_argument("--inputs", nargs="+", required=True)
            subparser.add_argument("--output", required=True)
        if name in {"build-dataset", "run"}:
            subparser.add_argument("--source")
        subparser.set_defaults(func=handler)

    compare = subparsers.add_parser("compare")
    compare.add_argument("--config", required=True)
    compare.add_argument("--baseline", required=True)
    compare.add_argument("--candidate", required=True)
    compare.add_argument("--output", required=True)
    compare.set_defaults(func=cmd_compare)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
