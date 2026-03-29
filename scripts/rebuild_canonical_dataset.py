import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mac_pipeline.canonical_dataset import rebuild_canonical_dataset


def main() -> None:
    output_path = rebuild_canonical_dataset(REPO_ROOT)
    line_count = sum(1 for line in output_path.read_text().splitlines() if line.strip())
    print(f"Wrote {line_count} cases to {output_path}")


if __name__ == "__main__":
    main()
