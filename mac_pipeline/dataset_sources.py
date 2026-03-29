from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from mac_pipeline.types import DatasetSourceConfig
from mac_pipeline.utils import load_records, resolve_path


def resolve_dataset_source(
    base_dir: Path,
    source: DatasetSourceConfig,
    override: str | None = None,
    override_kind: str | None = None,
    override_config_name: str | None = None,
    override_split: str | None = None,
    override_revision: str | None = None,
) -> DatasetSourceConfig:
    resolved = replace(source)
    if override is not None:
        effective_kind = override_kind or resolved.kind
        if effective_kind == "hf":
            resolved = DatasetSourceConfig(
                kind="hf",
                repo_id=override,
                config_name=resolved.config_name,
                split=resolved.split,
                revision=resolved.revision,
            )
        else:
            resolved = DatasetSourceConfig(kind="local", path=override)
    elif override_kind is not None and override_kind != resolved.kind:
        if override_kind == "hf":
            resolved = DatasetSourceConfig(
                kind="hf",
                repo_id=resolved.repo_id or resolved.path,
                config_name=resolved.config_name,
                split=resolved.split,
                revision=resolved.revision,
            )
        else:
            resolved = DatasetSourceConfig(kind="local", path=resolved.path or resolved.repo_id)

    if override_config_name is not None:
        resolved.config_name = override_config_name
    if override_split is not None:
        resolved.split = override_split
    if override_revision is not None:
        resolved.revision = override_revision

    resolved.validate()
    if resolved.kind == "local":
        resolved.path = str(resolve_path(base_dir, resolved.path or ""))
    return resolved


def load_source_records(source: DatasetSourceConfig) -> tuple[list[dict[str, Any]], str]:
    source.validate()
    if source.kind == "local":
        path = Path(source.path or "")
        if not path.exists():
            raise FileNotFoundError(f"Source dataset does not exist: {path}")
        return load_records(path), str(path)
    return _load_hf_records(source), source.describe()


def _load_hf_records(source: DatasetSourceConfig) -> list[dict[str, Any]]:
    from datasets import load_dataset

    dataset = load_dataset(
        source.repo_id,
        name=source.config_name,
        split=source.split,
        revision=source.revision,
    )
    return [dict(row) for row in dataset]
