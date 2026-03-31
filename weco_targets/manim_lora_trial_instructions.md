Optimize `mean_case_score` for the Manim fine-tuning trial without turning the run into an expensive full-scale sweep.

Constraints:

- Only edit values inside `TRIAL_OVERRIDES` in `weco_targets/manim_lora_trial.py`.
- Keep the file valid Python and preserve the dictionary structure.
- Prefer small, targeted changes over broad rewrites.
- Keep `evaluation.run_render` enabled so the score still reflects runnable scenes.
- Do not increase `train.iters` above 140.
- Do not increase `evaluation.max_cases` above 16.
- Do not increase `evaluation.max_render_seconds` above 120.
- Do not change `BASE_CONFIG_PATH`, artifact paths, or the base model.

Optimization hints:

- Explore learning rate, evaluation weights, short-horizon training budget, and generation settings first.
- If you use tag filters, keep them plausible and avoid collapsing the dataset to a tiny niche.
- Treat `render_success_rate`, `syntax_success_rate`, and `test_loss` as guardrails even though the primary metric is `mean_case_score`.
