from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mac_pipeline.ablation_variants import write_ablation_variants


class AblationVariantTests(unittest.TestCase):
    def test_variants_filter_training_only_and_share_frozen_holdouts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            rows = [
                {"case_id": "p", "corpus_roles": ["pedagogical"]},
                {"case_id": "a", "corpus_roles": ["api_reference"]},
                {"case_id": "c", "corpus_roles": ["pedagogical", "composite"]},
            ]
            split_map = {
                "train": rows,
                "valid": [{"case_id": "v", "corpus_roles": ["pedagogical"]}],
                "test": [{"case_id": "t", "corpus_roles": ["api_reference"]}],
            }

            manifest = write_ablation_variants(split_map, Path(tmp_dir))

            self.assertEqual(
                _ids(Path(tmp_dir) / "pedagogical_only" / "train.jsonl"),
                ["c", "p"],
            )
            self.assertEqual(
                _ids(Path(tmp_dir) / "api_reference_only" / "train.jsonl"),
                ["a"],
            )
            self.assertEqual(
                _ids(Path(tmp_dir) / "without_composite" / "train.jsonl"),
                ["a", "p"],
            )
            for variant in manifest["variants"]:
                self.assertEqual(_ids(Path(tmp_dir) / variant / "valid.jsonl"), ["v"])
                self.assertEqual(_ids(Path(tmp_dir) / variant / "test.jsonl"), ["t"])


def _ids(path: Path) -> list[str]:
    return sorted(json.loads(line)["case_id"] for line in path.read_text().splitlines())


if __name__ == "__main__":
    unittest.main()
