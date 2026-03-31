from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mac_pipeline.weco_support import WecoSupportError, require_weco_cli  # noqa: E402

DEFAULT_SOURCE = REPO_ROOT / "weco_targets" / "manim_lora_trial.py"
DEFAULT_INSTRUCTIONS = REPO_ROOT / "weco_targets" / "manim_lora_trial_instructions.md"


def _validate_api_key_passthrough(passthrough: list[str]) -> None:
    index = 0
    while index < len(passthrough):
        token = passthrough[index]
        if token != "--api-key":
            index += 1
            continue
        index += 1
        found_key = False
        while index < len(passthrough) and not passthrough[index].startswith("-"):
            found_key = True
            raw_assignment = passthrough[index]
            if "=" not in raw_assignment:
                raise WecoSupportError(
                    "Invalid `--api-key` value. Use provider=KEY, for example "
                    "`--api-key openai=$OPENAI_API_KEY`."
                )
            provider, key = raw_assignment.split("=", 1)
            if not provider or not key:
                raise WecoSupportError(
                    "Empty provider key detected for `--api-key`. Either remove "
                    "`--api-key` to use Weco credits after login, or export the "
                    "environment variable first so `provider=KEY` is non-empty."
                )
            index += 1
        if not found_key:
            raise WecoSupportError(
                "`--api-key` was provided without any provider=KEY values."
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Launch a repo-native Weco optimization for Manim fine-tuning."
    )
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--steps", type=int, default=6)
    parser.add_argument("--metric", default="mean_case_score")
    parser.add_argument("--goal", default="maximize")
    parser.add_argument("--model")
    parser.add_argument("--log-dir", default=".runs")
    parser.add_argument("--save-logs", action="store_true")
    parser.add_argument("--require-review", action="store_true")
    parser.add_argument("--apply-change", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the Weco command instead of executing it.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args, passthrough = parser.parse_known_args()
    try:
        source_path = Path(args.source).resolve()
        weco_executable = require_weco_cli()
        _validate_api_key_passthrough(passthrough)

        eval_command = (
            "uv run python scripts/weco_manim_eval.py "
            f"--source {shlex.quote(str(source_path))}"
        )
        command = [
            weco_executable,
            "run",
            "--source",
            str(source_path),
            "--eval-command",
            eval_command,
            "--metric",
            args.metric,
            "--goal",
            args.goal,
            "--steps",
            str(args.steps),
            "--log-dir",
            args.log_dir,
            "--additional-instructions",
            str(DEFAULT_INSTRUCTIONS),
        ]
        if args.model:
            command.extend(["--model", args.model])
        if args.save_logs:
            command.append("--save-logs")
        if args.require_review:
            command.append("--require-review")
        if args.apply_change:
            command.append("--apply-change")
        command.extend(passthrough)

        if args.dry_run:
            print(shlex.join(command))
            return

        subprocess.run(command, cwd=REPO_ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
    except WecoSupportError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
