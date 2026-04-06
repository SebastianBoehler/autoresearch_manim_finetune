from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mac_pipeline.benchmark_report import build_benchmark_report


def _write_summary(path: Path, *, score: float, render: float, syntax: float) -> None:
    payload = {
        "summary": {
            "num_cases": 21,
            "mean_case_score": score,
            "render_success_rate": render,
            "syntax_success_rate": syntax,
        }
    }
    path.write_text(json.dumps(payload))


class BenchmarkReportTests(unittest.TestCase):
    def test_build_benchmark_report_sorts_by_score_then_render_then_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            a = tmp / "a.json"
            b = tmp / "b.json"
            c = tmp / "c.json"
            _write_summary(a, score=0.70, render=0.80, syntax=0.90)
            _write_summary(b, score=0.70, render=0.85, syntax=0.85)
            _write_summary(c, score=0.65, render=0.95, syntax=1.00)

            payload = build_benchmark_report(
                [
                    {"name": "A", "category": "api", "path": str(a)},
                    {"name": "B", "category": "api", "path": str(b)},
                    {"name": "C", "category": "api", "path": str(c)},
                ],
                tmp / "report.json",
            )

        self.assertEqual([entry["name"] for entry in payload["leaderboard"]], ["B", "A", "C"])


if __name__ == "__main__":
    unittest.main()
