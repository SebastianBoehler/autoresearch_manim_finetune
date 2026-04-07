from __future__ import annotations

import unittest

from mac_pipeline.public_benchmark import describe_case_status, render_public_benchmark_markdown


class PublicBenchmarkTests(unittest.TestCase):
    def test_describe_case_status_handles_common_paths(self) -> None:
        self.assertEqual(describe_case_status({"render_ok": True, "syntax_ok": True, "scene_name": "Scene"}), "Rendered")
        self.assertEqual(describe_case_status({"render_ok": False, "syntax_ok": True, "scene_name": "Scene"}), "Render failed")
        self.assertEqual(describe_case_status({"render_ok": None, "syntax_ok": True, "scene_name": None}), "No scene detected")
        self.assertEqual(describe_case_status({"render_ok": None, "syntax_ok": False, "scene_name": None}), "Syntax error")

    def test_render_public_benchmark_markdown_includes_sections(self) -> None:
        report = {
            "num_cases": 21,
            "leaderboard": [
                {
                    "name": "Xiaomi MiMo-V2-Pro",
                    "category": "api",
                    "summary": {
                        "mean_case_score": 0.79,
                        "render_success_rate": 0.875,
                        "syntax_success_rate": 0.81,
                    },
                },
                {
                    "name": "Qwen 2.5 Coder 3B Fine-tuned",
                    "category": "local_finetuned",
                    "summary": {
                        "mean_case_score": 0.65,
                        "render_success_rate": 0.56,
                        "syntax_success_rate": 0.76,
                    },
                },
                {
                    "name": "MiniMax M2.7",
                    "category": "api",
                    "summary": {
                        "mean_case_score": 0.66,
                        "render_success_rate": 0.53,
                        "syntax_success_rate": 0.76,
                    },
                },
            ],
        }
        examples = [
            {
                "title": "Transform Matching Shapes",
                "summary": "All selected models rendered it.",
                "prompt": "Create a morph scene.",
                "rows": [
                    {
                        "name": "Xiaomi MiMo-V2-Pro",
                        "status": "Rendered",
                        "score": "1.000",
                        "render": "1.000",
                        "syntax": "1.000",
                        "poster_path": "figures/benchmark_examples/xiaomi.png",
                        "video_path": "videos/benchmark_examples/xiaomi.mp4",
                    }
                ],
            }
        ]
        markdown = render_public_benchmark_markdown(
            report=report,
            generated_on="April 7, 2026",
            examples=examples,
        )
        self.assertIn("# Public Manim Benchmark", markdown)
        self.assertIn("Xiaomi MiMo-V2-Pro", markdown)
        self.assertIn("## Rendered Examples", markdown)
        self.assertIn("videos/benchmark_examples/xiaomi.mp4", markdown)
        self.assertNotIn("## Unresolved Models", markdown)
