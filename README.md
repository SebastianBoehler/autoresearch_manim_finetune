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

## Using the Karpathy Loop

Point your coding agent at `program.md`. The adapted loop treats:

- held-out loss as the primary fast metric
- render success and case score as regression checks
- config / dataset / prompt edits as the main levers, not architecture hacking in `train.py`

## Notes

- `mlx-lm` and `manim` install on current Apple Silicon Python 3.13, but Manim still depends on the Homebrew system packages above.
- If render checks are too slow early on, set `"run_render": false` in the config and use loss + static checks during inner-loop iteration.
- Once the dataset gets large enough, keep a strict held-out test set and avoid training on it indirectly through manual prompt tuning.

## License

MIT
