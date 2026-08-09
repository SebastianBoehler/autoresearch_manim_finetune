from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mac_pipeline.review.candidates import _selected_case_ids
from mac_pipeline.review.render import _find_rendered_video


class ReviewGateTests(unittest.TestCase):
    def test_promotion_requires_render_and_three_quality_scores(self) -> None:
        incomplete = [{"case_id": "demo", "decision": "promote", "confidence": 0.95}]

        with self.assertRaisesRegex(ValueError, "render_ok"):
            _selected_case_ids(incomplete)

    def test_promotion_rejects_unresolved_blocking_issues(self) -> None:
        review = [
            {
                "case_id": "demo",
                "decision": "promote",
                "confidence": 0.95,
                "render_ok": True,
                "factual_score": 5,
                "pedagogical_score": 5,
                "visual_score": 5,
                "blocking_issues": ["caption overlaps graph"],
            }
        ]

        with self.assertRaisesRegex(ValueError, "blocking_issues"):
            _selected_case_ids(review)

    def test_promotion_accepts_complete_high_quality_evidence(self) -> None:
        review = [
            {
                "case_id": "demo",
                "decision": "promote",
                "confidence": 0.9,
                "render_ok": True,
                "factual_score": 4,
                "pedagogical_score": 5,
                "visual_score": 4,
                "blocking_issues": [],
            }
        ]

        self.assertEqual(_selected_case_ids(review), ["demo"])

    def test_render_lookup_never_falls_back_to_another_scene(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            media_dir = Path(tmp_dir)
            other = media_dir / "videos" / "OtherScene.mp4"
            other.parent.mkdir()
            other.write_bytes(b"video")

            self.assertIsNone(_find_rendered_video(media_dir, "ExpectedScene"))


if __name__ == "__main__":
    unittest.main()
