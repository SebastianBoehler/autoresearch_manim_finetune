from __future__ import annotations

import argparse
import platform
from pathlib import Path

import manim

from mac_pipeline.api_surface import snapshot_public_api
from mac_pipeline.utils import write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Snapshot the installed public Manim API.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    snapshot = snapshot_public_api(
        manim,
        python_version=platform.python_version(),
        expected_version=args.version,
    )
    write_json(args.output, snapshot)
    print(f"Wrote {len(snapshot['public_symbols'])} symbols to {args.output}")


if __name__ == "__main__":
    main()
