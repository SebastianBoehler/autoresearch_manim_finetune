from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mac_pipeline.weco_support import (  # noqa: E402
    DEFAULT_WECO_METRICS,
    WecoSupportError,
    collect_numeric_metrics,
    default_observe_sources,
    dedupe_paths,
    load_eval_summary,
    parse_metric_assignments,
    run_weco_cli,
)


def _add_source_args(command: list[str], sources: list[Path]) -> None:
    if not sources:
        return
    if len(sources) == 1:
        command.extend(["--source", str(sources[0])])
        return
    command.extend(["--sources", *[str(source) for source in sources]])


def _resolve_sources(args: argparse.Namespace) -> list[Path]:
    sources: list[Path] = []
    if getattr(args, "config", None) and not args.no_default_sources:
        sources.extend(default_observe_sources(args.config))
    raw_sources = [Path(path).resolve() for path in (args.source or [])]
    return dedupe_paths([*sources, *raw_sources])


def _print_or_run(command: list[str], dry_run: bool) -> None:
    if dry_run:
        print(shlex.join(["weco", *command]))
        return
    output = run_weco_cli(command)
    if output:
        print(output)


def cmd_init(args: argparse.Namespace) -> None:
    sources = _resolve_sources(args)
    command = ["observe", "init", "--metric", args.metric, "--goal", args.goal]
    if args.name:
        command.extend(["--name", args.name])
    if args.instructions:
        command.extend(["--additional-instructions", args.instructions])
    _add_source_args(command, sources)
    _print_or_run(command, args.dry_run)


def cmd_log(args: argparse.Namespace) -> None:
    metrics: dict[str, float] = {}
    if args.eval:
        _, _, summary = load_eval_summary(Path(args.eval).resolve())
        metrics.update(collect_numeric_metrics(summary, DEFAULT_WECO_METRICS))
    metrics.update(parse_metric_assignments(args.metric))
    if not metrics and args.status == "completed":
        raise WecoSupportError(
            "Provide --eval or one or more --metric name=value entries for completed steps."
        )

    command = [
        "observe",
        "log",
        "--run-id",
        args.run_id,
        "--step",
        str(args.step),
        "--status",
        args.status,
    ]
    if args.description:
        command.extend(["--description", args.description])
    if metrics:
        command.extend(["--metrics", json.dumps(metrics, separators=(",", ":"))])
    if args.parent_step is not None:
        command.extend(["--parent-step", str(args.parent_step)])
    _add_source_args(command, _resolve_sources(args))
    _print_or_run(command, args.dry_run)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Initialize and log Weco Observe runs from mac_pipeline outputs."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--config", required=True, help="Experiment config used by the run.")
    init.add_argument("--name", help="Run name shown in Weco.")
    init.add_argument(
        "--metric",
        default="mean_case_score",
        help="Primary Weco metric. Defaults to the repo's generation quality score.",
    )
    init.add_argument(
        "--goal",
        choices=["max", "maximize", "min", "minimize"],
        default="max",
        help="Optimization direction for the primary metric.",
    )
    init.add_argument(
        "--instructions",
        help="Optional run-level instructions shown in Weco.",
    )
    init.add_argument(
        "--source",
        action="append",
        help="Additional source file to snapshot. Repeat as needed.",
    )
    init.add_argument(
        "--no-default-sources",
        action="store_true",
        help="Track only explicitly provided --source paths.",
    )
    init.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the assembled Weco command instead of executing it.",
    )
    init.set_defaults(func=cmd_init)

    log = subparsers.add_parser("log")
    log.add_argument("--run-id", required=True)
    log.add_argument("--step", type=int, required=True)
    log.add_argument(
        "--status",
        choices=["completed", "failed"],
        default="completed",
    )
    log.add_argument("--description")
    log.add_argument(
        "--eval",
        help="Eval JSON to extract metrics from.",
    )
    log.add_argument(
        "--metric",
        action="append",
        default=[],
        help="Extra metrics in name=value form. Repeat as needed.",
    )
    log.add_argument("--parent-step", type=int)
    log.add_argument(
        "--config",
        help="Experiment config used to infer default tracked source files.",
    )
    log.add_argument(
        "--source",
        action="append",
        help="Additional source file to snapshot for this step.",
    )
    log.add_argument(
        "--no-default-sources",
        action="store_true",
        help="Do not include repo-default tracked files from --config.",
    )
    log.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the assembled Weco command instead of executing it.",
    )
    log.set_defaults(func=cmd_log)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except WecoSupportError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
