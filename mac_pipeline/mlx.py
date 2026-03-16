from __future__ import annotations

import json
import re
import shutil
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
VAL_LOSS_PATTERN = re.compile(
    rf"Iter\s+(\d+):\s+Val loss\s+{FLOAT_PATTERN}",
    re.IGNORECASE,
)


def _run(
    command: list[str],
    log_path: Path | None = None,
    include_stderr: bool = True,
    append_log: bool = False,
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
    mode = "a" if append_log else "w"
    with log_path.open(mode) as handle:
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


def _base_lora_command(
    config: ExperimentConfig,
    dataset_dir: Path,
    adapter_path: Path | None,
    *,
    iters_override: int | None = None,
    resume_adapter_file: Path | None = None,
) -> list[str]:
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
        str(iters_override or train.iters),
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
        "--save-every",
        str(train.save_every),
        "--test-batches",
        str(train.test_batches),
        "--max-seq-length",
        str(train.max_seq_length),
        "--seed",
        str(train.seed),
    ]
    if adapter_path is not None:
        command.extend(["--adapter-path", str(adapter_path)])
    if resume_adapter_file is not None:
        command.extend(["--resume-adapter-file", str(resume_adapter_file)])
    if train.mask_prompt:
        command.append("--mask-prompt")
    if train.grad_checkpoint:
        command.append("--grad-checkpoint")
    return command


def _append_log_message(log_path: Path, message: str) -> None:
    ensure_parent(log_path)
    with log_path.open("a") as handle:
        handle.write(f"{message.rstrip()}\n")


def _parse_last_val_loss(raw_output: str) -> tuple[int, float] | None:
    matches = list(VAL_LOSS_PATTERN.finditer(raw_output))
    if not matches:
        return None
    match = matches[-1]
    return int(match.group(1)), float(match.group(2))


def _resolve_chunk_size(config: ExperimentConfig) -> int:
    train = config.train
    if train.early_stopping_chunk_size > 0:
        return train.early_stopping_chunk_size
    return max(1, min(train.steps_per_eval, train.save_every))


def _snapshot_checkpoint(adapter_path: Path, step: int) -> Path:
    checkpoint_path = adapter_path / f"{step:07d}_adapters.safetensors"
    shutil.copy2(adapter_path / "adapters.safetensors", checkpoint_path)
    return checkpoint_path


def _restore_best_checkpoint(adapter_path: Path, best_checkpoint_path: Path, best_step: int, best_loss: float) -> None:
    shutil.copy2(best_checkpoint_path, adapter_path / "adapters.safetensors")
    metadata = {
        "best_step": best_step,
        "best_val_loss": best_loss,
        "checkpoint_path": str(best_checkpoint_path),
    }
    (adapter_path / "best_checkpoint.json").write_text(json.dumps(metadata, indent=2))


def _train_single_run(config: ExperimentConfig, dataset_dir: Path, adapter_path: Path, log_path: Path) -> str:
    command = _base_lora_command(config, dataset_dir, adapter_path)
    command.append("--train")
    return _run(command, log_path)


def _train_with_early_stopping(
    config: ExperimentConfig,
    dataset_dir: Path,
    adapter_path: Path,
    log_path: Path,
) -> str:
    train = config.train
    total_iters = train.iters
    chunk_size = _resolve_chunk_size(config)
    completed_iters = 0
    best_loss: float | None = None
    best_step: int | None = None
    best_checkpoint_path: Path | None = None
    stale_evals = 0

    if adapter_path.exists():
        shutil.rmtree(adapter_path)
    if log_path.exists():
        log_path.unlink()

    while completed_iters < total_iters:
        current_iters = min(chunk_size, total_iters - completed_iters)
        resume_file = adapter_path / "adapters.safetensors" if completed_iters > 0 else None
        _append_log_message(
            log_path,
            f"[mac_pipeline] chunk_start completed={completed_iters} current_iters={current_iters}",
        )
        command = _base_lora_command(
            config,
            dataset_dir,
            adapter_path,
            iters_override=current_iters,
            resume_adapter_file=resume_file if resume_file and resume_file.exists() else None,
        )
        command.append("--train")
        chunk_output = _run(command, log_path, append_log=True)

        completed_iters += current_iters
        current_checkpoint_path = _snapshot_checkpoint(adapter_path, completed_iters)
        val_result = _parse_last_val_loss(chunk_output)
        if val_result is None:
            continue

        local_step, val_loss = val_result
        global_step = completed_iters - current_iters + local_step
        min_delta = train.early_stopping_min_delta
        improved = best_loss is None or val_loss < (best_loss - min_delta)
        if improved:
            best_loss = val_loss
            best_step = global_step
            best_checkpoint_path = current_checkpoint_path
            stale_evals = 0
            _append_log_message(
                log_path,
                f"[mac_pipeline] best_checkpoint step={best_step} val_loss={best_loss:.3f}",
            )
        else:
            stale_evals += 1
            _append_log_message(
                log_path,
                f"[mac_pipeline] no_improvement step={global_step} val_loss={val_loss:.3f} stale_evals={stale_evals}",
            )
            if stale_evals >= train.early_stopping_patience:
                _append_log_message(
                    log_path,
                    f"[mac_pipeline] early_stop triggered at step={global_step} patience={train.early_stopping_patience}",
                )
                break

    if (
        train.restore_best_checkpoint
        and best_checkpoint_path is not None
        and best_step is not None
        and best_loss is not None
    ):
        _restore_best_checkpoint(adapter_path, best_checkpoint_path, best_step, best_loss)
        _append_log_message(
            log_path,
            f"[mac_pipeline] restored_best_checkpoint step={best_step} val_loss={best_loss:.3f}",
        )

    return log_path.read_text()


def train_adapter(config: ExperimentConfig, dataset_dir: Path, adapter_path: Path, log_path: Path) -> str:
    if config.train.early_stopping_patience <= 0:
        return _train_single_run(config, dataset_dir, adapter_path, log_path)
    return _train_with_early_stopping(config, dataset_dir, adapter_path, log_path)


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


def evaluate_loss(
    config: ExperimentConfig,
    dataset_dir: Path,
    adapter_path: Path | None,
    log_path: Path,
) -> dict[str, float | None]:
    command = _base_lora_command(config, dataset_dir, adapter_path)
    command.append("--test")
    raw_output = _run(command, log_path)
    metrics = parse_loss_metrics(raw_output)
    metrics["log_path"] = str(log_path)
    return metrics


def generate_completion(
    base_model: str,
    adapter_path: Path | None,
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
    if adapter_path is not None:
        command.extend(["--adapter-path", str(adapter_path)])
    if generation.top_k > 0:
        command.extend(["--top-k", str(generation.top_k)])
    if system_prompt:
        command.extend(["--system-prompt", system_prompt])
    return _run(command, include_stderr=False).strip()
