from __future__ import annotations

import ast
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from mac_pipeline.mlx import evaluate_loss, generate_completion
from mac_pipeline.types import ExperimentConfig, MetricWeights
from mac_pipeline.utils import load_records, write_json

SCENE_BASES = {"Scene", "ThreeDScene", "MovingCameraScene", "ZoomedScene"}
CODE_BLOCK_PATTERN = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_code(text: str) -> str:
    match = CODE_BLOCK_PATTERN.search(text)
    return match.group(1).strip() if match else text.strip()


def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def detect_scene_class(code: str) -> str | None:
    tree = ast.parse(code)
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            if any(_base_name(base) in SCENE_BASES for base in node.bases):
                return node.name
    return None


def run_render_check(code: str, scene_name: str, quality: str, timeout_seconds: int) -> tuple[bool, str]:
    quality_flag = {"low": "-ql", "medium": "-qm", "high": "-qh"}.get(quality, "-ql")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        script_path = tmp_path / "scene.py"
        script_path.write_text(code)
        command = [
            sys.executable,
            "-m",
            "manim",
            quality_flag,
            "--disable_caching",
            "--media_dir",
            str(tmp_path / "media"),
            str(script_path),
            scene_name,
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False, f"render timed out after {timeout_seconds}s"
        output = (result.stdout + "\n" + result.stderr).strip()
        return result.returncode == 0, output[-1500:]


def score_case(case: dict[str, Any], code: str, render_enabled: bool, weights: MetricWeights, quality: str, timeout_seconds: int) -> dict[str, Any]:
    syntax_ok = True
    syntax_error = ""
    scene_name = None
    try:
        scene_name = detect_scene_class(code)
    except SyntaxError as exc:
        syntax_ok = False
        syntax_error = str(exc)

    required = case.get("must_contain", [])
    required_ratio = (
        sum(1 for snippet in required if snippet in code) / len(required) if required else 1.0
    )
    forbidden = case.get("must_not_contain", [])
    forbidden_ok = all(snippet not in code for snippet in forbidden)

    render_ok = None
    render_log = ""
    if render_enabled and syntax_ok and scene_name:
        render_ok, render_log = run_render_check(code, scene_name, quality, timeout_seconds)

    enabled_weights = {
        "syntax": weights.syntax,
        "scene_class": weights.scene_class,
        "required_snippets": weights.required_snippets,
        "forbidden_snippets": weights.forbidden_snippets,
    }
    if render_ok is not None:
        enabled_weights["render"] = weights.render
    total_weight = sum(enabled_weights.values()) or 1.0
    weighted_score = (
        enabled_weights["syntax"] * float(syntax_ok)
        + enabled_weights["scene_class"] * float(bool(scene_name))
        + enabled_weights["required_snippets"] * required_ratio
        + enabled_weights["forbidden_snippets"] * float(forbidden_ok)
        + enabled_weights.get("render", 0.0) * float(bool(render_ok))
    ) / total_weight

    return {
        "case_id": case["case_id"],
        "syntax_ok": syntax_ok,
        "syntax_error": syntax_error,
        "scene_name": scene_name,
        "required_snippet_ratio": required_ratio,
        "forbidden_ok": forbidden_ok,
        "render_ok": render_ok,
        "render_log_tail": render_log,
        "weighted_score": weighted_score,
    }


def evaluate_adapter(config: ExperimentConfig, dataset_dir: Path, adapter_path: Path, output_path: Path) -> dict[str, Any]:
    records = load_records(dataset_dir / "test.jsonl")
    max_cases = config.evaluation.max_cases or len(records)
    selected = records[:max_cases]
    per_case: list[dict[str, Any]] = []
    for record in selected:
        system_prompt = next(
            (message["content"] for message in record["messages"] if message["role"] == "system"),
            None,
        )
        user_prompt = next(
            message["content"] for message in record["messages"] if message["role"] == "user"
        )
        raw_response = generate_completion(
            base_model=config.base_model,
            adapter_path=adapter_path,
            prompt=user_prompt,
            system_prompt=system_prompt,
            generation=config.generation,
        )
        code = extract_code(raw_response)
        case_result = score_case(
            case=record,
            code=code,
            render_enabled=config.evaluation.run_render,
            weights=config.evaluation.metric_weights,
            quality=config.evaluation.render_quality,
            timeout_seconds=config.evaluation.max_render_seconds,
        )
        case_result["raw_response"] = raw_response
        case_result["code"] = code
        per_case.append(case_result)

    syntax_rate = sum(item["syntax_ok"] for item in per_case) / len(per_case)
    render_attempts = [item for item in per_case if item["render_ok"] is not None]
    render_rate = (
        sum(item["render_ok"] for item in render_attempts) / len(render_attempts)
        if render_attempts
        else None
    )
    mean_case_score = sum(item["weighted_score"] for item in per_case) / len(per_case)

    payload = {
        "run_name": config.name,
        "base_model": config.base_model,
        "adapter_path": str(adapter_path),
        "dataset_dir": str(dataset_dir),
        "summary": {
            "num_cases": len(per_case),
            "syntax_success_rate": syntax_rate,
            "render_success_rate": render_rate,
            "mean_case_score": mean_case_score,
        },
        "cases": per_case,
    }
    if config.run_loss_eval:
        payload["summary"].update(
            evaluate_loss(
                config=config,
                dataset_dir=dataset_dir,
                adapter_path=adapter_path,
                log_path=output_path.with_suffix(".loss.log"),
            )
        )
    write_json(output_path, payload)
    return payload
