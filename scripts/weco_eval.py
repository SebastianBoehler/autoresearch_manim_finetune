from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mac_pipeline.weco_support import (  # noqa: E402
    DEFAULT_WECO_METRICS,
    WecoSupportError,
    collect_numeric_metrics,
    format_metric_lines,
    load_eval_summary,
    resolve_eval_output_path,
)


def _run_pipeline_eval(args: argparse.Namespace) -> Path:
    if args.mode == "run" and args.output:
        raise WecoSupportError("--output is only supported with --mode eval.")
    if args.mode == "run" and args.base_only:
        raise WecoSupportError("--base-only only works with --mode eval.")

    command = [
        sys.executable,
        "-m",
        "mac_pipeline.cli",
        args.mode,
        "--config",
        str(Path(args.config).resolve()),
    ]
    if args.mode == "eval":
        if args.base_only:
            command.append("--base-only")
        if args.output:
            command.extend(["--output", str(Path(args.output).resolve())])

    subprocess.run(command, cwd=REPO_ROOT, check=True)
    return resolve_eval_output_path(args.config, args.output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print mac_pipeline eval metrics in a Weco-friendly format."
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--eval", help="Existing eval JSON to read.")
    source_group.add_argument(
        "--config",
        help="Experiment config to evaluate before printing metrics.",
    )
    parser.add_argument(
        "--mode",
        choices=["eval", "run"],
        default="eval",
        help="Pipeline command to run when --config is provided.",
    )
    parser.add_argument(
        "--base-only",
        action="store_true",
        help="Pass through to `mac_pipeline.cli eval --base-only`.",
    )
    parser.add_argument(
        "--output",
        help="Optional eval JSON path when running `mac_pipeline.cli eval`.",
    )
    parser.add_argument(
        "--metric",
        action="append",
        help="Metric to print. Repeat to limit output to specific metrics.",
    )
    parser.add_argument(
        "--require-metric",
        help="Exit with an error if this metric is not available.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        eval_path = Path(args.eval).resolve() if args.eval else _run_pipeline_eval(args)
        _, _, summary = load_eval_summary(eval_path)
        selected_metrics = args.metric or list(DEFAULT_WECO_METRICS)
        metrics = collect_numeric_metrics(summary, selected_metrics)
        if args.require_metric and args.require_metric not in metrics:
            raise WecoSupportError(
                f"Required metric {args.require_metric!r} is missing from {eval_path}."
            )
        lines = format_metric_lines(metrics, selected_metrics)
        if not lines:
            raise WecoSupportError(f"No numeric metrics found in {eval_path}.")
    except (WecoSupportError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    for line in lines:
        print(line)


if __name__ == "__main__":
    main()
