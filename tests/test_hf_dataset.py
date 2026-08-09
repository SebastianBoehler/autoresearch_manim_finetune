from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

from mac_pipeline.hf_dataset import (
    _copy_preview_items,
    _validate_dataset_card_asset_paths,
    build_dataset_card,
)
from mac_pipeline.hf_frozen_splits import load_frozen_chat_splits


class HFDatasetPreviewTests(unittest.TestCase):
    def test_frozen_chat_splits_preserve_membership(self) -> None:
        cases = [{"case_id": name} for name in ("a", "b", "c")]
        with tempfile.TemporaryDirectory() as tmp_dir:
            split_dir = Path(tmp_dir)
            for name, case_id in (("train", "a"), ("valid", "b"), ("test", "c")):
                (split_dir / f"{name}.jsonl").write_text(
                    json.dumps({"case_id": case_id, "messages": []}) + "\n"
                )

            splits = load_frozen_chat_splits(cases, split_dir)

        self.assertEqual([row["case_id"] for row in splits["train"]], ["a"])
        self.assertEqual([row["case_id"] for row in splits["valid"]], ["b"])
        self.assertEqual([row["case_id"] for row in splits["test"]], ["c"])

    def test_frozen_chat_splits_reject_leakage(self) -> None:
        cases = [{"case_id": name} for name in ("a", "b", "c")]
        with tempfile.TemporaryDirectory() as tmp_dir:
            split_dir = Path(tmp_dir)
            (split_dir / "train.jsonl").write_text(
                json.dumps({"case_id": "a", "messages": []}) + "\n"
            )
            (split_dir / "valid.jsonl").write_text(
                json.dumps({"case_id": "a", "messages": []}) + "\n"
            )
            (split_dir / "test.jsonl").write_text(
                json.dumps({"case_id": "c", "messages": []}) + "\n"
            )

            with self.assertRaisesRegex(ValueError, "appears in both"):
                load_frozen_chat_splits(cases, split_dir)

    def test_preview_items_keep_unsuffixed_names_when_stale_assets_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            source_dir = tmp / "sources"
            source_dir.mkdir()
            preview = source_dir / "preview.png"
            preview.write_bytes(b"png")

            output_dir = tmp / "export"
            asset_dir = output_dir / "assets"
            asset_dir.mkdir(parents=True)
            (asset_dir / "preview-1.png").write_bytes(b"stale")

            metadata = {"preview_items": []}
            _copy_preview_items(
                output_dir,
                metadata,
                [{"path": str(preview), "caption": "Preview"}],
            )

            self.assertEqual(
                metadata["preview_items"],
                [{"path": "assets/preview.png", "caption": "Preview"}],
            )
            self.assertEqual((asset_dir / "preview.png").read_bytes(), b"png")

    def test_preview_items_suffix_only_current_duplicate_basenames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            left = tmp / "left"
            right = tmp / "right"
            left.mkdir()
            right.mkdir()
            first = left / "preview.png"
            second = right / "preview.png"
            first.write_bytes(b"first")
            second.write_bytes(b"second")

            output_dir = tmp / "export"
            metadata = {"preview_items": []}
            _copy_preview_items(
                output_dir,
                metadata,
                [
                    {"path": str(first), "caption": "First"},
                    {"path": str(second), "caption": "Second"},
                ],
            )

            self.assertEqual(
                metadata["preview_items"],
                [
                    {"path": "assets/preview.png", "caption": "First"},
                    {"path": "assets/preview-2.png", "caption": "Second"},
                ],
            )
            self.assertEqual((output_dir / "assets" / "preview.png").read_bytes(), b"first")
            self.assertEqual((output_dir / "assets" / "preview-2.png").read_bytes(), b"second")

    def test_dataset_card_asset_validation_fails_for_missing_local_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            card = "![Broken](assets/missing.png)\n"

            with self.assertRaisesRegex(FileNotFoundError, "assets/missing.png"):
                _validate_dataset_card_asset_paths(card, output_dir)

    def test_build_dataset_card_references_existing_preview_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            (output_dir / "assets").mkdir()
            (output_dir / "assets" / "preview.png").write_bytes(b"png")
            metadata = {
                "counts": {"cases": 3, "chat": {"train": 1, "validation": 1, "test": 1}},
                "repo_id": "owner/demo",
                "pretty_name": "Demo",
                "license": "mit",
                "license_name": None,
                "license_link": None,
                "languages": [],
                "task_categories": [],
                "size_categories": [],
                "tags": [],
                "preview_items": [{"path": "assets/preview.png", "caption": "Preview"}],
                "preview_image": None,
                "preview_caption": None,
                "source_dataset": "demo.jsonl",
                "split_seed": 42,
                "dataset_filter": {"include_tags": [], "exclude_tags": []},
            }

            card = build_dataset_card(metadata, output_dir)
            _validate_dataset_card_asset_paths(card, output_dir)


if __name__ == "__main__":
    unittest.main()
