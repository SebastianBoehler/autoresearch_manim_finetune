from pathlib import Path

from mac_pipeline.canonical_dataset import rebuild_canonical_dataset


REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    output_path = rebuild_canonical_dataset(REPO_ROOT)
    line_count = sum(1 for line in output_path.read_text().splitlines() if line.strip())
    print(f"Wrote {line_count} cases to {output_path}")


if __name__ == "__main__":
    main()
