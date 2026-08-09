from __future__ import annotations

import inspect
from types import ModuleType
from typing import Any


def snapshot_public_api(
    manim_module: ModuleType | Any,
    *,
    python_version: str,
    expected_version: str | None = None,
) -> dict[str, Any]:
    manim_version = str(manim_module.__version__)
    if expected_version and manim_version != expected_version:
        raise ValueError(
            f"Expected Manim Community Edition {expected_version}, found {manim_version}."
        )
    public_symbols = sorted(
        name
        for name, value in vars(manim_module).items()
        if not name.startswith("_")
        and (inspect.isclass(value) or inspect.isfunction(value))
        and str(getattr(value, "__module__", "")).startswith("manim")
    )
    return {
        "schema_version": 1,
        "package": "manim",
        "manim_version": manim_version,
        "python_version": python_version,
        "public_symbols": public_symbols,
    }
