from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from mac_pipeline.types import ExperimentConfig, GenerationConfig
from mac_pipeline.utils import ensure_parent

FLOAT_PATTERN = r"([0-9]+(?:\.[0-9]+)?)"
LOSS_PATTERNS = [
    re.compile(rf"\btest loss\b[:=]?\s*{FLOAT_PATTERN}", re.IGNORECASE),
    re.compile(rf"\bloss\b[:=]?\s*{FLOAT_PATTERN}", re.IGNORECASE),
]
PERPLEXITY_PATTERNS = [
    re.compile(rf"\bperplexity\b[:=]?\s*{FLOAT_PATTERN}", re.IGNORECASE),
    re.compile(rf"\bppl\b[:=]?\s*{FLOAT_PATTERN}", re.IGNORECASE),
]


def _run(
    command: list[str],
    log_path: Path | None = None,
    include_stderr: bool = True,
) -> str:
    if log_path is None:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        output = result.stdout.strip()
        if include_stderr and result.stderr.strip():
            output = f"{output}\n{result.stderr.strip()}".strip()
        if result.returncode != 0:
            raise RuntimeError(output or result.stderr.strip())
        return output
    ensure_parent(log_path)
    with log_path.open("w") as handle:
        result = subprocess.run(
            command,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    output = log_path.read_text()
    if result.returncode != 0:
        raise RuntimeError(output)
    return output


def _base_lora_command(config: ExperimentConfig, dataset_dir: Path, adapter_path: Path) -> list[str]:
    train = config.train
    command = [
        sys.executable,
        "-m",
        "mlx_lm",
        "lora",
        "--model",
        config.base_model,
        "--data",
        str(dataset_dir),
        "--fine-tune-type",
        train.fine_tune_type,
        "--optimizer",
        train.optimizer,
        "--num-layers",
        str(train.num_layers),
        "--batch-size",
        str(train.batch_size),
        "--iters",
        str(train.iters),
        "--val-batches",
        str(train.val_batches),
        "--learning-rate",
        str(train.learning_rate),
        "--steps-per-report",
        str(train.steps_per_report),
        "--steps-per-eval",
        str(train.steps_per_eval),
        "--grad-accumulation-steps",
        str(train.grad_accumulation_steps),
        "--adapter-path",
        str(adapter_path),
        "--save-every",
        str(train.save_every),
        "--test-batches",
        str(train.test_batches),
        "--max-seq-length",
        str(train.max_seq_length),
        "--seed",
        str(train.seed),
    ]
    if train.mask_prompt:
        command.append("--mask-prompt")
    if train.grad_checkpoint:
        command.append("--grad-checkpoint")
    return command


def train_adapter(config: ExperimentConfig, dataset_dir: Path, adapter_path: Path, log_path: Path) -> str:
    command = _base_lora_command(config, dataset_dir, adapter_path)
    command.append("--train")
    return _run(command, log_path)


def parse_loss_metrics(raw_output: str) -> dict[str, float | None]:
    def _first_match(patterns: list[re.Pattern[str]]) -> float | None:
        for pattern in patterns:
            match = pattern.search(raw_output)
            if match:
                return float(match.group(1))
        return None

    return {
        "test_loss": _first_match(LOSS_PATTERNS),
        "test_perplexity": _first_match(PERPLEXITY_PATTERNS),
    }


def evaluate_loss(config: ExperimentConfig, dataset_dir: Path, adapter_path: Path, log_path: Path) -> dict[str, float | None]:
    command = _base_lora_command(config, dataset_dir, adapter_path)
    command.append("--test")
    raw_output = _run(command, log_path)
    metrics = parse_loss_metrics(raw_output)
    metrics["log_path"] = str(log_path)
    return metrics


def generate_completion(
    base_model: str,
    adapter_path: Path,
    prompt: str,
    system_prompt: str | None,
    generation: GenerationConfig,
) -> str:
    command = [
        sys.executable,
        "-m",
        "mlx_lm",
        "generate",
        "--model",
        base_model,
        "--adapter-path",
        str(adapter_path),
        "--prompt",
        prompt,
        "--max-tokens",
        str(generation.max_tokens),
        "--temp",
        str(generation.temperature),
        "--top-p",
        str(generation.top_p),
        "--seed",
        str(generation.seed),
        "--verbose",
        "False",
    ]
    if generation.top_k > 0:
        command.extend(["--top-k", str(generation.top_k)])
    if system_prompt:
        command.extend(["--system-prompt", system_prompt])
    return _run(command, include_stderr=False).strip()
