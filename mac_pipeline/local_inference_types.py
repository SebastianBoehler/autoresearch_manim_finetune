from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class LocalGenerationMetrics:
    transport: str
    wall_seconds: float
    ttft_seconds: float | None = None
    prompt_tokens: int | None = None
    prompt_tokens_per_second: float | None = None
    generation_tokens: int | None = None
    generation_tokens_per_second: float | None = None
    end_to_end_generation_tokens_per_second: float | None = None
    peak_memory_gb: float | None = None
    stop_reason: str | None = None
    hit_token_ceiling: bool | None = None
    draft_model: str | None = None
    num_draft_tokens: int | None = None
    draft_accept_count: int | None = None
    draft_accept_rate: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LocalGenerationResult:
    text: str
    metrics: LocalGenerationMetrics
