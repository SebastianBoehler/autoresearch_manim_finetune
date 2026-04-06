from __future__ import annotations

from pathlib import Path

from mac_pipeline.types import BenchmarkTargetConfig
from mac_pipeline.utils import resolve_path

SKILL_PROMPT_HEADER = (
    "Apply the following repository skill as supplemental guidance. "
    "It does not change the output contract: return a single runnable Manim Python snippet "
    "that satisfies the user request."
)


def resolve_skill_path(repo_root: Path, skill_path: str) -> Path:
    path = resolve_path(repo_root, skill_path)
    return path / "SKILL.md" if path.is_dir() else path


def load_target_skill(
    target: BenchmarkTargetConfig,
    repo_root: Path,
) -> tuple[str | None, str | None]:
    if not target.skill_path:
        return None, None
    path = resolve_skill_path(repo_root, target.skill_path)
    if not path.exists():
        raise FileNotFoundError(f"Benchmark skill file does not exist: {path}")
    return path.read_text().strip(), str(path)


def compose_system_prompt(
    base_system_prompt: str | None,
    skill_text: str | None,
) -> str | None:
    parts: list[str] = []
    if base_system_prompt and base_system_prompt.strip():
        parts.append(base_system_prompt.strip())
    if skill_text and skill_text.strip():
        parts.append(f"{SKILL_PROMPT_HEADER}\n\n{skill_text.strip()}")
    if not parts:
        return None
    return "\n\n---\n\n".join(parts)
