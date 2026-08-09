# Learning App Quality Review

Date: 2026-04-23

## Product Constraint

For an on-demand learning app, a 15 second generation budget is acceptable. The local inference work therefore should optimize for predictable sub-15s responses and high educational taste, not just maximum tokens per second.

## Current Dataset Observations

- Canonical dataset size: 178 records.
- Held-out split size: 21 records.
- The corpus has useful Manim API breadth, especially `Axes`, `ValueTracker`, `NumberPlane`, `Surface`, `BarChart`, `ZoomedScene`, and `ThreeDScene`.
- Duration tags skew toward long scenes: 74 records tagged `duration:30s`, 30 tagged `duration:20s`, 48 tagged `duration:10s`, and no explicit `duration:15s` tag.
- Many records teach object placement and API usage, but fewer teach compact explanation design: staged reveals, visual hierarchy, tasteful color restraint, and one clear learning claim.
- Common pattern risk: title + objects + labels + wait. This is renderable, but it does not consistently train the model to produce polished learning-app scenes.
- The dataset has no files over the project LOC limit, but the median completion is only 26 LOC. That is good for speed, but some samples are too sparse to teach pacing or taste.

## Taste Targets

New learning-app samples should prefer:

- One concept per scene with a visible before/after or question/answer arc.
- 12-15 second pacing with 3-5 intentional beats.
- A stable layout: title, main visual, caption or takeaway, no cramped corner labels.
- Reusable visual grammar: muted base objects, one accent color per active idea, clear highlight boxes.
- Low render risk unless the sample intentionally teaches a high-risk Manim feature.
- Plain Manim Community Edition with no external assets.

## Coverage Gaps To Fill

- `duration:15s` scenes aimed at on-demand educational generation.
- Learning-app micro-explanations for foundational concepts, not only broad demos.
- Explicit taste patterns: progressive disclosure, fixed takeaway captions, legends, and clean comparisons.
- More `NumberLine`, `BraceBetweenPoints`, `BarChart`, `Matrix`, `Code`, and split-panel examples with restrained composition.
- Quality-oriented negative examples should remain out of training; the canonical set should only receive rendered, reviewed positive samples.

## Proposed Sample Batch

Batch goal: stage compact, tasteful 15s learning-app examples that teach one concept clearly and render quickly.

Target size: 12 candidate records.

Complexification fraction: 25%.

Reject upfront:

- Decorative complexity that does not improve the explanation.
- Dense text paragraphs.
- Three-dimensional scenes for this batch.
- Long multi-topic narratives.
- Custom assets or non-plain-Manim dependencies.

## Candidate Specs

1. `fraction_unit_interval_reveal`
Prompt: Create a 15-second Manim scene that explains why `3/4` means three equal parts of one whole. Show a clean NumberLine from 0 to 1, four equal tick intervals, three highlighted segments, a moving dot landing at `3/4`, and a final takeaway caption.
Core constructs: `NumberLine`, `BraceBetweenPoints`, `Dot`, `MathTex`, `SurroundingRectangle`.
Taste goal: calm number-line teaching pattern with one accent color.

2. `derivative_tangent_zoom`
Prompt: Create a 15-second Manim scene that explains a derivative as the slope of a tangent. Plot a smooth curve on axes, move a point along the curve with a short tangent line, show the slope label updating once, and finish with a boxed caption saying the derivative is local rate of change.
Core constructs: `Axes`, `.plot`, `ValueTracker`, `always_redraw`, `Line`, `DecimalNumber`.
Taste goal: dynamic idea with minimal moving parts.

3. `binary_search_interval_shrink`
Prompt: Create a 15-second Manim scene that visualizes binary search on a sorted number line. Show the search interval as a translucent band, test the midpoint, shrink the interval twice, and end with the target found.
Core constructs: `NumberLine`, `Rectangle`, `Dot`, `Arrow`, `ReplacementTransform`, `MathTex`.
Taste goal: algorithm as spatial narrowing, not code clutter.

4. `bayes_prior_to_posterior_bars`
Prompt: Create a 15-second Manim scene that explains a Bayesian update from prior to posterior. Show three small bar charts labeled prior, evidence, and posterior, animate one hypothesis gaining weight, and add a concise takeaway caption.
Core constructs: `BarChart`, `MathTex`, `Arrow`, `SurroundingRectangle`, `ReplacementTransform`.
Taste goal: statistical intuition through a clean left-to-right flow.

5. `attention_weighted_average_micro`
Prompt: Create a 15-second Manim scene that explains attention as a weighted average. Show three value vectors, three attention weights, copy the strongest weight into a highlighted output token, and keep a small legend visible.
Core constructs: `Matrix`, `MathTex`, `Arrow`, `TransformFromCopy`, `SurroundingRectangle`.
Taste goal: ML concept with fewer objects than the existing long attention traces.

6. `gradient_descent_step_size_compare`
Prompt: Create a 15-second Manim scene comparing small and large gradient descent step sizes on the same contour map. Use two colored paths, moving dots, and a final caption contrasting slow progress with overshooting.
Core constructs: `NumberPlane`, `Ellipse`, `VMobject`, `MoveAlongPath`, `Dot`.
Taste goal: comparison scene with visual tradeoff.

7. `memory_retrieval_cue_path`
Prompt: Create a 15-second Manim scene explaining retrieval cues. Show a cue node lighting up, a path activating through two memory nodes, and the correct memory card surfacing at the end.
Core constructs: `Circle`, `Line`, `VGroup`, `LaggedStart`, `SurroundingRectangle`.
Taste goal: neuroscience/learning domain coverage with simple geometry.

8. `supply_demand_price_shift`
Prompt: Create a 15-second Manim scene showing how demand shift changes equilibrium price. Plot supply and demand lines, highlight the old intersection, shift demand right, and mark the new higher price.
Core constructs: `Axes`, `.plot_line_graph` or `.plot`, `Dot`, `DashedLine`, `Arrow`.
Taste goal: economics explanation with clear before/after.

9. `matrix_transform_grid_shear`
Prompt: Create a 15-second Manim scene showing a matrix as a grid transformation. Display a square grid, shear it smoothly, and keep the matrix label fixed next to the transformed basis vectors.
Core constructs: `NumberPlane`, `Matrix`, `Arrow`, `Transform`, `MathTex`.
Taste goal: linear algebra without excessive notation.

10. `chemical_equilibrium_balance`
Prompt: Create a 15-second Manim scene explaining dynamic chemical equilibrium. Show forward and reverse arrows between reactants and products, animate both arrows at different speeds, then settle into equal-rate balance.
Core constructs: `MathTex`, `Arrow`, `ValueTracker`, `always_redraw`, `DecimalNumber`.
Taste goal: chemistry concept with motion carrying the explanation.

11. `recursion_stack_unwind`
Prompt: Create a 15-second Manim scene showing a recursive call stack building and unwinding. Stack three function cards, highlight the base case, then pop cards back with return values.
Core constructs: `Code`, `RoundedRectangle`, `VGroup`, `Arrow`, `ReplacementTransform`.
Taste goal: programming concept with strong temporal structure.

12. `confidence_interval_band`
Prompt: Create a 15-second Manim scene explaining a confidence interval as uncertainty around an estimate. Show a dot estimate on a number line, expand a translucent interval band, compare narrow and wide intervals, and end with a plain-language caption.
Core constructs: `NumberLine`, `Dot`, `Rectangle`, `BraceBetweenPoints`, `Text`.
Taste goal: statistics scene that avoids formula overload.

## Recommended Next Batch

Start with six low-risk records:

- `fraction_unit_interval_reveal`
- `derivative_tangent_zoom`
- `binary_search_interval_shrink`
- `bayes_prior_to_posterior_bars`
- `attention_weighted_average_micro`
- `confidence_interval_band`

These fit the 15s product target, cover underrepresented learning-app pacing, and should render quickly enough for candidate review.

## Round 12 Implementation Checkpoint

- Staged the six recommended low-risk records in `data/manim_review_candidates_round12_learning_app_taste.json`.
- Audited the shard with zero schema errors and zero warnings.
- Rendered all six candidates at exactly 15 seconds.
- Iterated visual defects before promotion: derivative updater timeout, fraction label crowding, Bayes caption staging, and attention label contrast.
- Rated all six as approved, with manual quality scores from 4.0 to 4.5.
- Promoted all six into `data/manim_review_promoted.jsonl` and rebuilt `data/manim_dataset.jsonl`.
- Rebuilt the main Qwen 3B dataset split: 184 canonical records, 138 train, 23 validation, 23 test.
- Added a focused learning-app taste config so local models can be compared on this product target without waiting for the full held-out benchmark.

## MLX Candidate Shortlist

The current Hugging Face `library=mlx` trending list makes the Prism ML Ternary Bonsai checkpoints the best next local candidates for this repo's `mlx_lm` path. They advertise native MLX quickstarts and very small packed sizes: 1.7B at 0.45 GiB, 4B at 1.05 GiB, and 8B at 2.15 GiB.

The `mlx-community/Qwen3.5-9B-MLX-4bit` checkpoint is interesting, but it is an `mlx_vlm` conversion for image-text-to-text rather than an `mlx_lm` text-generation checkpoint. Keep it out of the current benchmark path until the repo has explicit `mlx_vlm` support.

Added two configs:

- `configs/local_mlx_trending_latency_benchmark.json` for one-case speed smoke tests across Qwen, Qwen LoRA, Bonsai 1-bit, and the three Ternary Bonsai variants.
- `configs/local_mlx_trending_taste_benchmark.json` for a two-case render-quality smoke test of the most plausible small local competitors.
- `configs/local_mlx_ternary_1_7b_taste_benchmark.json` for a fast quality sanity check when only the smallest Ternary Bonsai checkpoint has been downloaded.

## Round 12 Model Checkpoint

Focused 4-case learning-app taste benchmark after deterministic Manim repair hardening:

- Qwen 2.5 Coder 3B LoRA: score 0.875, syntax 1.00, render 1.00.
- Qwen 2.5 Coder 3B base: score 0.688, syntax 1.00, render 0.50.
- Bonsai 8B MLX 1-bit: score 0.436, syntax 0.75, render 0.00.

One-case 256-token latency smoke on the same held-out prompt:

- Ternary Bonsai 1.7B 2-bit: 1.032s wall, 0.148s TTFT, 248.0 end-to-end tok/s.
- Qwen 2.5 Coder 3B LoRA: 6.084s wall, 0.251s TTFT, 42.1 end-to-end tok/s.
- Qwen 2.5 Coder 3B base: 6.475s wall, 1.492s TTFT, 39.5 end-to-end tok/s.

Two-case quality smoke:

- Qwen 2.5 Coder 3B LoRA: score 0.850, syntax 1.00, render 1.00.
- Ternary Bonsai 1.7B 2-bit: score 0.261, syntax 0.50, render 0.00.

Decision at the time: use Qwen 3B LoRA as the current local generator candidate. Treat Ternary Bonsai 1.7B as a possible fast draft/spec model, not as the final code generator without fine-tuning. Repair-assisted scores are diagnostics and should not be mixed with raw model-quality evaluation.

## Overnight Round 12 Results

The isolated round12 Qwen 3B LoRA trained successfully without overwriting the current adapter, but it is not a promotion candidate.

- Round12 Qwen 3B LoRA full eval: 23 cases, score 0.574, syntax 0.609, render 0.643, test loss 0.605, perplexity 1.832.
- Round12 best checkpoint: step 50, validation loss 0.630.
- Focused learning-app taste benchmark: current Qwen LoRA still wins with score 0.875, syntax 1.00, render 1.00.
- Focused learning-app taste benchmark: round12 Qwen LoRA collapsed to score 0.232, syntax 0.00, render not attempted.
- Failure mode: round12 generations frequently produced unclosed parentheses, invalid argument ordering, or incomplete code, so lower loss did not transfer to better on-demand Manim generation.

Trending MLX Bonsai continuation:

- Ternary Bonsai 4B 2-bit: 1.583s wall, 0.180s TTFT, 183.3 decode tok/s, 161.7 end-to-end tok/s for 256 tokens.
- Ternary Bonsai 8B 2-bit: 2.409s wall, 0.248s TTFT, 119.0 decode tok/s for 256 tokens.
- Two-case taste benchmark: Qwen LoRA scored 0.850 with 100% render; Ternary Bonsai 8B scored 0.525 with 0% render; Ternary Bonsai 4B scored 0.346 with 0% render.

Decision: do not promote round12 LoRA. Continue with current Qwen LoRA as the generator and focus next on generation-length/temperature sweeps plus repair/verifier improvements.

## Quality Speed Sweep

Current Qwen LoRA max-token sweep on the four focused learning-app taste prompts:

- 700 tokens: score 0.705, syntax 0.75, render 1.00 for syntax-valid cases, 15.43s wall on the latency prompt.
- 900 tokens: score 0.705, syntax 0.75, render 1.00 for syntax-valid cases, 19.86s wall.
- 1100 tokens: score 0.705, syntax 0.75, render 1.00 for syntax-valid cases, 24.27s wall.
- 1400 tokens: score 0.875, syntax 1.00, render 1.00, 30.91s wall.

The bottleneck case is `attention_weighted_average_micro`. It truncates below 1400 tokens and needs the full cap for syntax success. The simpler number-line/statistics prompts can render at a 700-token cap and often stop before hitting the cap.

Adaptive cap experiment:

- Policy: use 1400 tokens only for attention/matrix/weighted-average prompts, otherwise 700.
- Result: score 0.875, syntax 1.00, render 1.00.
- Mean generation wall time: 16.48s across four prompts.
- Per-case wall time: binary search 15.31s, attention 31.17s, fraction 10.01s, confidence interval 9.43s.

Decision: adaptive caps are better than a single 1400-token cap, but the attention case is still too long for a strict 15s product budget. The generated code also contains repetitive `wait`/highlight loops that pass render checks but are not tasteful. Next quality work should add a duration/repetition verifier, not just more fine-tuning.

## Static Generation Quality Verifier

Added a static Manim generation-quality audit that estimates scene duration from `self.play` and `self.wait`, counts pacing calls, and flags repeated play patterns. This catches outputs that technically render but are poor learning-app candidates.

Adaptive cap audit:

- `binary_search_interval_shrink`: estimated 44.0s, 23 play calls, 21 waits, repeated play pattern count 9.
- `attention_weighted_average_micro`: estimated 77.0s, 38 play calls, 38 waits, repeated play pattern count 18.
- `fraction_unit_interval_reveal`: estimated 10.0s, no pacing warnings.
- `confidence_interval_band`: estimated 7.0s, no pacing warnings.

Single 1400-token cap audit:

- `binary_search_interval_shrink`: estimated 114.0s, 58 play calls, 56 waits, repeated play pattern count 27.
- `attention_weighted_average_micro`: estimated 77.0s, 38 play calls, 38 waits, repeated play pattern count 18.

Decision: the next scoring gate should require render success plus pacing/taste constraints. For learning-app generation, reject outputs with estimated duration above 20s, more than 18 `self.play` calls, more than 8 waits, or repeated `self.play` patterns.

## Production Gate Metrics

The evaluator and model benchmark now emit two stricter product metrics:

- `quality_success_rate`: share of generated cases with no pacing/taste warnings.
- `production_success_rate`: share of generated cases that have valid syntax, render successfully, and pass the pacing/taste verifier.

Leaderboard sorting now prioritizes production-ready output before raw weighted score. This avoids promoting models that render but create 40-100s repetitive scenes, which is not acceptable for on-demand learning-app generation.

Adaptive-cap rerun with first-class gate metrics:

- Syntax success rate: 1.00.
- Render success rate: 1.00.
- Quality success rate: 0.50.
- Production success rate: 0.50.
- Mean wall time: 17.12s across four focused prompts.

The two production failures are the same pacing failures as the static audit: `binary_search_interval_shrink` estimates 44.0s with 23 play calls and 21 waits, while `attention_weighted_average_micro` estimates 77.0s with 38 play calls and 38 waits. Next iteration should target concise scene synthesis or post-generation pacing repair before more training.

## Deterministic Pacing Repair

Added a conservative post-generation compactor experiment that removes repeated one-line `self.play(...)` loops after three repeats, drops waits paired with removed repeated plays, and caps remaining waits at eight calls. This is now considered an opt-in diagnostic/product-cleanup experiment, not the default model evaluation path.

Rescoring the saved adaptive-cap generations with the pacing repair:

- Syntax success rate: 1.00.
- Render success rate: 1.00.
- Quality success rate: 1.00.
- Production success rate: 1.00.
- Mean case score: 0.875.

The two repaired failures now pass the production gate:

- `binary_search_interval_shrink`: 44.0s -> 19.0s estimated scene duration, 23 -> 11 play calls, 21 -> 8 waits.
- `attention_weighted_average_micro`: 77.0s -> 17.0s estimated scene duration, 38 -> 8 play calls, 38 -> 8 waits.

Decision update: keep current Qwen LoRA plus semantic stop as the default raw model path. Deterministic repair and pacing compaction should remain opt-in experiments and must be reported separately from raw model metrics.

## Natural Stop vs Token Caps

Hard token caps are not the product strategy. `max_tokens` should be a safety ceiling, because a 30-60s animation legitimately needs more code than a 15s micro-scene. The model should learn when the scene is complete and emit a natural stop; the benchmark should measure whether it stops cleanly instead of forcing fixed output lengths.

Observed cap-sweep behavior on `attention_weighted_average_micro`: generations often ran exactly to the requested ceiling (`generation_tokens == max_tokens`). That does not prove the model cannot stop naturally; it means the tested ceilings were below the model's learned completion length or that repetitive loops consumed the budget before EOS. Both are model/inference/data problems, not a reason to optimize by lowering caps.

Next optimization target:

- Track `stop_reason` and `hit_token_ceiling` in local inference metrics.
- Run a natural-stop benchmark with a high safety ceiling to see whether EOS appears before the ceiling.
- Penalize repeated highlight/wait loops in evaluation and training examples.
- Tune decoding and model choice for speed without using short caps as the main control knob.

Implementation decision: use the model tokenizer's native chat-template EOS/end-of-turn token rather than a custom textual stop marker. Training dataset rows are now chat-only records with `messages`, not mixed `prompt`/`completion` plus `messages`, so MLX-LM uses `ChatDataset` and applies the same system/user/assistant chat template used at inference. This should train the built-in assistant stop behavior directly.

## Chat-Only EOS Probe

Rebuilt chat-only datasets so MLX-LM uses `ChatDataset` and the model tokenizer's native assistant EOS/end-of-turn behavior. Split sizes: full probe 138/23/23, focused learning-app taste 1/1/4.

Stop benchmark at a 2560-token safety ceiling:

- Current adapter: model EOS 0.50, token ceiling 0.50, mean 1498 tokens, 34.30s wall, production 0.75, score 0.705.
- Base-trained chat-EOS probe: best step 50, val loss 0.579, model EOS 1.00, token ceiling 0.00, mean 634.25 tokens, 14.43s wall, production 0.50, score 0.646.
- Current-adapter chat-EOS refresh: best step 25, val loss 0.515, model EOS 1.00, token ceiling 0.00, mean 593.75 tokens, 13.43s wall, production 0.00, score 0.55.

Decision: chat-only training fixes the stop behavior, but both EOS probe adapters are not promotion candidates. The current adapter remains the best product checkpoint. The next useful experiment is not a larger blind EOS refresh; it should mix chat-only formatting with render-safe Manim examples and/or lower learning rate, then promote only if both `model_eos_rate` and `production_success_rate` improve.

## Raw-Eval Performance Iteration

Detailed notes moved to `docs/raw-demo-performance-iteration.md` to keep this file below the 300-line project limit.

Decision: use `configs/local_mlx_speculative_dynamic_stop_seed7_fast_prod_benchmark.json` as the current raw demo profile when production success matters more than absolute fastest response. It improves the corrected raw benchmark from 2/4 to 3/4 production-ready cases at mean 13.29s wall time. Keep seed42 dynamic-stop as the speed reference only.
