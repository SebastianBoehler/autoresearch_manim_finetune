from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mac_pipeline.public_benchmark import build_public_benchmark_page


def main() -> None:
    payload = build_public_benchmark_page(
        report_path=REPO_ROOT / "artifacts/benchmarks/model-benchmark-report.json",
        output_path=REPO_ROOT / "docs/benchmark.md",
        public_data_path=REPO_ROOT / "docs/data/model-benchmark-public.json",
        examples_dir=REPO_ROOT / "docs/figures/benchmark_examples",
        render_cache_dir=REPO_ROOT / "artifacts/docs_benchmark_renders",
    )
    print(f"Wrote docs/benchmark.md with {len(payload['examples'])} example sections.")


if __name__ == "__main__":
    main()
