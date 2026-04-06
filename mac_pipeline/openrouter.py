from __future__ import annotations

import os
import time
from typing import Any

import requests

from mac_pipeline.types import BenchmarkTargetConfig, GenerationConfig, OpenRouterConfig

MAX_OPENROUTER_ATTEMPTS = 4
OPENROUTER_RETRY_BASE_SECONDS = 10


def _normalize_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                parts.append(item["text"])
                continue
            if isinstance(item.get("text"), dict) and isinstance(item["text"].get("value"), str):
                parts.append(item["text"]["value"])
        return "\n".join(part.strip() for part in parts if part.strip()).strip()
    raise RuntimeError(f"Unsupported OpenRouter message content type: {type(content)!r}")


def _headers(config: OpenRouterConfig) -> dict[str, str]:
    api_key = os.environ.get(config.api_key_env)
    if not api_key:
        raise RuntimeError(
            f"Missing OpenRouter API key. Set {config.api_key_env} before running remote benchmarks."
        )
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if config.site_url:
        headers["HTTP-Referer"] = config.site_url
    if config.app_name:
        headers["X-Title"] = config.app_name
    return headers


def _payload(
    target: BenchmarkTargetConfig,
    prompt: str,
    system_prompt: str | None,
    generation: GenerationConfig,
    config: OpenRouterConfig,
) -> dict[str, Any]:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload: dict[str, Any] = {
        "model": target.model,
        "messages": messages,
        "temperature": generation.temperature,
        "top_p": generation.top_p,
        "max_tokens": generation.max_tokens,
    }
    transforms = target.transforms or config.transforms
    if transforms:
        payload["transforms"] = transforms
    route = target.route or config.route
    if route:
        payload["route"] = route
    return payload


def generate_openrouter_completion(
    target: BenchmarkTargetConfig,
    prompt: str,
    system_prompt: str | None,
    generation: GenerationConfig,
    config: OpenRouterConfig,
) -> str:
    last_error: Exception | None = None
    for attempt in range(1, MAX_OPENROUTER_ATTEMPTS + 1):
        try:
            response = requests.post(
                f"{config.api_base.rstrip('/')}/chat/completions",
                headers=_headers(config),
                json=_payload(target, prompt, system_prompt, generation, config),
                timeout=config.timeout_seconds,
            )
        except requests.RequestException as exc:
            last_error = exc
            if attempt < MAX_OPENROUTER_ATTEMPTS:
                time.sleep(OPENROUTER_RETRY_BASE_SECONDS * attempt)
                continue
            break

        if response.status_code >= 400:
            last_error = RuntimeError(
                f"OpenRouter request failed with {response.status_code}: {response.text[:1200]}"
            )
            if response.status_code in {408, 429, 500, 502, 503, 504} and attempt < MAX_OPENROUTER_ATTEMPTS:
                time.sleep(OPENROUTER_RETRY_BASE_SECONDS * attempt)
                continue
            break

        payload = response.json()
        choices = payload.get("choices")
        if not choices:
            raise RuntimeError(f"OpenRouter response did not include choices: {payload}")
        message = choices[0].get("message", {})
        content = message.get("content")
        if content is None:
            raise RuntimeError(f"OpenRouter response did not include message content: {payload}")
        return _normalize_content(content)

    raise RuntimeError(f"OpenRouter failed for model {target.model}: {last_error}")
