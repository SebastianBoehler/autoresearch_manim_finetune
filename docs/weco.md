# Weco Integration

Weco fits this repo best as an observability layer around the existing MLX fine-tuning loop.

- Use `weco observe` when you want the hosted run tree, code diffs, and metric charts for your own training and evaluation loop.
- Treat `weco run` as a secondary workflow for narrower experiments, such as letting Weco mutate a config or prompt file. It is less natural for the main loop because every evaluation can trigger a full fine-tune.

## Platform Split

The current Weco split is:

- Open-source: the `weco` CLI and the separate `AIDE ML` reference implementation.
- Hosted: the Weco dashboard and production optimization platform.
- BYOK: supported through `weco run --api-key provider=KEY`, but you still use the hosted Weco account layer for runs, credits, and the dashboard.

So the answer to "can we self-host the dashboard because the site says open source?" is: not from the public docs and repos I found. The open-source path is the CLI and AIDE ML, not the Weco dashboard itself.

## Install

The repo now keeps Weco as an optional extra so the core Manim pipeline stays lean:

```bash
uv sync --extra weco
```

Then authenticate the CLI:

```bash
uv run weco login
```

## Fastest Real Trial

This repo now includes a dedicated Weco target file plus a launcher, so you can run a real short-horizon Manim optimization immediately:

```bash
uv run python scripts/weco_manim_run.py \
  --steps 6 \
  --save-logs
```

That uses your Weco login session and credits. This is the least fragile way to confirm the integration works.

If you want BYOK instead, make sure the provider env var is actually set before passing it through:

```bash
echo "$OPENAI_API_KEY"

uv run python scripts/weco_manim_run.py \
  --steps 6 \
  --save-logs \
  --api-key openai=$OPENAI_API_KEY
```

If `echo "$OPENAI_API_KEY"` prints nothing, omit `--api-key` or export the key first.

What this does:

- Weco edits [`weco_targets/manim_lora_trial.py`](../weco_targets/manim_lora_trial.py), not your main config.
- [`scripts/weco_manim_eval.py`](../scripts/weco_manim_eval.py) materializes those edits into a real runtime config under `artifacts/weco/`.
- The existing `mac_pipeline.cli run` command trains and evaluates the candidate.
- The eval script prints `mean_case_score` plus the secondary guardrail metrics for Weco to read.

Use `--dry-run` first if you want to inspect the exact command:

```bash
uv run python scripts/weco_manim_run.py --dry-run
```

## Primary Metric

The default Weco primary metric in this repo is `mean_case_score`.

- It already reflects Manim-generation quality in [`mac_pipeline/eval.py`](../mac_pipeline/eval.py).
- It is faster to reason about than raw `test_loss` when you care about runnable scenes, snippet adherence, and render success.
- The helper scripts still log `render_success_rate`, `syntax_success_rate`, `test_loss`, and `test_perplexity` so you can catch reward hacking.

## Observe Workflow

1. Authenticate with Weco:

```bash
weco login
```

2. Initialize an observed run. By default the helper snapshots the config plus the core train/eval files:

```bash
WECO_RUN_ID=$(uv run python scripts/weco_observe.py init \
  --config configs/m4_max_qwen25coder_3b.json \
  --name "manim-lora-sweep" \
  --metric mean_case_score \
  --goal max)
```

3. Log the base model as step `0`:

```bash
uv run python -m mac_pipeline.cli eval \
  --config configs/m4_max_qwen25coder_3b.json \
  --base-only \
  --output artifacts/evals/m4-max-qwen25coder-3b-base-weco.json

uv run python scripts/weco_observe.py log \
  --run-id "$WECO_RUN_ID" \
  --step 0 \
  --eval artifacts/evals/m4-max-qwen25coder-3b-base-weco.json \
  --description "Base Qwen2.5-Coder-3B-Instruct"
```

4. Train and evaluate a candidate, then log it as the next step:

```bash
uv run python -m mac_pipeline.cli run \
  --config configs/m4_max_qwen25coder_3b.json

uv run python scripts/weco_observe.py log \
  --run-id "$WECO_RUN_ID" \
  --step 1 \
  --eval artifacts/evals/m4-max-qwen25coder-3b.json \
  --description "LoRA baseline on canonical dataset"
```

5. Open the Weco dashboard to inspect the metric curve, branching history, and tracked file diffs.

## Branching And Failed Runs

When a candidate fails or you intentionally branch from an earlier good step, log that explicitly:

```bash
uv run python scripts/weco_observe.py log \
  --run-id "$WECO_RUN_ID" \
  --step 2 \
  --status failed \
  --description "Higher render budget caused timeout regressions" \
  --metric mean_case_score=0 \
  --metric render_success_rate=0

uv run python scripts/weco_observe.py log \
  --run-id "$WECO_RUN_ID" \
  --step 3 \
  --parent-step 1 \
  --eval artifacts/evals/m4-max-qwen25coder-3b-alt.json \
  --description "Branched from step 1 with longform-heavy dataset mix"
```

## Repo Helpers

### `scripts/weco_observe.py`

Thin wrapper around `weco observe init` and `weco observe log`.

- `init` creates a run and snapshots the tracked files.
- `log` reads metrics from an eval JSON and forwards them to Weco.
- `--dry-run` prints the exact `weco` CLI command for verification.

### `scripts/weco_eval.py`

Prints repo metrics in Weco-friendly `metric: value` format.

- Point it at an existing eval JSON:

```bash
uv run python scripts/weco_eval.py \
  --eval artifacts/evals/m4-max-qwen25coder-3b.json
```

- Or have it run the repo evaluation command first:

```bash
uv run python scripts/weco_eval.py \
  --config configs/m4_max_qwen25coder_3b.json \
  --mode eval \
  --require-metric mean_case_score
```

### `scripts/weco_manim_run.py`

Launches a real repo-native Weco optimization with the right defaults already wired in.

- Default editable file: [`weco_targets/manim_lora_trial.py`](../weco_targets/manim_lora_trial.py)
- Default evaluation command: [`scripts/weco_manim_eval.py`](../scripts/weco_manim_eval.py)
- Default metric: `mean_case_score`
- Default goal: `maximize`

## Experimental `weco run` Path

If you want Weco to mutate a single file directly, use the repo-native target above rather than pointing Weco at the full training pipeline or a large JSON config. Each step still retrains an adapter, so it is materially slower than standard Weco code-optimization examples, but the blast radius is controlled.
