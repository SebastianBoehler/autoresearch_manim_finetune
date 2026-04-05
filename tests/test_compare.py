from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mac_pipeline.compare import compare_runs


def _write_eval(path: Path, *, loss: float, render: float, score: float) -> None:
    payload = {
        "summary": {
            "test_loss": loss,
            "render_success_rate": render,
            "mean_case_score": score,
        }
    }
    path.write_text(json.dumps(payload))


class CompareRunsTests(unittest.TestCase):
    def test_unacceptable_render_regression_blocks_candidate_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            baseline_path = tmp / "baseline.json"
            candidate_path = tmp / "candidate.json"
            _write_eval(baseline_path, loss=0.70, render=0.50, score=0.45)
            _write_eval(candidate_path, loss=0.52, render=0.35, score=0.68)

            result = compare_runs(
                baseline_path=baseline_path,
                candidate_path=candidate_path,
                min_loss_delta=0.01,
                tie_loss_delta=0.003,
                allowed_render_regression=0.05,
            )

        self.assertEqual(result["decision"], "baseline")
        self.assertIn(
            "candidate regressed on render_success_rate beyond the allowed threshold",
            result["rationale"],
        )

    def test_candidate_can_win_when_render_regression_stays_within_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            baseline_path = tmp / "baseline.json"
            candidate_path = tmp / "candidate.json"
            _write_eval(baseline_path, loss=0.70, render=0.50, score=0.45)
            _write_eval(candidate_path, loss=0.52, render=0.47, score=0.68)

            result = compare_runs(
                baseline_path=baseline_path,
                candidate_path=candidate_path,
                min_loss_delta=0.01,
                tie_loss_delta=0.003,
                allowed_render_regression=0.05,
            )

        self.assertEqual(result["decision"], "candidate")
        self.assertIn(
            "candidate improves held-out loss without unacceptable render regression",
            result["rationale"],
        )


if __name__ == "__main__":
    unittest.main()
