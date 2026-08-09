# Raw Demo Performance Iteration

Date: 2026-04-25

## Baseline Correction

After disabling default code repair, the old dynamic-stop demo artifact was rescored against raw generated code:

- Seed 42 dynamic-stop baseline raw rescore: syntax 1.00, render 0.50, quality 1.00, production 0.50, mean score 0.7125.
- Main raw render failures: unsupported bare `opacity=` constructor kwargs and point/coordinate misuse with `SurroundingRectangle`.
- Latency for seed42 remains the speed reference: mean wall 8.02s, p95 9.28s, mean output 397.75 tokens.

## Rejected Experiments

- Prompt-only `manim-demo-safe-fast` skill: regressed to render 0.25 and mean score 0.6375.
- Bare-token suppression for `opacity`: regressed to render 0.25 because the model substituted other unsupported API such as `alpha`, `numbers_with_labels`, and `add_numbers_to_tips`.
- API-safety microrefresh adapter: trained cleanly from current LoRA and improved validation loss from 0.668 to 0.616, but held-out raw demo score regressed to render 0.25 and mean score 0.625. Do not promote.
- Multi-adapter router: current adapter covers attention/fraction, chat-EOS probe covers confidence, but neither solved binary search; the full router run hit a Metal GPU timeout when switching later adapters.

## Current Best Raw Profile

Config: `configs/local_mlx_speculative_dynamic_stop_seed7_fast_prod_benchmark.json`

- Same current Qwen 3B LoRA, same 0.5B speculative draft, no code repair.
- Changes: `seed=7` and `dynamic_stop_target_ratio=0.55`.
- Raw 4-case demo benchmark: syntax 1.00, render 0.75, quality 0.75, production 0.75, mean score 0.7875.
- Latency: mean wall 13.29s, median 13.25s, p95 16.58s, mean output 449.75 tokens, mean end-to-end throughput 33.29 tok/s.
- Warm in-process latency after one warmup case: mean wall 8.56s, median 8.51s, p95 11.13s, mean output 449.75 tokens, mean end-to-end throughput 52.10 tok/s, mean peak memory 6.80 GB.

Decision: use seed7-fast-prod as the best current raw demo profile when production success matters more than absolute fastest response. Keep seed42 dynamic-stop as the fastest profile but mark it lower reliability under raw evaluation.

## Draft Token Sweep

Warm latency-only sweep on the current seed7-fast-prod profile:

- Draft tokens 2: mean wall 9.15s, p95 10.24s, mean 47.95 end-to-end tok/s.
- Draft tokens 3: mean wall 8.36s, p95 10.83s, mean 53.36 end-to-end tok/s.
- Draft tokens 4: mean wall 7.20s, p95 10.13s, mean 54.40 end-to-end tok/s.
- Draft tokens 5: mean wall 7.79s, p95 9.07s, mean 52.64 end-to-end tok/s.

Render validation rejects the apparent draft-token speedups. Draft tokens 4 scored syntax 1.00, render 0.00, production 0.00, mean 0.5625. Draft tokens 5 scored syntax 1.00, render 0.00, production 0.00, mean 0.5750. Keep `num_draft_tokens=3` as the current production setting despite slightly slower latency.

## Remaining Blocker

`binary_search_interval_shrink` still emits unsupported `opacity=` and fails render. This should be solved by model/data behavior around `Rectangle(..., fill_opacity=...)` bands, not evaluator repair.

## Broad Smoke Check

Heartbeat follow-up on the first eight broad held-out cases:

- Seed42 broad first-8: syntax 0.75, render 0.50, quality 0.75, production 0.375, mean score 0.6565.
- Seed7-fast-prod broad first-8: syntax 1.00, render 0.375, quality 1.00, production 0.375, mean score 0.7422.

Interpretation: seed7-fast-prod improves syntax and mean score on broad smoke, but does not improve broad production readiness. Keep it scoped to the learning-app demo profile until a full broad run or data fix improves render reliability.

Broad render failures in the smoke were unsupported Matrix background kwargs, incorrect numeric constructor/value arguments, invented coordinate helpers, a Riemann timeout, and an out-of-range list access. These are model/API knowledge failures, not cases to hide with default evaluator repair.

## Full Broad Run

The full 23-case broad render benchmark confirmed the smoke result:

- Seed42 broad full: syntax 0.8261, render 0.5263, quality 0.7826, production 0.4348, mean score 0.6911.
- Seed7-fast-prod broad full: syntax 0.8696, render 0.5000, quality 0.8261, production 0.4348, mean score 0.6936.

Seed7 fixed some syntax/render failures (`math_brace_interval_measurement`, `continuousmotion`, `supply_demand_equilibrium_panel_story`, `ml_activation_comparison_panel`) but regressed several previously renderable finance/chemistry/3D cases. Conclusion remains unchanged: seed7-fast-prod is a demo-profile improvement, not a broad-profile promotion.

An offline per-case seed oracle across seed42 and seed7 would score syntax 0.9565, render 0.6364, quality 0.9130, production 0.6087, and mean score 0.7861. This suggests seed routing has real upside, but production use would need a cheap prompt/category router because on-demand sequential generation plus render selection would exceed the latency budget.

## Offline Router Analysis

Artifact: `artifacts/benchmarks/offline-seed-router-analysis/seed42-vs-seed7-router.json`

Repro command:

```bash
.venv/bin/python scripts/analyze_seed_router.py \
  --dataset artifacts/datasets/m4-max-qwen25coder-3b/test.jsonl \
  --baseline artifacts/benchmarks/local-mlx-speculative-broad-render/finetuned-qwen25coder-3b-speculative-dynamic-stop.json \
  --candidate artifacts/benchmarks/local-mlx-speculative-broad-render-seed7-fast-prod/finetuned-qwen25coder-3b-seed7-fast-prod.json \
  --output artifacts/benchmarks/offline-seed-router-analysis/seed42-vs-seed7-router.json
```

Greedy category routing selected seed7 for `tag:math`, `tag:source:repo`, `tag:ml`, and `tag:review-guided`; otherwise it kept seed42. On this 23-case held-out set, that reaches syntax 0.9565, render 0.6364, quality 0.9130, production 0.6087, and mean score 0.7795. The exact per-case oracle mean is 0.7861.

This is a routing hypothesis, not a promoted production policy. Leave-one-out stress testing regresses to production 0.3913 and mean score 0.6757, so the router is not robust enough to ship. The next useful experiment is fresh generation on new category-balanced prompts, without second-pass repair or render-based selection.

## Targeted Failure Refresh

Artifacts:

- `data/manim_raw_failure_refresh.jsonl`: 8 validated raw-failure pattern samples.
- `data/manim_demo_failure_refresh.jsonl`: 3 validated direct demo-failure samples.
- `artifacts/evals/raw_failure_refresh_selfcheck.json`: 8/8 syntax, render, quality, production.
- `artifacts/evals/demo_failure_refresh_selfcheck.json`: 3/3 syntax, render, quality, production.
- `artifacts/adapters/m4-max-qwen25coder-3b-raw-failure-refresh`: 25-step continuation refresh.
- `artifacts/adapters/m4-max-qwen25coder-3b-targeted-refresh-full`: full refresh from base, early-stopped at step 125 and restored best step 50, val loss 0.648.

Demo-profile benchmark (`configs/local_mlx_speculative_dynamic_stop_raw_failure_refresh_benchmark.json`):

- Current adapter: render 0.75, quality 0.75, production 0.75, mean 0.7875.
- 25-step continuation refresh: render 0.25, production 0.25, mean 0.6250. Do not promote.
- Full targeted refresh: render 0.75, quality 1.00, production 0.75, mean 0.7500. Do not promote because mean regressed and it introduced `ORANGE_D` on the attention case.
- Lower-LR stable refresh: best checkpoint step 75, val loss 0.626, but demo syntax 0.75, production 0.50, mean 0.6107. Do not promote; validation loss did not predict raw generation reliability.

Fresh category-balanced eval (`configs/local_mlx_speculative_category_balanced_fresh_benchmark.json`):

- Current adapter: syntax 0.875, render 0.2857, quality 0.75, production 0.25, mean 0.6674.
- Full targeted refresh: syntax 0.875, render 0.4286, quality 0.875, production 0.375, mean 0.6446.

Interpretation: targeted training is moving some raw API behavior in the right direction, but not cleanly enough to replace the current demo adapter. Next failure targets are undefined color constants (`ORANGE_D`), `Rational` without import, invented `NumberLine.background_rectangle`, `Graph(..., x_range=...)`, matrix entry indexing, `Axes.get_vertical_line(..., color=...)`, repeated 3D surface kwargs, and syntax truncation.

Second-wave API-error samples in `data/manim_api_error_refresh.jsonl` self-check at 8/8 production, but the lower-LR full refresh still regressed the demo. Keep the samples for future full-data training, but do not promote either targeted adapter from this run.

## Small MLX Coder Probe

Latency-only 256-token probe (`configs/local_mlx_small_coder_latency_benchmark.json`):

- Qwen2.5-Coder 0.5B 4-bit: mean wall 0.784s, generation 374 tok/s.
- Qwen2.5-Coder 1.5B 4-bit: mean wall 1.143s, generation 253 tok/s.
- Fine-tuned Qwen2.5-Coder 1.5B short curriculum: mean wall 1.812s, generation 153 tok/s.
- Fine-tuned Qwen2.5-Coder 1.5B targeted: mean wall 1.827s, generation 152 tok/s.
- Current fine-tuned Qwen2.5-Coder 3B: mean wall 6.567s, generation 40 tok/s.

Two-case render probe (`configs/local_mlx_small_coder_taste_benchmark.json`):

- Current 3B adapter: syntax 1.00, render 0.50, mean 0.700.
- Raw 0.5B 4-bit: syntax 0.50, render 0.00, mean 0.296.
- Raw 1.5B 4-bit: syntax 0.00, no render attempts, mean 0.143.
- Fine-tuned 1.5B targeted: syntax 0.00, no render attempts, mean 0.179.
- Fine-tuned 1.5B short curriculum: syntax 0.00, no render attempts, mean 0.179.

Conclusion: small MLX coders have the desired speed envelope, but current 1.5B fine-tuning is not yet usable. The 1.5B output repeats and truncates, so the next small-model experiment should focus on EOS/repetition behavior and shorter completion curriculum before render quality.

Follow-up: a short-duration 1.5B curriculum trained very fast, but did not improve the two-case syntax probe. This points away from quick small-model LoRA and toward either stronger base models or explicit completion-control work before quality tuning.
