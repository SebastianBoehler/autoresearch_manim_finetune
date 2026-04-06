from __future__ import annotations

import time
import uuid
from typing import Iterable

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from mac_pipeline.types import GenerationConfig

MAX_ADK_ATTEMPTS = 4
ADK_RETRY_BASE_SECONDS = 15


def _extract_text(parts: Iterable[types.Part]) -> str:
    text_parts = [part.text.strip() for part in parts if getattr(part, "text", None)]
    return "\n".join(part for part in text_parts if part).strip()


def generate_adk_openrouter_completion(
    *,
    model: str,
    prompt: str,
    system_prompt: str | None,
    generation: GenerationConfig,
) -> str:
    last_error: Exception | None = None
    for attempt in range(1, MAX_ADK_ATTEMPTS + 1):
        session_service = InMemorySessionService()
        app_name = "autoresearch-manim-adk"
        user_id = "benchmark-user"
        session_id = str(uuid.uuid4())
        agent = LlmAgent(
            name="manim_benchmark_agent",
            model=LiteLlm(model=f"openrouter/{model}", timeout=180),
            instruction=system_prompt or "Return a single runnable Manim Python snippet.",
            include_contents="none",
            generate_content_config=types.GenerateContentConfig(
                temperature=generation.temperature,
                top_p=generation.top_p,
                max_output_tokens=generation.max_tokens,
            ),
        )
        runner = Runner(
            agent=agent,
            app_name=app_name,
            session_service=session_service,
            auto_create_session=True,
        )
        content = types.Content(role="user", parts=[types.Part(text=prompt)])

        final_response = ""
        try:
            for event in runner.run(user_id=user_id, session_id=session_id, new_message=content):
                if not event.is_final_response() or not event.content or not event.content.parts:
                    continue
                final_response = _extract_text(event.content.parts)
        except Exception as exc:  # pragma: no cover - ADK surfaces many dynamic exception types.
            last_error = exc

        if final_response:
            return final_response
        if attempt < MAX_ADK_ATTEMPTS:
            time.sleep(ADK_RETRY_BASE_SECONDS * attempt)

    if last_error is not None:
        raise RuntimeError(f"ADK failed for model {model}: {last_error}") from last_error
    raise RuntimeError(f"ADK did not return a final text response for model {model}.")
