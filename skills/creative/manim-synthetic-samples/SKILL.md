---
name: manim-synthetic-samples
description: Design, generate, audit, and stage synthetic Manim fine-tuning samples with a reasoning-first mechanism-design workflow. Use when creating new data/manim_* candidate shards, expanding underrepresented Manim coverage, reviewing sample quality, deciding prompt/completion diversity, or preparing render-review batches before promotion into data/manim_dataset.jsonl.
---

# Manim Synthetic Samples

## Overview

Create candidate Manim training samples by planning the dataset mechanism first, then generating records. Optimize for controlled coverage, local diversity, calibrated complexity, and renderable code quality instead of random topic brainstorming.

Use this skill for dataset samples. Use `manim-video` when the user wants an actual rendered video or production Manim scene.

## Core Workflow

1. Inspect the current corpus before proposing new records:
   - Read `data/manim_dataset.jsonl` plus recent `data/manim_review_candidates_*.json`.
   - Count tags, `must_contain` snippets, durations, scene base classes, and source domains.
   - Identify gaps as explicit target nodes, not vague themes.

2. Build a coverage scaffold:
   - Factor axes: Manim API feature, animation mechanic, visual layout, knowledge domain, duration, scene class, and render risk.
   - Write 8-20 target node sets for a batch before writing prompts.
   - Exclude illogical combinations, such as `ThreeDScene` with zoom-window requirements unless the sample intentionally teaches that constraint.

3. Generate meta-prompts from node sets:
   - Include concrete visual requirements, time budget, and expected movement.
   - Require enough specificity that `must_contain` can be checked mechanically.
   - Avoid prompts that merely rename an existing sample.

4. Create locally diverse variants:
   - For repeated concepts, vary the geometry, timing, narrative framing, and primary Manim constructs.
   - Keep variants semantically related but implementation-distinct.
   - Do not scale volume by cloning the same prompt with swapped nouns.

5. Complexify deliberately:
   - Complexify only a configured fraction of a batch, normally 20-40%.
   - Add difficulty through multi-stage state changes, camera behavior, fixed overlays, trackers, or comparisons.
   - Preserve renderability and readability; complexity that makes labels cramped is negative signal.

6. Apply quality gates:
   - Static audit with `scripts/audit_candidate_shard.py`.
   - Real render pass with the repo review commands.
   - Human review before promotion.

Read `references/mechanism-design.md` when designing a new batch or when a batch needs a principled coverage plan.

## Candidate Record Contract

Each candidate record must be a JSON object compatible with existing repo data:

- `case_id`: stable snake_case id, unique across the candidate shard and canonical dataset.
- `prompt`: user-facing task description with visual and timing requirements.
- `completion`: runnable Manim Community Edition code with `from manim import *` and exactly one intended scene class.
- `entry_scene`: class name to render.
- `tags`: include domain, mechanism, duration, `tier:candidate`, `status:unreviewed`, and `review-candidate` for staged samples.
- `must_contain`: snippets that prove the target Manim constructs are present.
- `must_not_contain`: forbidden snippets, especially unsupported custom libraries.
- `license`: normally `MIT` for locally authored synthetic records.
- Provenance fields: `source_name`, `source_domain`, `source_repo_path`, `uses_custom_library`, `is_plain_manim_candidate`, `requires_manual_conversion`.
- Optional timing fields: `target_duration_seconds`, `target_duration_tolerance_seconds`.

Use `data/manim_review_candidates_round<N>_<theme>.json` for staged batches unless the user asks for a different path.

## Static Audit

Run the bundled audit before rendering:

```bash
python skills/creative/manim-synthetic-samples/scripts/audit_candidate_shard.py \
  --input data/manim_review_candidates_roundN_theme.json \
  --canonical data/manim_dataset.jsonl \
  --summary artifacts/sample_audits/roundN_theme.json
```

The audit catches schema errors, duplicate ids, missing required snippets, forbidden snippets, syntax failures, missing entry scenes, and weak tag coverage. Treat errors as blockers. Treat warnings as prompts for review.

## Review Handoff

After static audit passes, use the repo workflow:

```bash
uv run python -m mac_pipeline.cli render-review-candidates \
  --input data/manim_review_candidates_roundN_theme.json \
  --output-dir artifacts/review_candidate_renders/roundN_theme
```

```bash
uv run python -m mac_pipeline.cli build-sample-review-session \
  --input data/manim_review_candidates_roundN_theme.json \
  --output-dir artifacts/reviews/candidate-roundN-theme-curation
```

Only promote samples that pass render review and add useful coverage:

```bash
uv run python -m mac_pipeline.cli promote-review-candidates \
  --input data/manim_review_candidates_roundN_theme.json \
  --review artifacts/reviews/candidate-roundN-theme-curation/ratings.jsonl
```
