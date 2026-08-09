from __future__ import annotations

import re
import sys
from pathlib import Path

from mac_pipeline.local_inference_types import LocalGenerationMetrics
from mac_pipeline.types import GenerationConfig

_VERBOSE_SEPARATOR = "=" * 10
_PROMPT_PATTERN = re.compile(
    r"^Prompt:\s+(?P<tokens>\d+)\s+tokens,\s+(?P<tps>[0-9]+(?:\.[0-9]+)?)\s+tokens-per-sec$"
)
_GENERATION_PATTERN = re.compile(
    r"^Generation:\s+(?P<tokens>\d+)\s+tokens,\s+(?P<tps>[0-9]+(?:\.[0-9]+)?)\s+tokens-per-sec$"
)
_PEAK_MEMORY_PATTERN = re.compile(
    r"^Peak memory:\s+(?P<gb>[0-9]+(?:\.[0-9]+)?)\s+GB$"
)


def build_subprocess_command(
    base_model: str,
    adapter_path: Path | None,
    prompt: str,
    system_prompt: str | None,
    generation: GenerationConfig,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "mlx_lm",
        "generate",
        "--model",
        base_model,
        "--prompt",
        prompt,
        "--max-tokens",
        str(generation.max_tokens),
        "--temp",
        str(generation.temperature),
        "--top-p",
        str(generation.top_p),
        "--seed",
        str(generation.seed),
        "--verbose",
        "True",
    ]
    if adapter_path is not None:
        command.extend(["--adapter-path", str(adapter_path)])
    if generation.top_k > 0:
        command.extend(["--top-k", str(generation.top_k)])
    if generation.draft_model:
        command.extend(
            [
                "--draft-model",
                generation.draft_model,
                "--num-draft-tokens",
                str(generation.num_draft_tokens),
            ]
        )
    if system_prompt:
        command.extend(["--system-prompt", system_prompt])
    return command


def parse_verbose_output(
    output: str,
    wall_seconds: float,
) -> tuple[str, LocalGenerationMetrics]:
    lines = output.splitlines()
    if not lines:
        raise RuntimeError("mlx_lm generate returned no stdout.")

    if lines[0] != _VERBOSE_SEPARATOR:
        text = output.strip()
        metrics = LocalGenerationMetrics(
            transport="subprocess",
            wall_seconds=wall_seconds,
        )
        return text, metrics

    prompt_index = next(
        (
            index
            for index in range(len(lines) - 1, -1, -1)
            if lines[index].startswith("Prompt:")
        ),
        None,
    )
    if prompt_index is None:
        if "No text generated for this prompt" in output:
            metrics = LocalGenerationMetrics(
                transport="subprocess",
                wall_seconds=wall_seconds,
                generation_tokens=0,
                end_to_end_generation_tokens_per_second=0.0,
            )
            return "", metrics
        raise RuntimeError("Unable to parse verbose mlx_lm output.")

    if prompt_index < 2 or lines[prompt_index - 1] != _VERBOSE_SEPARATOR:
        raise RuntimeError("Malformed verbose mlx_lm output.")

    prompt_match = _PROMPT_PATTERN.match(lines[prompt_index])
    generation_match = (
        _GENERATION_PATTERN.match(lines[prompt_index + 1])
        if prompt_index + 1 < len(lines)
        else None
    )
    peak_memory_match = (
        _PEAK_MEMORY_PATTERN.match(lines[prompt_index + 2])
        if prompt_index + 2 < len(lines)
        else None
    )
    if prompt_match is None or generation_match is None or peak_memory_match is None:
        raise RuntimeError("Unable to parse mlx_lm timing statistics.")

    text = "\n".join(lines[1 : prompt_index - 1]).strip("\n")
    generation_tokens = int(generation_match.group("tokens"))
    metrics = LocalGenerationMetrics(
        transport="subprocess",
        wall_seconds=wall_seconds,
        prompt_tokens=int(prompt_match.group("tokens")),
        prompt_tokens_per_second=float(prompt_match.group("tps")),
        generation_tokens=generation_tokens,
        generation_tokens_per_second=float(generation_match.group("tps")),
        end_to_end_generation_tokens_per_second=(
            generation_tokens / wall_seconds if wall_seconds > 0 else None
        ),
        peak_memory_gb=float(peak_memory_match.group("gb")),
    )
    return text, metrics
