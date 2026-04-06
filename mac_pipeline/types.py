from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SplitConfig:
    train_fraction: float = 0.8
    valid_fraction: float = 0.1
    seed: int = 42


@dataclass
class DatasetFilterConfig:
    include_tags: list[str] = field(default_factory=list)
    exclude_tags: list[str] = field(default_factory=list)


@dataclass
class DatasetSourceConfig:
    kind: str = "local"
    path: str | None = None
    repo_id: str | None = None
    config_name: str | None = None
    split: str = "train"
    revision: str | None = None

    @classmethod
    def load(cls, raw: str | dict[str, Any]) -> "DatasetSourceConfig":
        if isinstance(raw, str):
            return cls(kind="local", path=raw)
        if not isinstance(raw, dict):
            raise TypeError(
                "source_dataset must be either a string path or an object config."
            )
        return cls(
            kind=raw.get("kind", "local"),
            path=raw.get("path"),
            repo_id=raw.get("repo_id"),
            config_name=raw.get("config_name"),
            split=raw.get("split", "train"),
            revision=raw.get("revision"),
        )

    def validate(self) -> None:
        if self.kind == "local":
            if not self.path:
                raise ValueError("Local source_dataset requires a non-empty path.")
            return
        if self.kind == "hf":
            if not self.repo_id:
                raise ValueError("HF source_dataset requires a non-empty repo_id.")
            return
        raise ValueError(f"Unsupported source_dataset kind: {self.kind}")

    def describe(self) -> str:
        self.validate()
        if self.kind == "local":
            return self.path or ""
        revision = f"@{self.revision}" if self.revision else ""
        config_name = self.config_name or "default"
        return f"hf://{self.repo_id}{revision}/{config_name}:{self.split}"


@dataclass
class TrainConfig:
    fine_tune_type: str = "lora"
    optimizer: str = "adamw"
    mask_prompt: bool = True
    num_layers: int = 12
    batch_size: int = 1
    iters: int = 300
    val_batches: int = 25
    learning_rate: float = 1e-4
    steps_per_report: int = 10
    steps_per_eval: int = 25
    grad_accumulation_steps: int = 8
    save_every: int = 25
    test_batches: int = -1
    max_seq_length: int = 2048
    grad_checkpoint: bool = True
    seed: int = 42
    early_stopping_patience: int = 3
    early_stopping_min_delta: float = 0.01
    early_stopping_chunk_size: int = 25
    restore_best_checkpoint: bool = True


@dataclass
class GenerationConfig:
    max_tokens: int = 2560
    temperature: float = 0.2
    top_p: float = 0.95
    top_k: int = 0
    seed: int = 42


@dataclass
class MetricWeights:
    syntax: float = 0.25
    scene_class: float = 0.15
    required_snippets: float = 0.25
    forbidden_snippets: float = 0.05
    render: float = 0.30


@dataclass
class EvaluationConfig:
    run_render: bool = True
    max_cases: int = 0
    render_quality: str = "low"
    max_render_seconds: int = 120
    allowed_render_regression: float = 0.05
    min_loss_delta: float = 0.01
    tie_loss_delta: float = 0.003
    metric_weights: MetricWeights = field(default_factory=MetricWeights)


@dataclass
class OpenRouterConfig:
    api_base: str = "https://openrouter.ai/api/v1"
    api_key_env: str = "OPENROUTER_API_KEY"
    site_url: str | None = None
    app_name: str = "autoresearch-manim-finetune"
    timeout_seconds: int = 180
    route: str | None = None
    transforms: list[str] = field(default_factory=list)


@dataclass
class BenchmarkTargetConfig:
    name: str
    backend: str
    model: str
    adapter_path: str | None = None
    skill_path: str | None = None
    route: str | None = None
    transforms: list[str] = field(default_factory=list)


@dataclass
class ExperimentConfig:
    name: str
    base_model: str
    source_dataset: DatasetSourceConfig
    dataset_dir: str
    adapter_path: str
    eval_output_path: str
    results_tsv: str = "results.tsv"
    run_loss_eval: bool = True
    dataset_filter: DatasetFilterConfig = field(default_factory=DatasetFilterConfig)
    splits: SplitConfig = field(default_factory=SplitConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)

    @classmethod
    def load(cls, path: str | Path) -> "ExperimentConfig":
        raw = json.loads(Path(path).read_text())
        return cls(
            name=raw["name"],
            base_model=raw["base_model"],
            source_dataset=DatasetSourceConfig.load(raw["source_dataset"]),
            dataset_dir=raw["dataset_dir"],
            adapter_path=raw["adapter_path"],
            eval_output_path=raw["eval_output_path"],
            results_tsv=raw.get("results_tsv", "results.tsv"),
            run_loss_eval=raw.get("run_loss_eval", True),
            dataset_filter=DatasetFilterConfig(**raw.get("dataset_filter", {})),
            splits=SplitConfig(**raw.get("splits", {})),
            train=TrainConfig(**raw.get("train", {})),
            generation=GenerationConfig(**raw.get("generation", {})),
            evaluation=EvaluationConfig(
                metric_weights=MetricWeights(
                    **raw.get("evaluation", {}).get("metric_weights", {})
                ),
                **{
                    key: value
                    for key, value in raw.get("evaluation", {}).items()
                    if key != "metric_weights"
                },
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkConfig:
    name: str
    dataset_dir: str
    output_dir: str
    targets: list[BenchmarkTargetConfig]
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    openrouter: OpenRouterConfig = field(default_factory=OpenRouterConfig)

    @classmethod
    def load(cls, path: str | Path) -> "BenchmarkConfig":
        raw = json.loads(Path(path).read_text())
        return cls(
            name=raw["name"],
            dataset_dir=raw["dataset_dir"],
            output_dir=raw["output_dir"],
            targets=[BenchmarkTargetConfig(**target) for target in raw["targets"]],
            generation=GenerationConfig(**raw.get("generation", {})),
            evaluation=EvaluationConfig(
                metric_weights=MetricWeights(
                    **raw.get("evaluation", {}).get("metric_weights", {})
                ),
                **{
                    key: value
                    for key, value in raw.get("evaluation", {}).items()
                    if key != "metric_weights"
                },
            ),
            openrouter=OpenRouterConfig(**raw.get("openrouter", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
