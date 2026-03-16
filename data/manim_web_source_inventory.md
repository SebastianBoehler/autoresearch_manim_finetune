# Manim Web Source Inventory

This file tracks web-discovered Manim source pools that are worth importing,
converting, or using as eval-only inspiration.

## Direct import candidates

- `ManimCommunity/jupyter_examples`
  - URL: <https://github.com/ManimCommunity/jupyter_examples>
  - Why it matters: official Manim Community examples in notebook form
  - Format: `ipynb`
  - Compatibility: plain Manim Community
  - Action: build a notebook importer that extracts `%%manim` cells into cases

- `jeertmans/manim-tutorial`
  - URL: <https://github.com/jeertmans/manim-tutorial>
  - License: MIT
  - Why it matters: contains `examples/manim_examples.py` with Community examples
  - Compatibility: mixed repo, but includes plain CE examples and separate ManimGL examples
  - Action: include in repo-ingest and keep only plain-Manim cases

## Inspiration / conversion sources

- Official Manim docs examples
  - URL: <https://docs.manim.community/en/stable/examples.html>
  - Why it matters: reliable Community Edition patterns for camera motion, vector fields, and 3D scene structure
  - Compatibility: plain Manim Community
  - Action: keep converting scene choreography and API patterns into our own long-form gold cases

- `3b1b/videos`
  - URL: <https://github.com/3b1b/videos>
  - License: CC BY-NC-SA 4.0
  - Why it matters: very rich 3Blue1Brown-style scene logic and pedagogy
  - Compatibility: older `manimlib` / `manim_imports_ext` stack, not Manim Community
  - Action: use as inspiration or manual conversion source, not direct training import

- `3b1b/manim`
  - URL: <https://github.com/3b1b/manim>
  - License: MIT
  - Why it matters: original ManimGL engine plus example scenes
  - Compatibility: ManimGL / `manimlib`, not Community Edition
  - Action: use for conversion ideas and API comparison, not direct CE training

- `jeertmans/manim-slides`
  - URL: <https://github.com/jeertmans/manim-slides>
  - License: MIT
  - Why it matters: slide-oriented scenes and presentation patterns
  - Compatibility: plugin-specific `Slide` API
  - Action: inspiration only unless we explicitly want plugin-conditioned outputs

- `dynamic-manim-components`
  - URL: <https://github.com/philip-murray/dynamic-manim-components>
  - License: MIT
  - Why it matters: good examples for equation editing and staged math transforms
  - Compatibility: plugin-specific `reactive_manim`
  - Action: use for converting math-animation ideas into plain-Manim gold cases

## Prompt / eval source

- `generative-manim`
  - URL: <https://github.com/360macky/generative-manim>
  - Why it matters: already contains a benchmark suite under `training/benchmarks/tasks/core_v1.jsonl`
  - Compatibility: tasks are prompt/eval metadata, not direct scene examples
  - Action: mine for held-out eval prompts and feature-coverage challenge cases

## Community discovery

- Reddit tutorial thread:
  - URL: <https://www.reddit.com/r/manim/comments/pz4h6d/manim_tutorial_github_repo/>
  - Why it matters: useful trailhead to `manim-tutorial` and adjacent community examples
  - Action: use as a discovery path, not as a direct training source
