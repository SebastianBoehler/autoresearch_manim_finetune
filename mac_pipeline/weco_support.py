from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable

from mac_pipeline.types import ExperimentConfig
from mac_pipeline.utils import resolve_path

DEFAULT_WECO_METRICS = (
    "mean_case_score",
    "render_success_rate",
    "syntax_success_rate",
    "test_loss",
    "test_perplexity",
    "num_cases",
)

DEFAULT_OBSERVE_SOURCE_PATHS = (
    "mac_pipeline/eval.py",
    "mac_pipeline/mlx.py",
    "mac_pipeline/compare.py",
)


class WecoSupportError(RuntimeError):
    pass


def load_experiment_context(
    config_path: str | Path,
) -> tuple[ExperimentConfig, Path, Path]:
    resolved = Path(config_path).resolve()
    repo_root = resolved.parent.parent
    return ExperimentConfig.load(resolved), resolved, repo_root


def default_observe_sources(config_path: str | Path) -> list[Path]:
    _, resolved_config, repo_root = load_experiment_context(config_path)
    sources = [resolved_config]
    for relative_path in DEFAULT_OBSERVE_SOURCE_PATHS:
        source_path = (repo_root / relative_path).resolve()
        if source_path.exists():
            sources.append(source_path)
    return dedupe_paths(sources)


def dedupe_paths(paths: Iterable[str | Path]) -> list[Path]:
    seen: set[Path] = set()
    ordered: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path).resolve()
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return ordered


def resolve_eval_output_path(
    config_path: str | Path,
    output_path: str | Path | None = None,
) -> Path:
    config, _, repo_root = load_experiment_context(config_path)
    if output_path is not None:
        return Path(output_path).resolve()
    return resolve_path(repo_root, config.eval_output_path).resolve()


def load_eval_summary(eval_path: str | Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    resolved = Path(eval_path).resolve()
    payload = json.loads(resolved.read_text())
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise WecoSupportError(f"Missing summary object in eval payload: {resolved}")
    return resolved, payload, summary


def collect_numeric_metrics(
    summary: dict[str, Any],
    metric_names: Iterable[str] | None = None,
) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for name in metric_names or DEFAULT_WECO_METRICS:
        value = summary.get(name)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            metrics[name] = float(value)
    return metrics


def parse_metric_assignments(raw_metrics: Iterable[str] | None) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for raw_metric in raw_metrics or []:
        if "=" not in raw_metric:
            raise WecoSupportError(
                f"Invalid metric assignment {raw_metric!r}. Use name=value."
            )
        name, raw_value = raw_metric.split("=", 1)
        metric_name = name.strip()
        if not metric_name:
            raise WecoSupportError("Metric name cannot be empty.")
        try:
            metrics[metric_name] = float(raw_value.strip())
        except ValueError as exc:
            raise WecoSupportError(
                f"Metric {metric_name!r} must be numeric, got {raw_value!r}."
            ) from exc
    return metrics


def format_metric_lines(
    metrics: dict[str, float],
    metric_names: Iterable[str] | None = None,
) -> list[str]:
    ordered_names = list(metric_names or metrics.keys())
    lines: list[str] = []
    for name in ordered_names:
        if name not in metrics:
            continue
        value = metrics[name]
        if float(value).is_integer():
            lines.append(f"{name}: {int(value)}")
        else:
            lines.append(f"{name}: {value:.6f}")
    return lines


def require_weco_cli() -> str:
    executable = shutil.which("weco")
    if executable is None:
        raise WecoSupportError(
            "Weco CLI not found. Install it first, for example with `pipx install weco`."
        )
    return executable


def run_weco_cli(command_args: list[str]) -> str:
    executable = require_weco_cli()
    result = subprocess.run(
        [executable, *command_args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise WecoSupportError(message or "Weco CLI command failed.")
    return result.stdout.strip()
