from __future__ import annotations

from typing import Any

from mac_pipeline.types import GenerationConfig


def build_runtime_options(tokenizer: Any, generation: GenerationConfig) -> tuple[Any, list[Any], Any, Any]:
    mx, stream_generate, make_sampler, make_logits_processors = _import_sampling_runtime()
    sampler = make_sampler(
        generation.temperature,
        generation.top_p,
        0.0,
        1,
        top_k=generation.top_k,
        xtc_probability=0.0,
        xtc_threshold=0.0,
        xtc_special_tokens=_encode_text(tokenizer, "\n") + list(tokenizer.eos_token_ids),
    )
    logits_processors = make_logits_processors(
        logit_bias=_suppressed_token_biases(tokenizer, generation.suppressed_token_texts),
        repetition_penalty=generation.repetition_penalty,
        repetition_context_size=generation.repetition_context_size,
        presence_penalty=generation.presence_penalty,
        presence_context_size=generation.presence_context_size,
        frequency_penalty=generation.frequency_penalty,
        frequency_context_size=generation.frequency_context_size,
    )
    return sampler, logits_processors, mx, stream_generate


def _suppressed_token_biases(tokenizer: Any, token_texts: list[str]) -> dict[int, float] | None:
    if not token_texts:
        return None
    biases: dict[int, float] = {}
    for text in token_texts:
        token_ids = _encode_text_without_special_tokens(tokenizer, text)
        if len(token_ids) != 1:
            raise ValueError(
                f"suppressed_token_texts entries must encode to one token: {text!r} -> {token_ids}"
            )
        biases[token_ids[0]] = -100.0
    return biases


def _encode_text_without_special_tokens(tokenizer: Any, text: str) -> list[int]:
    try:
        return list(tokenizer.encode(text, add_special_tokens=False))
    except TypeError:
        return list(tokenizer.encode(text))


def _encode_text(tokenizer: Any, text: str) -> list[int]:
    add_special_tokens = getattr(tokenizer, "bos_token", None) is None or not text.startswith(
        getattr(tokenizer, "bos_token", "") or ""
    )
    try:
        return list(tokenizer.encode(text, add_special_tokens=add_special_tokens))
    except TypeError:
        return list(tokenizer.encode(text))


def _import_sampling_runtime() -> tuple[Any, Any, Any, Any]:
    try:
        import mlx.core as mx
        from mlx_lm import stream_generate
        from mlx_lm.sample_utils import make_logits_processors, make_sampler
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Local MLX inference requires `mlx_lm`. Install the repo environment with `uv sync`."
        ) from exc
    return mx, stream_generate, make_sampler, make_logits_processors
