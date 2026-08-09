from __future__ import annotations

import copy
import unittest

from mac_pipeline.curation import apply_curation, records_digest


class CurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = [
            {
                "case_id": "keep",
                "prompt": "Create an axes example.",
                "completion": "from manim import *\nclass Keep(Scene):\n    pass\n",
                "tags": ["math"],
            },
            {
                "case_id": "fix",
                "prompt": "Create a broken example.",
                "completion": "from manim import *\nclass Fix(Scene):\n    pass\n",
                "tags": ["math"],
            },
        ]
        self.manifest = {
            "schema_version": 1,
            "dataset_version": "manim-curated-v1",
            "source_sha256": records_digest(self.records),
            "expected_case_count": 2,
            "target_runtime": {
                "manim_version": "0.20.1",
                "python_version": "3.13",
                "renderer": "cairo",
            },
            "render_verification": {
                "manim_version": "0.20.1",
                "renderer": "cairo",
                "quality": "low",
                "successful_case_ids": ["keep"],
            },
            "decisions": [
                {"case_id": "keep", "decision": "accept", "reason": "reviewed"},
                {"case_id": "fix", "decision": "rewrite", "reason": "render failure"},
            ],
        }

    def test_applies_explicit_decisions_and_enriches_only_accepted_rows(self) -> None:
        result = apply_curation(self.records, self.manifest, public_symbols={"Scene"})

        self.assertEqual([row["case_id"] for row in result.accepted], ["keep"])
        self.assertEqual([row["case_id"] for row in result.rewrite], ["fix"])
        self.assertEqual(result.accepted[0]["manim_version"], "0.20.1")
        self.assertTrue(result.accepted[0]["render_verified"])
        self.assertEqual(result.accepted[0]["render_verified_version"], "0.20.1")
        self.assertEqual(result.rewrite[0]["curation_reason"], "render failure")

    def test_rejects_accept_decision_without_exact_render_evidence(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["render_verification"]["successful_case_ids"] = []

        with self.assertRaisesRegex(ValueError, "accepted cases lack render evidence.*keep"):
            apply_curation(self.records, manifest, public_symbols={"Scene"})

    def test_rejects_render_evidence_from_another_runtime(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["render_verification"]["manim_version"] = "0.19.0"

        with self.assertRaisesRegex(ValueError, "render verification runtime"):
            apply_curation(self.records, manifest, public_symbols={"Scene"})

    def test_rejects_manifest_that_does_not_cover_every_source_row(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["decisions"].pop()

        with self.assertRaisesRegex(ValueError, "missing decisions.*fix"):
            apply_curation(self.records, manifest, public_symbols={"Scene"})

    def test_rejects_changed_source_digest(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["source_sha256"] = "0" * 64

        with self.assertRaisesRegex(ValueError, "source_sha256"):
            apply_curation(self.records, manifest, public_symbols={"Scene"})


if __name__ == "__main__":
    unittest.main()
