Optimize `render_success_rate` for the Manim fine-tuning trial without turning the run into an expensive sweep.

Constraints:

- Only edit values inside `TRIAL_OVERRIDES` in `weco_targets/manim_render_reliability_trial.py`.
- Keep the file valid Python and preserve the dictionary structure.
- Prefer small, targeted changes over broad rewrites.
- Keep `evaluation.run_render` enabled.
- Do not increase `train.iters` above `140`.
- Do not increase `evaluation.max_cases` above `16`.
- Do not increase `evaluation.max_render_seconds` above `120`.
- Do not change `BASE_CONFIG_PATH`, artifact paths, or the base model.

Optimization hints:

- Prioritize generation settings that reduce looping, truncation, and API drift.
- Explore `temperature`, `top_p`, `top_k`, and `max_tokens` before larger training changes.
- If you use tag filters, prefer plausible quality slices such as `longform`, `source:docs`, or `converted` before narrowing by topic.
- Keep the dataset broad enough to preserve general Manim competence.
- Treat `syntax_success_rate` and `mean_case_score` as guardrails while maximizing render success.
