from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mac_pipeline.curated_export import export_curated_dataset
from mac_pipeline.curation import records_digest
from mac_pipeline.types import SplitConfig


class CuratedExportTests(unittest.TestCase):
    def test_export_writes_reconciled_grouped_and_versioned_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            records = [
                {
                    "case_id": f"case_{index}",
                    "prompt": f"Explain concept {index} with a diagram.",
                    "completion": "from manim import *\nclass Demo(Scene):\n    pass\n",
                    "tags": ["docs"] if index == 0 else [f"topic-{index}"],
                    "source_domain": "math",
                }
                for index in range(7)
            ]
            source_path = root / "source.jsonl"
            _write_jsonl(source_path, records)
            decisions = [
                {"case_id": row["case_id"], "decision": "accept", "reason": "reviewed"}
                for row in records[:6]
            ] + [
                {"case_id": "case_6", "decision": "rewrite", "reason": "broken"}
            ]
            manifest = {
                "schema_version": 1,
                "dataset_version": "test-v1",
                "source_sha256": records_digest(records),
                "expected_case_count": 7,
                "target_runtime": {
                    "manim_version": "0.20.1",
                    "python_version": "3.13",
                    "renderer": "cairo",
                },
                "render_verification": {
                    "manim_version": "0.20.1",
                    "renderer": "cairo",
                    "quality": "low",
                    "successful_case_ids": [row["case_id"] for row in records[:6]],
                },
                "decisions": decisions,
            }
            manifest_path = root / "curation.json"
            manifest_path.write_text(json.dumps(manifest))
            api_surface_path = root / "api.json"
            api_surface_path.write_text(
                json.dumps({"manim_version": "0.20.1", "public_symbols": ["Scene"]})
            )

            summary = export_curated_dataset(
                source_path=source_path,
                curation_manifest_path=manifest_path,
                api_surface_path=api_surface_path,
                output_dir=root / "output",
                split_config=SplitConfig(train_fraction=0.5, valid_fraction=0.25, seed=3),
            )

            self.assertEqual(summary["counts"], {"source": 7, "accepted": 6, "quarantine": 0, "rewrite": 1})
            accepted = _read_jsonl(root / "output" / "cases.jsonl")
            self.assertTrue(all(row["manim_version"] == "0.20.1" for row in accepted))
            api_rows = _read_jsonl(root / "output" / "api_reference.jsonl")
            self.assertEqual([row["case_id"] for row in api_rows], ["case_0"])
            split_groups: dict[str, set[str]] = {}
            for name in ("train", "valid", "test"):
                for row in _read_jsonl(root / "output" / f"{name}.jsonl"):
                    split_groups.setdefault(row["split_group"], set()).add(name)
            self.assertTrue(all(len(splits) == 1 for splits in split_groups.values()))
            self.assertTrue((root / "output" / "api_coverage.json").exists())


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("".join(json.dumps(record) + "\n" for record in records))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


if __name__ == "__main__":
    unittest.main()
