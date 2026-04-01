"""
Editable Weco search space for short-horizon Manim fine-tuning trials.

Weco should keep the overall file structure intact and only make coherent changes
inside TRIAL_OVERRIDES. The eval script materializes this into a real config JSON
and runs the existing MLX pipeline.
"""

BASE_CONFIG_PATH = "configs/m4_max_qwen25coder_3b.json"

TRIAL_OVERRIDES = {
    "name": "m4-max-qwen25coder-3b-weco-trial",
    "dataset_filter": {
        "include_tags": [],
        "exclude_tags": [],
    },
    "train": {
        "iters": 120,
        "learning_rate": 0.00015,
        "val_batches": 12,
        "steps_per_eval": 20,
        "save_every": 20,
        "grad_accumulation_steps": 8,
        "early_stopping_patience": 3,
        "early_stopping_min_delta": 0.005,
        "early_stopping_chunk_size": 20,
    },
    "generation": {
        "temperature": 0.2,
        "top_p": 0.95,
        "top_k": 40,
        "max_tokens": 2560,
    },
    "evaluation": {
        "max_cases": 16,
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
