# Curated Manim Dataset v1

This repository now treats `data/manim_dataset.jsonl` as historical raw input and
`data/curated/manim_v0_20_1/` as the training and benchmark source of truth.

## Runtime contract

- Manim Community Edition: exactly `0.20.1`
- Python context: `3.13`
- verified renderer: `cairo`
- dataset version: `manim-curated-v1`
- split policy: concept-and-source-grouped v1, seed 42

Every accepted row carries the runtime version, corpus roles, extracted Manim API
symbols and methods, its split group, and successful exact-scene render evidence.
The system message explicitly tells the model to generate only Manim Community
Edition 0.20.1 code.

## Current disposition

| Disposition | Rows | Meaning |
|---|---:|---|
| Accepted | 150 | Exact-scene rendered and eligible for the curated corpus |
| Quarantine | 68 | Preserved, but awaiting a discriminating review or simplification |
| Rewrite | 24 | Has a concrete render, factual, constraint, or teaching defect |

The frozen split is 120 train, 15 validation, and 15 test rows. The API-reference
lane contains 17 accepted rows. The current top-level API coverage uses 92 of the
401 public callables discovered from the pinned installation, with 197 inferred
object methods represented.

Eight new expansion-v1 rows add statistics, computer science, biology, control
engineering, chemistry, linguistics, medicine, and climate science. All eight
passed exact rendering, duration tolerance, and representative-frame review; the
auditable review record is `data/manim_interdisciplinary_expansion_v1_review.json`.

Twenty expansion-v2 rows broaden the corpus across astronomy, geology, electrical
and mechanical engineering, materials, operations research, cybersecurity,
databases, networking, algorithms, geometry, economics, logic, music,
psychology, physiology, microbiology, quantum physics, fluid mechanics, and
epidemiology. Four are longer 25-second, multi-beat explainers for opportunity
cost and specialization, signal detection, antibiotic selection, and Bernoulli
flow. They still define exactly one scene class, but use progressive disclosure
to teach a causal sequence. All 20 passed exact rendering, duration tolerance,
factual/mechanism audit, and representative-frame review; the auditable record is
`data/manim_diverse_expansion_v2_review.json`.

These figures describe code/API coverage, not full educational coverage. A symbol
needs examples across multiple concepts and fields before it counts as robustly
covered.

## Rebuild

```bash
PYTHONPATH=. .venv/bin/python scripts/snapshot_manim_api.py \
  --version 0.20.1 \
  --output /tmp/manim_api_surface_v0_20_1.json

PYTHONPATH=. .venv/bin/python scripts/build_curated_dataset.py
```

The checked-in API snapshot changes only when the pinned Manim version changes.
The curation manifest records the source digest and refuses to build if raw rows
change without an explicit decision.

## Generated files

- `cases.jsonl`: accepted, enriched canonical rows.
- `train.jsonl`, `valid.jsonl`, `test.jsonl`: grouped MLX chat splits.
- `api_reference.jsonl`: clean versioned API-reference lane.
- `quarantine.jsonl`: reversible exclusions awaiting review.
- `rewrite.jsonl`: concrete repair queue.
- `api_coverage.json`: symbol/method coverage and gaps.
- `manifest.json`: counts, digests, runtime, split, and ablation metadata.
- `ablations/`: alternative training sets sharing the same validation and test rows.

## Training

Build the curated dataset once, then use `train` and `eval` separately. Do not use
the legacy `run` command with these configs because it rebuilds row-level splits.

```bash
uv run python -m mac_pipeline.cli train \
  --config configs/m4_max_qwen25coder_3b_curated_v1.json

uv run python -m mac_pipeline.cli eval \
  --config configs/m4_max_qwen25coder_3b_curated_v1.json
```

Equivalent configs exist for:

- pedagogical-only training;
- API-reference-only training;
- training without composite/long-form rows.

All variants share the same frozen validation and test splits. The optimizer-step
budget is also held fixed. Reports should still include examples and tokens seen,
because the API-only training set is intentionally much smaller.

## Quality benchmark

After the adapters exist:

```bash
uv run python -m mac_pipeline.cli benchmark \
  --config configs/local_mlx_curated_v1_quality_benchmark.json
```

Compare raw model output first. Syntax repair, render repair, and pacing repair are
reported separately and must not be merged into the raw model-quality score.

## TPS and responsiveness benchmark

```bash
uv run python -m mac_pipeline.cli latency-benchmark \
  --config configs/local_mlx_curated_v1_tps_benchmark.json \
  --warmup-cases 1 \
  --repetitions 3
```

The latency benchmark compares the 3B base model, curated 3B adapter, speculative
decoding with a 0.5B draft, and a 1.5B base model. Record at least:

- prompt-processing TPS;
- decode TPS;
- end-to-end TPS;
- time to first token;
- total generation wall time;
- generated token count and stop reason.

TPS alone is not the product objective. Promotion requires a quality floor on the
same frozen holdout: valid Python, exact-scene render, prompt-contract coverage,
acceptable pacing, visual readability, factual correctness, and teaching value.

## Future expansion

New candidates should fill both an API matrix and a disciplinary/visual matrix.
Machine learning is only one field. Planned coverage includes mathematics,
statistics, physics, engineering, chemistry, biology, medicine, computer science,
economics, social science, humanities, and language, using process animations,
graphs, spatial diagrams, comparisons, timelines, algorithm traces, and precise
static infographics.

Every candidate still needs one objective, a visible mechanism, a misconception or
boundary, and a transfer check. Successful rendering is necessary but not a review.
