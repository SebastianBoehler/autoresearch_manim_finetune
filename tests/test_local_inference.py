from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mac_pipeline.local_inference import (
    clear_model_cache,
    generate_completion,
    generate_completion_result,
)
from mac_pipeline.local_inference import _native_stop_reason, _should_stop_stream
from mac_pipeline.local_inference_cli import build_subprocess_command, parse_verbose_output
from mac_pipeline.local_inference_types import LocalGenerationResult
from mac_pipeline.types import GenerationConfig


class LocalInferenceTests(unittest.TestCase):
    def tearDown(self) -> None:
        clear_model_cache()

    def test_generate_completion_uses_in_process_transport_by_default(self) -> None:
        expected = LocalGenerationResult(
            text="print('hi')",
            metrics=SimpleNamespace(),
        )
        with patch(
            "mac_pipeline.local_inference._generate_in_process",
            return_value=expected,
        ) as mock_generate:
            text = generate_completion(
                base_model="demo/model",
                adapter_path=None,
                prompt="Draw a circle.",
                system_prompt=None,
                generation=GenerationConfig(),
            )

        self.assertEqual(text, "print('hi')")
        mock_generate.assert_called_once()

    def test_generate_completion_result_routes_to_subprocess_transport(self) -> None:
        expected = LocalGenerationResult(
            text="print('bye')",
            metrics=SimpleNamespace(),
        )
        with patch(
            "mac_pipeline.local_inference._generate_subprocess",
            return_value=expected,
        ) as mock_generate:
            result = generate_completion_result(
                base_model="demo/model",
                adapter_path=Path("/tmp/adapter"),
                prompt="Draw a square.",
                system_prompt="You are helpful.",
                generation=GenerationConfig(),
                transport="subprocess",
            )

        self.assertEqual(result.text, "print('bye')")
        mock_generate.assert_called_once()

    def test_parse_verbose_output_extracts_text_and_metrics(self) -> None:
        output = "\n".join(
            [
                "==========",
                "from manim import *",
                "",
                "class Demo(Scene):",
                "    pass",
                "==========",
                "Prompt: 128 tokens, 512.500 tokens-per-sec",
                "Generation: 64 tokens, 128.250 tokens-per-sec",
                "Peak memory: 7.125 GB",
            ]
        )

        text, metrics = parse_verbose_output(output, wall_seconds=1.5)

        self.assertIn("class Demo(Scene)", text)
        self.assertEqual(metrics.transport, "subprocess")
        self.assertEqual(metrics.prompt_tokens, 128)
        self.assertEqual(metrics.generation_tokens, 64)
        self.assertAlmostEqual(metrics.prompt_tokens_per_second, 512.5)
        self.assertAlmostEqual(metrics.generation_tokens_per_second, 128.25)
        self.assertAlmostEqual(metrics.end_to_end_generation_tokens_per_second, 64 / 1.5)
        self.assertAlmostEqual(metrics.peak_memory_gb, 7.125)

    def test_dynamic_stop_halts_complete_manim_scene(self) -> None:
        text = """from manim import *

class Demo(Scene):
    def construct(self):
        dot = Dot()
        self.play(FadeIn(dot), run_time=4)
        self.play(dot.animate.shift(RIGHT), run_time=4)
        self.play(dot.animate.shift(LEFT), run_time=4)
        self.wait(2)
"""
        should_stop = _should_stop_stream(
            [text],
            "Create a 15-second Manim scene.",
            GenerationConfig(dynamic_manim_stop=True, dynamic_stop_min_tokens=1),
            generation_tokens=128,
        )

        self.assertTrue(should_stop)

    def test_native_stop_reason_prefers_model_eos(self) -> None:
        self.assertEqual(
            _native_stop_reason("stop", 42, GenerationConfig(max_tokens=100)),
            "model_eos",
        )
        self.assertEqual(
            _native_stop_reason("length", 100, GenerationConfig(max_tokens=100)),
            "token_ceiling",
        )

    def test_dynamic_stop_respects_check_interval(self) -> None:
        text = """from manim import *

class Demo(Scene):
    def construct(self):
        dot = Dot()
        self.play(FadeIn(dot), run_time=4)
        self.play(dot.animate.shift(RIGHT), run_time=4)
        self.play(dot.animate.shift(LEFT), run_time=4)
        self.wait(2)
"""
        generation = GenerationConfig(
            dynamic_manim_stop=True,
            dynamic_stop_min_tokens=1,
            dynamic_stop_check_interval=16,
        )

        self.assertFalse(
            _should_stop_stream([text], "Create a 15-second Manim scene.", generation, 127)
        )
        self.assertTrue(
            _should_stop_stream([text], "Create a 15-second Manim scene.", generation, 128)
        )

    def test_subprocess_command_includes_speculative_draft_flags(self) -> None:
        command = build_subprocess_command(
            base_model="mlx-community/Qwen2.5-Coder-3B-Instruct-4bit",
            adapter_path=None,
            prompt="Draw a sine wave.",
            system_prompt=None,
            generation=GenerationConfig(
                draft_model="mlx-community/Qwen2.5-Coder-0.5B-Instruct-4bit",
                num_draft_tokens=4,
            ),
        )

        self.assertIn("--draft-model", command)
        self.assertIn("mlx-community/Qwen2.5-Coder-0.5B-Instruct-4bit", command)
        self.assertIn("--num-draft-tokens", command)
        self.assertIn("4", command)


if __name__ == "__main__":
    unittest.main()
