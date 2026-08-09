from __future__ import annotations

from pathlib import Path
from typing import Callable

from mac_pipeline.benchmark_prompting import compose_system_prompt, load_target_skill
from mac_pipeline.eval import extract_code, score_case
from mac_pipeline.eval_summary import summarize_case_results
from mac_pipeline.local_inference import generate_completion
from mac_pipeline.openrouter import generate_openrouter_completion
from mac_pipeline.target_generation import generation_for_target
from mac_pipeline.types import BenchmarkConfig, BenchmarkTargetConfig
from mac_pipeline.utils import ensure_dir, load_records, slugify, write_json


def _target_generator(
    benchmark: BenchmarkConfig,
    target: BenchmarkTargetConfig,
    repo_root: Path,
) -> Callable[[str, str | None], str]:
    if target.backend == "local":
        adapter_path = None
        if target.adapter_path:
            adapter_path = (repo_root / target.adapter_path).resolve()
        generation = generation_for_target(benchmark.generation, target)

        def _generate(prompt: str, system_prompt: str | None) -> str:
            return generate_completion(
                base_model=target.model,
                adapter_path=adapter_path,
                prompt=prompt,
                system_prompt=system_prompt,
                generation=generation,
                transport=target.local_transport or benchmark.generation.local_transport,
            )

        return _generate

    if target.backend == "openrouter":
        def _generate(prompt: str, system_prompt: str | None) -> str:
            return generate_openrouter_completion(
                target=target,
                prompt=prompt,
                system_prompt=system_prompt,
                generation=benchmark.generation,
                config=benchmark.openrouter,
            )

        return _generate

    if target.backend == "adk_openrouter":
        from mac_pipeline.adk_openrouter import generate_adk_openrouter_completion

        def _generate(prompt: str, system_prompt: str | None) -> str:
            return generate_adk_openrouter_completion(
                model=target.model,
                prompt=prompt,
                system_prompt=system_prompt,
                generation=benchmark.generation,
            )

        return _generate

    raise ValueError(f"Unsupported benchmark backend: {target.backend}")


def _evaluate_target(
    benchmark: BenchmarkConfig,
    target: BenchmarkTargetConfig,
    records: list[dict],
    repo_root: Path,
) -> dict:
    generate = _target_generator(benchmark, target, repo_root)
    skill_text, resolved_skill_path = load_target_skill(target, repo_root)
    per_case: list[dict] = []
    for record in records:
        base_system_prompt = next(
            (message["content"] for message in record["messages"] if message["role"] == "system"),
            None,
        )
        system_prompt = compose_system_prompt(base_system_prompt, skill_text)
        user_prompt = next(
            message["content"] for message in record["messages"] if message["role"] == "user"
        )
        raw_response = generate(user_prompt, system_prompt)
        code = extract_code(raw_response)
        case_result = score_case(
            case=record,
            code=code,
            render_enabled=benchmark.evaluation.run_render,
            weights=benchmark.evaluation.metric_weights,
            quality=benchmark.evaluation.render_quality,
            timeout_seconds=benchmark.evaluation.max_render_seconds,
            allow_code_repair=benchmark.evaluation.allow_code_repair,
        )
        case_result["raw_response"] = raw_response
        case_result["generated_code"] = code
        case_result["code"] = code
        case_result["prompt"] = user_prompt
        per_case.append(case_result)

    return {
        "run_name": target.name,
        "backend": target.backend,
        "model": target.model,
        "adapter_path": target.adapter_path,
        "skill_path": resolved_skill_path,
        "summary": summarize_case_results(per_case),
        "cases": per_case,
    }


def run_benchmark(benchmark: BenchmarkConfig, repo_root: Path) -> dict:
    dataset_dir = (repo_root / benchmark.dataset_dir).resolve()
    output_dir = ensure_dir((repo_root / benchmark.output_dir).resolve())
    records = load_records(dataset_dir / "test.jsonl")
    max_cases = benchmark.evaluation.max_cases or len(records)
    selected = records[:max_cases]

    target_results: list[dict] = []
    for target in benchmark.targets:
        output_path = output_dir / f"{slugify(target.name)}.json"
        try:
            payload = _evaluate_target(benchmark, target, selected, repo_root)
            write_json(output_path, payload)
            target_results.append(
                {
                    "name": target.name,
                    "backend": target.backend,
                    "model": target.model,
                    "skill_path": payload.get("skill_path"),
                    "output_path": str(output_path),
                    "summary": payload["summary"],
                }
            )
        except Exception as exc:
            error_payload = {
                "run_name": target.name,
                "backend": target.backend,
                "model": target.model,
                "skill_path": target.skill_path,
                "error": str(exc),
            }
            write_json(output_path, error_payload)
            target_results.append(
                {
                    "name": target.name,
                    "backend": target.backend,
                    "model": target.model,
                    "skill_path": target.skill_path,
                    "output_path": str(output_path),
                    "error": str(exc),
                }
            )

    leaderboard = sorted(
        [item for item in target_results if "summary" in item],
        key=lambda item: (
            item["summary"].get("production_success_rate") or 0.0,
            item["summary"].get("quality_success_rate", 0.0),
            item["summary"].get("mean_case_score", 0.0),
            item["summary"].get("render_success_rate") or 0.0,
            item["summary"].get("syntax_success_rate", 0.0),
        ),
        reverse=True,
    )
    payload = {
        "name": benchmark.name,
        "dataset_dir": str(dataset_dir),
        "num_cases": len(selected),
        "targets": target_results,
        "leaderboard": leaderboard,
    }
    write_json(output_dir / "leaderboard.json", payload)
    return payload
