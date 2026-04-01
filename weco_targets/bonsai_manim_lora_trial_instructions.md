Optimize `mean_case_score` for short-horizon Manim fine-tuning on Prism ML's Bonsai 8B MLX 1-bit model.

Constraints:

- Only edit values inside `TRIAL_OVERRIDES` in `weco_targets/bonsai_manim_lora_trial.py`.
- Keep the file valid Python and preserve the dictionary structure.
- Keep `evaluation.run_render` enabled.
- Do not increase `train.iters` above 160.
- Do not increase `evaluation.max_cases` above 16.
- Do not increase `evaluation.max_render_seconds` above 120.
- Do not change `BASE_CONFIG_PATH`, artifact paths, or the base model.

Optimization hints:

- Bonsai's model card suggests starting near temperature `0.5`, top-k `20`, and top-p `0.9`.
- Explore LoRA budget, evaluation weights, and generation parameters before broad dataset filtering.
- Treat `render_success_rate`, `syntax_success_rate`, and `test_loss` as guardrails even though the primary metric is `mean_case_score`.
