---
name: manim-demo-safe-fast
description: Supplemental benchmark guidance for compact, render-safe Manim learning-app demos.
---

# Manim Demo Safe Fast

Use this as a compact generation style for on-demand learning-app scenes.

## Output Contract

- Return only runnable Python code.
- Use `from manim import *`.
- Define exactly one scene class.
- Keep the scene compact: 3-5 `self.play(...)` calls and at most 2 `self.wait(...)` calls.
- Prefer a finished 12-18 second explanation over decorative extra steps.

## Render-Safe Manim Rules

- Do not pass `opacity=` into Manim constructors. Use `fill_opacity=` or `stroke_opacity=`.
- Use `SurroundingRectangle(...)` only around Mobjects, never around coordinates or raw points.
- For a band on a `NumberLine`, create a `Rectangle(width=..., height=..., fill_opacity=...)` and move it to the midpoint.
- Avoid unsupported constructor kwargs such as `include_background_box`, `background_box_style`, `tick_frequency`, `include_first_row`, `include_first_column`, and `column_widths`.
- Avoid custom helper classes and external assets.

## Taste Rules

- Use one clear title, one main visual, and one short takeaway caption.
- Keep labels outside the primary geometry.
- Use one accent color for the active idea and muted colors for context.
- Prefer grouped animations over repeated highlight/wait loops.
