# Manim Dataset Round 13 Expansion And Hugging Face Preview Fix

Date: 2026-05-11

## Context

The `autoresearch_manim_finetune` repo publishes a Hugging Face dataset, `sebastianboehler/autoresearch-manim`, from the canonical local dataset at `data/manim_dataset.jsonl`. The public dataset card has a preview gallery, but the rendered page currently shows broken image placeholders.

The local export in `artifacts/hf_datasets/autoresearch-manim/README.md` references suffixed preview files such as `assets/ml-attention-1.png`. The live Hugging Face dataset repository currently contains unsuffixed files such as `assets/ml-attention.png`, so the card references paths that do not exist on the Hub.

The repo already has a suitable sample workflow:

- stage new synthetic rows in `data/manim_review_candidates_*.json` or `.jsonl`
- render staged rows with `uv run python -m mac_pipeline.cli render-review-candidates`
- review rendered samples with the sample review app or a review JSONL
- promote approved rows with `uv run python -m mac_pipeline.cli promote-review-candidates`
- rebuild the canonical dataset through `scripts/rebuild_canonical_dataset.py`

## Goals

- Fix the Hugging Face dataset card preview gallery so uploaded image links resolve reliably.
- Add 30 new high-quality plain-Manim candidate samples for community-facing dataset expansion.
- Verify candidate quality before promotion into the canonical dataset.
- Keep the implementation aligned with existing shard, render, review, promote, and export paths.

## Non-Goals

- Do not add external Manim libraries, remote assets, mock data, or fallback sample rows.
- Do not bypass candidate review by directly editing only `data/manim_dataset.jsonl`.
- Do not change the fine-tuning architecture or benchmark model selection as part of this work.
- Do not require a new Hugging Face dataset layout unless the existing export path cannot be made reliable.

## Recommended Approach

Use a staged Round 13 candidate shard plus a small Hugging Face card/export fix.

The gallery fix should make preview asset names deterministic and stable. When copying preview items into the export directory, the exporter should preserve the original basename if no duplicate path exists in the current export operation. The generated README should reference exactly the files that will be uploaded. A verification step should confirm that every Markdown image path in the generated dataset card exists inside the export directory.

The sample expansion should create `data/manim_review_candidates_round13_public_quality.json` with 30 candidate records. Each row should follow the existing case schema and include:

- `case_id`
- `prompt`
- `completion`
- `entry_scene`
- `tags`
- `must_contain`
- `must_not_contain`
- `source_name`
- `source_domain`
- `source_repo_path`
- `uses_custom_library: false`
- `is_plain_manim_candidate: true`
- `requires_manual_conversion: false`
- `target_duration_seconds`
- `target_duration_tolerance_seconds`
- `license: MIT`

After rendering and review, approved candidates should be promoted into `data/manim_review_promoted.jsonl`, and `data/manim_dataset.jsonl` should be rebuilt from canonical sources.

## Candidate Mix

The 30 samples should improve public dataset value rather than only inflate count.

- 10 compact learning-app explainers, usually 12-18 seconds
- 6 math, calculus, and linear algebra scenes
- 5 machine-learning or code-visualization scenes
- 4 physics or engineering scenes
- 3 economics or statistics scenes
- 2 biology or chemistry scenes

Most scenes should be compact, clear educational explainers. A small minority can use more advanced Manim APIs such as `MovingCameraScene`, `ZoomedScene`, `ThreeDScene`, `Surface`, `StreamLines`, `TransformMatchingTex`, or `Code`, but only where that API directly improves the teaching value.

## Quality Bar

Each sample should teach one clear idea with a visible visual arc. Good rows should have:

- plain Manim Community Edition code with `from manim import *`
- exactly one scene class
- no external assets or custom libraries
- stable layout with readable text
- 3-5 intentional animation beats
- meaningful `must_contain` checks tied to the requested Manim constructs
- `must_not_contain` checks for forbidden custom library use when relevant
- row-level MIT license metadata

Samples should avoid:

- dense paragraphs on screen
- decorative complexity without explanatory value
- fragile camera choreography unless the scene is specifically about camera behavior
- repeated waits or highlight loops that technically render but feel low quality
- code that depends on file system assets, network access, or unsupported plugins

## Verification

Use layered verification before considering the work complete:

1. Run schema/load checks against the Round 13 candidate shard.
2. Check for duplicate `case_id` values across existing canonical cases, promoted rows, rejected rows, and the new candidate shard.
3. Run the static generation-quality audit on the new completions.
4. Render the candidate shard with the existing `render-review-candidates` command.
5. Promote only rows with successful renders and acceptable manual review decisions.
6. Rebuild `data/manim_dataset.jsonl`.
7. Regenerate the Hugging Face export.
8. Verify every dataset-card Markdown image path exists in the regenerated export directory.
9. Check the live or upload-ready Hugging Face asset paths use the same filenames referenced by the card.

## Error Handling

If a candidate fails schema validation, duplicate-id checks, static quality audit, or rendering, fix the candidate record directly or leave it unpromoted. Do not add fallback rows to reach the target count. If fewer than 30 rows pass, generate replacement candidates and run the same verification path.

If preview images still fail after export regeneration, prefer stable local asset references over removing the gallery. Remove the preview gallery only if verified image assets cannot be uploaded or resolved through the Hugging Face dataset card renderer.

## Files Expected To Change

- `mac_pipeline/hf_dataset.py` for deterministic preview asset copying and card path verification.
- Tests covering preview item filename stability and missing-card-asset detection.
- `data/manim_review_candidates_round13_public_quality.json` for staged samples.
- `data/manim_review_promoted.jsonl` after approved promotion.
- `data/manim_dataset.jsonl` after canonical rebuild.
- `artifacts/hf_datasets/autoresearch-manim/README.md` and `assets/` after export regeneration.
- Optional review artifacts under `artifacts/review_candidate_renders/round13_public_quality/`.

## Completion Criteria

- The generated Hugging Face dataset card has no broken local preview image references.
- The Round 13 shard starts with 30 high-quality candidate samples, and the final promoted dataset gains 30 newly approved samples from that shard after replacement of any failed candidates.
- Render results and promotion decisions are traceable through existing artifact and review files.
- The canonical dataset rebuild succeeds.
- Relevant automated tests pass.
