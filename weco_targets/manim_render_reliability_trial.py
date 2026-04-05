"""
Editable Weco search space for render-first Manim fine-tuning trials.

This target biases the search toward reliable, concise, API-compatible outputs.
Weco should only edit values inside TRIAL_OVERRIDES.
"""

BASE_CONFIG_PATH = "configs/m4_max_qwen25coder_3b.json"

TRIAL_OVERRIDES = {
    "name": "m4-max-qwen25coder-3b-render-reliability",
    "dataset_filter": {
        "include_tags": [],
        "exclude_tags": ["longform"],
    },
    "train": {
        "iters": 100,
        "learning_rate": 0.00008,
        "val_batches": 12,
        "steps_per_eval": 20,
        "save_every": 20,
        "grad_accumulation_steps": 8,
        "early_stopping_patience": 2,
        "early_stopping_min_delta": 0.003,
        "early_stopping_chunk_size": 20,
    },
    "generation": {
        "temperature": 0.0,
        "top_p": 0.9,
        "top_k": 0,
        "max_tokens": 1600,
    },
    "evaluation": {
        "max_cases": 16,
        "run_render": True,
        "render_quality": "low",
        "max_render_seconds": 90,
        "metric_weights": {
            "syntax": 0.30,
            "scene_class": 0.15,
            "required_snippets": 0.15,
            "forbidden_snippets": 0.05,
            "render": 0.35,
        },
    },
}
