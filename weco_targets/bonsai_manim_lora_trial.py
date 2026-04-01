"""
Editable Weco search space for short-horizon Bonsai Manim fine-tuning trials.

This target uses Prism ML's MLX-native 1-bit Bonsai 8B checkpoint as the base
model. Weco should keep the file structure intact and only adjust values inside
TRIAL_OVERRIDES.
"""

BASE_CONFIG_PATH = "configs/bonsai_8b_mlx_1bit.json"

TRIAL_OVERRIDES = {
    "name": "m4-max-bonsai-8b-1bit-weco-trial",
    "dataset_filter": {
        "include_tags": [],
        "exclude_tags": [],
    },
    "train": {
        "iters": 120,
        "learning_rate": 0.00008,
        "val_batches": 12,
        "steps_per_eval": 20,
        "save_every": 20,
        "grad_accumulation_steps": 8,
        "early_stopping_patience": 2,
        "early_stopping_min_delta": 0.005,
        "early_stopping_chunk_size": 20,
    },
    "generation": {
        "temperature": 0.5,
        "top_p": 0.9,
        "top_k": 20,
        "max_tokens": 2560,
    },
    "evaluation": {
        "max_cases": 12,
        "run_render": True,
        "render_quality": "low",
        "max_render_seconds": 90,
        "metric_weights": {
            "syntax": 0.2,
            "scene_class": 0.15,
            "required_snippets": 0.25,
            "forbidden_snippets": 0.05,
            "render": 0.35,
        },
    },
}
