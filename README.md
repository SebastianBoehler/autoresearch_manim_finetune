# autoresearch_manim_finetune

This fork keeps Karpathy's `program.md`-driven research loop, but swaps the CUDA-only baseline for a Mac-friendly MLX LoRA pipeline aimed at **Manim code generation**. The goal is not generic next-token loss on web text. The goal is a small open-source coding model that gets better at producing runnable, stylistically clean Manim scenes on Apple Silicon.

The repo now has two paths:

- `mac_pipeline/`: the active Apple Silicon fine-tuning workflow using `mlx-lm` and a Manim-specific evaluation harness.
- `prepare.py` / `train.py`: the upstream CUDA experiment baseline, kept here as reference only.

## What This Pipeline Optimizes

Each run trains a LoRA adapter on a curated Manim dataset and evaluates it on:

- held-out `test_loss` from the same high-quality dataset
- syntax validity
- scene-class detection
- required / forbidden snippet checks
- optional real Manim render success

That gives you the fast metric you asked for, `test_loss`, while still catching the common failure mode where a model gets lower loss but worse at actually producing runnable scenes.

## Recommended Starting Point on Your Machine

For an Apple Silicon laptop, start with:

- Base model: `Qwen/Qwen2.5-Coder-3B-Instruct`
- Fine-tuning: LoRA
- Evaluation: loss first, render pass rate as guardrail
- Dataset strategy: curated seed cases first, synthetic expansion second

On a 36 GB M4 Max, a 3B model is the right baseline for fast A/B iteration. Move to a larger code model only after the dataset and eval loop are stable.

## Mac Setup

Requirements:

- Apple Silicon Mac
- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Homebrew packages for Manim rendering

```bash
brew install pkg-config cairo pango ffmpeg
uv sync
```

## Quick Start

Refresh the official-docs seed set and merge it with the local hand-written cases:

```bash
uv run python -m mac_pipeline.cli import-doc-seeds \
  --manifest data/manim_docs_sources.json \
  --output data/manim_docs_seed_cases.jsonl

uv run python -m mac_pipeline.cli merge-case-files \
  --inputs data/manim_seed_cases.json data/manim_docs_seed_cases.jsonl \
  --output data/manim_bootstrap_cases.jsonl
```

Merge the converted ML and chemistry gold cases into the active bootstrap dataset:

```bash
uv run python -m mac_pipeline.cli merge-case-files \
  --inputs data/manim_seed_cases.json data/manim_docs_seed_cases.jsonl data/manim_converted_cases.jsonl data/manim_converted_cases_round2.jsonl \
  --output data/manim_full_bootstrap_cases_v2.jsonl
```

Import external example repositories and split them into plain-Manim candidates versus custom-library conversion candidates:

```bash
uv run python -m mac_pipeline.cli import-repo-examples \
  --manifest data/manim_repo_sources.json \
  --output data/manim_repo_raw_candidates.jsonl \
  --metadata artifacts/repo_ingest/metadata.json

uv run python -m mac_pipeline.cli filter-repo-candidates \
  --input data/manim_repo_raw_candidates.jsonl \
  --plain-output data/manim_repo_plain_candidates.jsonl \
  --custom-output data/manim_repo_custom_candidates.jsonl \
  --summary artifacts/repo_ingest/filter_summary.json
```

Build the train/valid/test splits from the seed dataset:

```bash
uv run python -m mac_pipeline.cli build-dataset \
  --config configs/m4_max_qwen25coder_3b.json
```

Run one baseline fine-tuning experiment end-to-end:

```bash
uv run python -m mac_pipeline.cli run \
  --config configs/m4_max_qwen25coder_3b.json
```

Re-run evaluation only after you already have adapter weights:

```bash
uv run python -m mac_pipeline.cli eval \
  --config configs/m4_max_qwen25coder_3b.json
```

Compare two evaluation outputs:

```bash
uv run python -m mac_pipeline.cli compare \
  --config configs/m4_max_qwen25coder_3b.json \
  --baseline artifacts/evals/baseline.json \
  --candidate artifacts/evals/candidate.json \
  --output artifacts/evals/ab_result.json
```

Create a figure comparing the base model and the fine-tuned adapter:

```bash
uv run python -m mac_pipeline.cli plot-comparison \
  --baseline artifacts/evals/m4-max-qwen25coder-3b-base.json \
  --finetuned artifacts/evals/m4-max-qwen25coder-3b.json \
  --output docs/figures/base-vs-finetuned.png
```

## Project Layout

```text
mac_pipeline/                 MLX fine-tuning, evaluation, and A/B tooling
configs/m4_max_qwen25coder_3b.json
                              Baseline experiment config for Apple Silicon
data/manim_seed_cases.json    Hand-written starter dataset
data/manim_docs_sources.json  Official docs example manifest
data/manim_docs_seed_cases.jsonl
                              Imported official docs examples
data/manim_bootstrap_cases.jsonl
                              Combined bootstrap dataset used by the config
data/manim_converted_cases.jsonl
                              Plain-Manim ML and chemistry conversions inspired by MIT repos
data/manim_full_bootstrap_cases.jsonl
                              Active merged dataset used by the config
data/manim_repo_sources.json  GitHub repo source manifest
data/manim_repo_raw_candidates.jsonl
                              Imported repo-derived scene candidates
data/manim_repo_plain_candidates.jsonl
                              Plain-Manim repo candidates that are near-trainable
data/manim_repo_custom_candidates.jsonl
                              Repo candidates that require custom-library conversion
program.md                    Autoresearch loop instructions for the agent
results.tsv                   Run log for keep / discard decisions
prepare.py, train.py          Legacy upstream CUDA baseline
```

## Dataset Guidance

The bootstrap dataset is intentionally small. It is there to bootstrap the loop, not to finish the job.

Good next expansions:

1. Add your own known-good Manim scenes first.
2. Import more official Manim examples through `data/manim_docs_sources.json`.
3. Create prompt variants around the same concept without changing correctness criteria.
4. Add hard evaluation-only prompts that never enter training.
5. Keep prompts concrete: scene objective, visual constraints, and required constructs.
6. Prefer short, correct, idiomatic scenes over flashy long ones.

Current external-source findings:

- `ManimML` and `manim-Chemistry` are both MIT-licensed.
- The current repo import produced `46` scene candidates total.
- Only `1` candidate was plain Manim without custom-library dependencies.
- The remaining `45` candidates are still valuable as concept seeds, but they should be reviewed or converted before joining the core training set.
- Two manual conversion passes added `14` new plain-Manim gold cases, all verified with real low-quality renders.
- The active merged dataset is now `28` cases total with a `21 / 3 / 4` train / valid / test split.

## Using the Karpathy Loop

Point your coding agent at `program.md`. The adapted loop treats:

- held-out loss as the primary fast metric
- render success and case score as regression checks
- config / dataset / prompt edits as the main levers, not architecture hacking in `train.py`

## Current Comparison

Below is the current direct comparison on the 4-case held-out split after expanding the converted gold set.

![Base vs Fine-tuned model comparison](docs/figures/base-vs-finetuned.png)

Observed results:

| Metric | Base model | Fine-tuned |
| --- | ---: | ---: |
| Syntax success rate | 1.000 | 1.000 |
| Render success rate | 0.500 | 0.000 |
| Mean case score | 0.725 | 0.544 |
| Test loss | n/a | 1.441 |
| Test perplexity | n/a | 4.225 |

Interpretation:

- The expanded dataset improved training stability, but the final checkpoint still overfit and regressed against the base model on held-out render success and case score.
- The best validation loss in the training log appeared early, so the next loop should add checkpoint selection or early stopping rather than always taking the last adapter snapshot.
- The base-model loss is marked `n/a` because `mlx_lm lora --test` requires an adapter path; the base comparison here is generation-based.

## Notes

- `mlx-lm` and `manim` install on current Apple Silicon Python 3.13, but Manim still depends on the Homebrew system packages above.
- The default config now trains in 25-step chunks, saves numbered adapter checkpoints every chunk, and restores the best validation checkpoint after early stopping.
- All adapters and eval artifacts live under `artifacts/`, which is gitignored and will not be pushed to GitHub.
- If render checks are too slow early on, set `"run_render": false` in the config and use loss + static checks during inner-loop iteration.
- Once the dataset gets large enough, keep a strict held-out test set and avoid training on it indirectly through manual prompt tuning.

## License

MIT
