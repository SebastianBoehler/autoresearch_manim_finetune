from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mac_pipeline.types import ExperimentConfig  # noqa: E402
from mac_pipeline.utils import ensure_parent, slugify  # noqa: E402
from mac_pipeline.weco_support import (  # noqa: E402
    DEFAULT_WECO_METRICS,
    WecoSupportError,
    collect_numeric_metrics,
    format_metric_lines,
    load_eval_summary,
)


def _load_target_module(source_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("weco_target", source_path)
    if spec is None or spec.loader is None:
        raise WecoSupportError(f"Unable to load Weco target: {source_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
            continue
        merged[key] = copy.deepcopy(value)
    return merged


def _resolve_source_dataset(source_dataset: Any) -> Any:
    if isinstance(source_dataset, str):
        return str((REPO_ROOT / source_dataset).resolve())
    if not isinstance(source_dataset, dict):
        return source_dataset
    resolved = copy.deepcopy(source_dataset)
    if resolved.get("kind", "local") == "local" and resolved.get("path"):
        resolved["path"] = str((REPO_ROOT / resolved["path"]).resolve())
    return resolved


def _materialize_runtime_config(
    source_path: Path,
    output_root: Path,
) -> tuple[Path, Path]:
    module = _load_target_module(source_path)
    base_config_value = getattr(module, "BASE_CONFIG_PATH", None)
    overrides = getattr(module, "TRIAL_OVERRIDES", None)
    if not isinstance(base_config_value, str):
        raise WecoSupportError("Weco target must define BASE_CONFIG_PATH as a string.")
    if not isinstance(overrides, dict):
        raise WecoSupportError("Weco target must define TRIAL_OVERRIDES as a dict.")

    base_config_path = (REPO_ROOT / base_config_value).resolve()
    base_payload = json.loads(base_config_path.read_text())
    runtime_payload = _deep_merge(base_payload, overrides)

    config_fingerprint = hashlib.sha1(
        json.dumps(runtime_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]
    run_slug = slugify(f"{source_path.stem}-{config_fingerprint}")
    run_root = (output_root / run_slug).resolve()
    runtime_config_path = run_root / "config.json"

    runtime_payload["name"] = f"{runtime_payload['name']}-{config_fingerprint}"
    runtime_payload["source_dataset"] = _resolve_source_dataset(
        runtime_payload.get("source_dataset")
    )
    runtime_payload["dataset_dir"] = str(run_root / "dataset")
    runtime_payload["adapter_path"] = str(run_root / "adapter")
    runtime_payload["eval_output_path"] = str(run_root / "eval.json")
    runtime_payload["results_tsv"] = str(output_root / "results.tsv")

    ensure_parent(runtime_config_path).write_text(
        json.dumps(runtime_payload, indent=2) + "\n"
    )
    ExperimentConfig.load(runtime_config_path)
    return runtime_config_path, Path(runtime_payload["eval_output_path"]).resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Materialize a Weco-tunable Manim config, run the pipeline, and print metrics."
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Editable Weco target Python file.",
    )
    parser.add_argument(
        "--output-root",
        default="artifacts/weco",
        help="Root directory for generated configs, adapters, and evals.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only materialize the runtime config and print its path.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    source_path = Path(args.source).resolve()
    output_root = Path(args.output_root).resolve()

    try:
        runtime_config_path, eval_output_path = _materialize_runtime_config(
            source_path=source_path,
            output_root=output_root,
        )
        if args.dry_run:
            print(runtime_config_path)
            return

        command = [
            sys.executable,
            "-m",
            "mac_pipeline.cli",
            "run",
            "--config",
            str(runtime_config_path),
        ]
        subprocess.run(command, cwd=REPO_ROOT, check=True)
        _, _, summary = load_eval_summary(eval_output_path)
        metrics = collect_numeric_metrics(summary, DEFAULT_WECO_METRICS)
        for line in format_metric_lines(metrics, DEFAULT_WECO_METRICS):
            print(line)
    except (WecoSupportError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
