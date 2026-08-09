from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mac_pipeline.latency_benchmark import run_latency_benchmark
from mac_pipeline.local_inference_types import LocalGenerationMetrics, LocalGenerationResult
from mac_pipeline.types import BenchmarkConfig, BenchmarkTargetConfig, EvaluationConfig, GenerationConfig


class LatencyBenchmarkTests(unittest.TestCase):
    def test_run_latency_benchmark_writes_summary_and_respects_transport(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            dataset_dir = repo_root / "artifacts" / "datasets" / "demo"
            dataset_dir.mkdir(parents=True)
            (dataset_dir / "test.jsonl").write_text(
                json.dumps(
                    {
                        "case_id": "demo-case",
                        "messages": [
                            {"role": "system", "content": "Base system prompt."},
                            {"role": "user", "content": "Draw a circle."},
                        ],
                    }
                )
                + "\n"
            )

            benchmark = BenchmarkConfig(
                name="latency-test",
                dataset_dir="artifacts/datasets/demo",
                output_dir="artifacts/benchmarks/latency-test",
                generation=GenerationConfig(local_transport="in_process"),
                evaluation=EvaluationConfig(max_cases=1, run_render=False),
                targets=[
                    BenchmarkTargetConfig(
                        name="local-base-subprocess",
                        backend="local",
                        model="Qwen/Qwen2.5-Coder-3B-Instruct",
                        local_transport="subprocess",
                        draft_model="mlx-community/Qwen2.5-Coder-0.5B-Instruct-4bit",
                        num_draft_tokens=4,
                    ),
                    BenchmarkTargetConfig(
                        name="local-base-in-process",
                        backend="local",
                        model="Qwen/Qwen2.5-Coder-3B-Instruct",
                        local_transport="in_process",
                    )
                ],
            )

            call_count = 0
            draft_models: list[str | None] = []

            def fake_generate_completion_result(
                *,
                transport: str,
                generation: GenerationConfig,
                **_: object,
            ) -> LocalGenerationResult:
                nonlocal call_count
                call_count += 1
                draft_models.append(generation.draft_model)
                return LocalGenerationResult(
                    text="print('ok')",
                    metrics=LocalGenerationMetrics(
                        transport=transport,
                        wall_seconds=0.5,
                        ttft_seconds=None if transport == "subprocess" else 0.1,
                        prompt_tokens=100,
                        prompt_tokens_per_second=400.0,
                        generation_tokens=50,
                        generation_tokens_per_second=125.0,
                        end_to_end_generation_tokens_per_second=100.0,
                        peak_memory_gb=6.5,
                    ),
                )

            with patch(
                "mac_pipeline.latency_benchmark.generate_completion_result",
                side_effect=fake_generate_completion_result,
            ):
                payload = run_latency_benchmark(
                    benchmark,
                    repo_root,
                    max_tokens=32,
                    target_names={"local-base-subprocess"},
                    warmup_cases=1,
                    repetitions=2,
                )

            output_path = (
                repo_root
                / "artifacts"
                / "benchmarks"
                / "latency-test"
                / "local-base-subprocess-latency.json"
            )
            target_payload = json.loads(output_path.read_text())

        self.assertEqual(call_count, 3)
        self.assertEqual(payload["max_tokens"], 32)
        self.assertEqual(len(payload["targets"]), 1)
        self.assertEqual(payload["leaderboard"][0]["local_transport"], "subprocess")
        self.assertEqual(target_payload["local_transport"], "subprocess")
        self.assertEqual(
            target_payload["draft_model"],
            "mlx-community/Qwen2.5-Coder-0.5B-Instruct-4bit",
        )
        self.assertEqual(target_payload["num_draft_tokens"], 4)
        self.assertEqual(
            draft_models,
            ["mlx-community/Qwen2.5-Coder-0.5B-Instruct-4bit"] * 3,
        )
        self.assertEqual(target_payload["summary"]["num_samples"], 2)
        self.assertEqual(target_payload["summary"]["mean_wall_seconds"], 0.5)
        self.assertEqual(target_payload["summary"]["mean_generation_tokens_per_second"], 125.0)


if __name__ == "__main__":
    unittest.main()
