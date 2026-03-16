# autoresearch for Manim on Apple Silicon

This repo is now a config-driven autoresearch loop for **MLX LoRA fine-tuning of an open-source coding model on Manim tasks**.

## Setup

Before the first run:

1. Read the in-scope files:
   - `README.md`
   - `configs/m4_max_qwen25coder_3b.json`
   - `data/manim_seed_cases.json`
   - `mac_pipeline/`
2. Verify Apple Silicon dependencies are installed:
   - `uv sync`
   - `brew install pkg-config cairo pango ffmpeg`
3. Verify `results.tsv` exists.
4. Build the dataset if the split files are missing:
   - `uv run python -m mac_pipeline.cli build-dataset --config configs/m4_max_qwen25coder_3b.json`
5. Run one baseline experiment before changing anything:
   - `uv run python -m mac_pipeline.cli run --config configs/m4_max_qwen25coder_3b.json`

## Objective

The primary fast metric is **held-out `test_loss`** on a curated Manim dataset.

Secondary regression guards:

- `render_success_rate`
- `syntax_success_rate`
- `mean_case_score`

Lower loss is better, but do not accept a candidate that meaningfully improves loss while breaking renderability.

## Main Levers

Prefer changing:

- dataset quality
- prompt wording in dataset examples
- train / eval split composition
- LoRA settings in `configs/*.json`
- generation settings in `configs/*.json`
- scoring thresholds in the evaluation config

Avoid touching the legacy CUDA files unless the human explicitly asks.

## Logging

Every completed run appends to `results.tsv` with:

```
run_name	base_model	test_loss	test_perplexity	syntax_success_rate	render_success_rate	mean_case_score	adapter_path	eval_output_path
```

The evaluation JSON in `artifacts/evals/` is the detailed record.

## Experiment Loop

LOOP:

1. Inspect current config and prior eval outputs.
2. Choose exactly one clear hypothesis.
3. Edit only what supports that hypothesis.
4. Run:
   - `uv run python -m mac_pipeline.cli run --config <config>`
5. Compare the new eval JSON against the previous baseline:
   - `uv run python -m mac_pipeline.cli compare --config <config> --baseline <old_eval> --candidate <new_eval> --output <ab_json>`
6. Keep the change only if:
   - loss improved enough to matter, and
   - render success did not regress beyond the configured threshold, or
   - loss is tied and generation quality improved
7. Record the reasoning in git history and continue.

## Simplicity Rule

If two changes perform similarly, keep the simpler one. Small loss gains are not worth brittle evaluation hacks or noisy data.

## Data Rule

Do not chase loss on a weak dataset. If the eval set is too small or too synthetic, improve the dataset before trusting the metric.
