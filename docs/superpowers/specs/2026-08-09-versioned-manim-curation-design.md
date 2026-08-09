# Versioned Manim Dataset Curation Design

Date: 2026-08-09

## Context

The canonical corpus contains useful Manim Community Edition API breadth, but its
current tier labels mix provenance, renderability, and teaching quality. Some
promoted rows fail on Manim 0.20.1, some have documented visual defects, and the
row-level random split leaks closely related source and concept families across
training and evaluation.

The target product is a low-latency educational visual generator for LecturePilot
and similar university learning settings. It needs both pedagogically effective
single-concept examples and broad, explicit API coverage. Neither goal should be
used as a substitute for the other.

## Goals

- Preserve every raw source row and make cleanup reversible.
- Pin the supported Manim Community Edition API version.
- Add version and API-use context to every accepted training row.
- Separate pedagogical, API-reference, and composite corpus roles.
- Quarantine or rewrite known render, factual, and visual defects.
- Prevent source-family and concept-family leakage across benchmark splits.
- Produce deterministic artifacts suitable for ablation, training, quality, and
  tokens-per-second benchmark runs.
- Make future promotion require render, factual, pedagogical, and visual evidence.

## Non-Goals

- Do not delete historical source shards or review records.
- Do not silently repair weak scenes during export.
- Do not train a model or publish to Hugging Face in this change.
- Do not claim that static checks replace human pedagogical review.
- Do not optimize model architecture before the evaluation corpus is trustworthy.

## Dataset Layers

### Raw canonical input

`data/manim_dataset.jsonl` remains the reproducible aggregate of historical source
shards. It is not treated as an automatically trusted training set.

### Curation manifest

A versioned manifest records the expected input digest and count, the target
runtime, and explicit exceptions. New or changed raw rows invalidate the manifest
until reviewed. Decisions are:

- `accept`: eligible for curated exports.
- `quarantine`: excluded pending a fresh review.
- `rewrite`: excluded because a concrete defect must be corrected.

### Curated corpus

Accepted rows receive:

- an explicit Manim Community Edition 0.20.1 system prompt;
- `manim_version`, `python_version`, and `renderers_tested` metadata;
- top-level Manim API symbols and inferred object-method usage;
- one or more `corpus_roles`;
- a stable `split_group` derived from provenance and concept similarity.

The curated corpus is the only default input for new training and ablation runs.

### API-reference corpus

Rows with documentation/API-reference provenance are exported separately while
remaining available in the combined curated corpus. Minimal API demonstrations do
not need to pretend to be full pedagogical explainers.

## Corpus Roles

- `pedagogical`: teaches one concept with an interpretable visual mechanism.
- `api_reference`: demonstrates a supported Manim feature precisely.
- `composite`: combines multiple APIs into a longer or multi-stage explainer.

Roles may overlap. API coverage is measured across roles, domains, and split
groups so a symbol is not considered well covered merely because one template is
duplicated many times.

## API Version Contract

The environment and generated records target exactly Manim Community Edition
0.20.1. The system prompt must state that version. A versioned API-surface snapshot
contains public Manim callables discovered from the installed package. Dataset API
usage is extracted with Python AST parsing and matched against that snapshot.

Coverage reports include:

- used and unused public top-level symbols;
- example counts per symbol;
- distinct domains, roles, and split groups per symbol;
- inferred method usage such as `Axes.plot`;
- underrepresented symbols with only one example or one concept family.

## Initial Cleanup Policy

Known render failures, factually misleading scenes, prompt/output mismatches, and
the noisy repository-import block are excluded. Round 13 is quarantined because
its ratings are boilerplate render approvals rather than discriminating teaching
reviews. Previously promoted rows with explicit overlap, contrast, readability,
or layout defects are quarantined for repair.

The cleanup is conservative: excluded rows remain in the raw dataset and appear in
a generated disposition report with reasons.

## Promotion Contract

A promotable review must contain:

- an accepted decision label;
- `render_ok: true` for the exact declared scene;
- factual, pedagogical, and visual scores of at least 4/5;
- confidence of at least 0.8;
- no unresolved blocking issues.

The renderer must locate the MP4 for the declared scene. It must not accept an
arbitrary video produced from another scene in the same file.

## Leakage-Resistant Splits

Rows are grouped before assignment. The group key prioritizes shared source files,
then normalized concept tags and near-duplicate prompt fingerprints. Whole groups
are assigned deterministically to train, validation, or test while approximating
the requested fractions.

The export verifies that no `split_group` occurs in more than one split. The group
identifier is retained in each record for auditability.

## Benchmark Contract

Training and benchmark manifests record:

- curated dataset version and digest;
- Manim, Python, renderer, model, and adapter versions;
- split-group policy and seed;
- raw and repair-assisted syntax/render/quality rates separately;
- prompt processing, time to first token, decode TPS, end-to-end TPS, generation
  wall time, and render wall time;
- factual/pedagogical/visual human-review results for the fixed holdout set.

Quality and speed are separate axes. A faster model is a product candidate only if
it meets the frozen production-quality threshold.

## Verification

1. Unit tests fail before each new behavior is implemented.
2. The existing test suite remains green.
3. The curation builder rejects a changed or incomplete source corpus.
4. Every curated row contains version, API, role, and split metadata.
5. No group leaks across split files.
6. Strict promotion rejects incomplete review evidence.
7. The exact-scene renderer does not fall back to another MP4.
8. The generated coverage and disposition counts reconcile with the source count.

## Follow-Up Expansion

New rows should be planned on two coverage matrices simultaneously:

- disciplinary coverage: mathematics, statistics, physics, engineering, biology,
  medicine, chemistry, computer science, economics, social science, humanities,
  and language;
- visual/API coverage: processes, diagrams, spatial structures, graphs, algorithm
  traces, comparisons, timelines, and supported Manim features.

Every new sample still needs one objective, a visible mechanism, a misconception or
boundary, and a transfer check. Diversity cannot justify weak teaching examples.
