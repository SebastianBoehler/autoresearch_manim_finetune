from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mac_pipeline.plotting import plot_eval_comparison


def main() -> int:
    baseline_eval = REPO_ROOT / "artifacts/evals/m4-max-qwen25coder-3b-base-v2.json"
    finetuned_eval = REPO_ROOT / "artifacts/evals/m4-max-qwen25coder-3b.json"
    output_path = REPO_ROOT / "docs/figures/base-vs-finetuned.png"

    if not baseline_eval.exists() or not finetuned_eval.exists():
        print("Skipping plot refresh: missing eval artifacts.")
        return 0

    plot_eval_comparison(
        baseline_eval_path=baseline_eval,
        finetuned_eval_path=finetuned_eval,
        output_path=output_path,
    )
    print(f"Updated {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
