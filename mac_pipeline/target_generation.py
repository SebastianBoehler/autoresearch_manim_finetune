from __future__ import annotations

from dataclasses import replace

from mac_pipeline.types import BenchmarkTargetConfig, GenerationConfig


def generation_for_target(
    generation: GenerationConfig,
    target: BenchmarkTargetConfig,
) -> GenerationConfig:
    draft_model = target.draft_model or generation.draft_model
    num_draft_tokens = (
        target.num_draft_tokens
        if target.num_draft_tokens is not None
        else generation.num_draft_tokens
    )
    if draft_model == generation.draft_model and num_draft_tokens == generation.num_draft_tokens:
        return generation
    return replace(
        generation,
        draft_model=draft_model,
        num_draft_tokens=num_draft_tokens,
    )
