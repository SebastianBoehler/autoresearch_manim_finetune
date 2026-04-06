from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mac_pipeline.benchmark import run_benchmark
from mac_pipeline.benchmark_prompting import (
    SKILL_PROMPT_HEADER,
    compose_system_prompt,
    load_target_skill,
    resolve_skill_path,
)
from mac_pipeline.types import BenchmarkConfig, BenchmarkTargetConfig, EvaluationConfig


class BenchmarkPromptingTests(unittest.TestCase):
    def test_resolve_skill_path_supports_skill_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            skill_dir = repo_root / "skills" / "creative" / "manim-video"
            skill_dir.mkdir(parents=True)
            expected = skill_dir / "SKILL.md"
            expected.write_text("# skill\n")

            resolved = resolve_skill_path(repo_root, "skills/creative/manim-video")

        self.assertEqual(resolved, expected)

    def test_compose_system_prompt_appends_skill_guidance(self) -> None:
        composed = compose_system_prompt("Base prompt.", "# Skill body")

        self.assertIsNotNone(composed)
        self.assertIn("Base prompt.", composed)
        self.assertIn(SKILL_PROMPT_HEADER, composed)
        self.assertIn("# Skill body", composed)

    def test_run_benchmark_injects_skill_into_generation_prompt(self) -> None:
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
            skill_dir = repo_root / "skills" / "creative" / "manim-video"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Hermes Skill\n\nUse pauses.\n")

            benchmark = BenchmarkConfig(
                name="prompt-test",
                dataset_dir="artifacts/datasets/demo",
                output_dir="artifacts/benchmarks/prompt-test",
                evaluation=EvaluationConfig(run_render=False, max_cases=1),
                targets=[
                    BenchmarkTargetConfig(
                        name="local-with-skill",
                        backend="local",
                        model="Qwen/Qwen2.5-Coder-3B-Instruct",
                        skill_path="skills/creative/manim-video",
                    )
                ],
            )

            captured: dict[str, str | None] = {}

            def fake_generate_completion(*, system_prompt: str | None, **_: object) -> str:
                captured["system_prompt"] = system_prompt
                return (
                    "```python\n"
                    "from manim import *\n\n"
                    "class Demo(Scene):\n"
                    "    def construct(self):\n"
                    "        self.add(Circle())\n"
                    "```"
                )

            with patch(
                "mac_pipeline.benchmark.generate_completion",
                side_effect=fake_generate_completion,
            ):
                payload = run_benchmark(benchmark, repo_root)

            output_path = repo_root / "artifacts" / "benchmarks" / "prompt-test" / "local-with-skill.json"
            target_payload = json.loads(output_path.read_text())
            skill_text, skill_path = load_target_skill(benchmark.targets[0], repo_root)

        self.assertEqual(payload["leaderboard"][0]["name"], "local-with-skill")
        self.assertEqual(target_payload["skill_path"], skill_path)
        self.assertEqual(
            captured["system_prompt"],
            compose_system_prompt("Base system prompt.", skill_text),
        )


if __name__ == "__main__":
    unittest.main()
