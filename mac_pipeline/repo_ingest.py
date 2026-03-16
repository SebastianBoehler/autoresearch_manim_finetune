from __future__ import annotations

import ast
import json
import re
import subprocess
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mac_pipeline.utils import ensure_parent, load_records, write_json, write_jsonl

SCENE_BASES = {"Scene", "ThreeDScene", "MovingCameraScene", "ZoomedScene"}
REPO_URL_PATTERN = re.compile(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")
CUSTOM_LIBRARY_PREFIXES = ("manim_ml", "manim_chemistry", "manim_physics")
PLAIN_ALLOWED_PREFIXES = {
    "manim",
    "numpy",
    "np",
    "math",
    "random",
    "itertools",
    "collections",
    "typing",
    "pathlib",
    "functools",
    "statistics",
    "decimal",
    "fractions",
    "copy",
    "PIL",
    "sys",
    "os",
}


@dataclass
class RepoConfig:
    name: str
    repo_url: str
    license: str
    domain: str
    include_paths: list[str]
    ref: str = "HEAD"


def _load_repo_manifest(path: Path) -> list[RepoConfig]:
    configs = []
    for record in load_records(path):
        missing = {"name", "repo_url", "license", "domain", "include_paths"} - record.keys()
        if missing:
            raise ValueError(f"Repo manifest entry missing keys: {sorted(missing)}")
        configs.append(RepoConfig(**record))
    return configs


def _repo_slug(repo_url: str) -> str:
    match = REPO_URL_PATTERN.match(repo_url)
    if not match:
        raise ValueError(f"Unsupported GitHub URL: {repo_url}")
    owner, repo = match.groups()
    return f"{owner}--{repo}"


def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _scene_classes(tree: ast.AST) -> list[str]:
    classes: list[str] = []
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.ClassDef) and any(_base_name(base) in SCENE_BASES for base in node.bases):
            classes.append(node.name)
    return classes


def _collect_imports(tree: ast.AST) -> tuple[list[str], list[str]]:
    imports: list[str] = []
    local_imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level > 0:
                local_imports.append("." * node.level + module)
            else:
                imports.append(module)
    return sorted(set(filter(None, imports))), sorted(set(filter(None, local_imports)))


def _custom_imports(imports: list[str], local_imports: list[str]) -> list[str]:
    custom = [name for name in imports if name.startswith(CUSTOM_LIBRARY_PREFIXES)]
    custom.extend(local_imports)
    return sorted(set(custom))


def _is_plain_manim_candidate(imports: list[str], local_imports: list[str]) -> bool:
    if local_imports:
        return False
    for name in imports:
        prefix = name.split(".")[0]
        if name.startswith(CUSTOM_LIBRARY_PREFIXES):
            return False
        if prefix not in PLAIN_ALLOWED_PREFIXES:
            return False
    return True


def _derive_prompt(scene_name: str, domain: str, repo_name: str) -> str:
    domain_phrase = {
        "ml": "machine learning",
        "chemistry": "chemistry",
    }.get(domain, domain)
    title = re.sub(r"(?<!^)(?=[A-Z])", " ", scene_name).strip()
    return (
        f"Create a Manim scene for a {domain_phrase} concept inspired by the `{title}` example "
        f"from the `{repo_name}` repository. Return runnable Python code with one main scene class."
    )


def _case_id(repo_name: str, file_path: str, scene_name: str) -> str:
    base = f"{repo_name}-{file_path}-{scene_name}".lower()
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-")


def _build_cases(config: RepoConfig, repo_root: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for include_path in config.include_paths:
        source_root = repo_root / include_path
        if not source_root.exists():
            continue
        for file_path in sorted(source_root.rglob("*.py")):
            if file_path.name.startswith("test_") or file_path.name == "__init__.py":
                continue
            code = file_path.read_text()
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", SyntaxWarning)
                    tree = ast.parse(code)
            except SyntaxError:
                continue
            scene_classes = _scene_classes(tree)
            if not scene_classes:
                continue
            imports, local_imports = _collect_imports(tree)
            custom_imports = _custom_imports(imports, local_imports)
            plain_candidate = _is_plain_manim_candidate(imports, local_imports)
            rel_path = str(file_path.relative_to(repo_root))
            for scene_name in scene_classes:
                cases.append(
                    {
                        "case_id": _case_id(config.name, rel_path, scene_name),
                        "prompt": _derive_prompt(scene_name, config.domain, config.name),
                        "completion": code.rstrip() + "\n",
                        "entry_scene": scene_name,
                        "tags": ["repo-import", config.domain, config.name.lower()],
                        "must_contain": [],
                        "must_not_contain": [],
                        "source_name": config.name,
                        "source_url": config.repo_url,
                        "license": config.license,
                        "source_domain": config.domain,
                        "source_repo_path": rel_path,
                        "source_ref": config.ref,
                        "imports": imports,
                        "local_imports": local_imports,
                        "custom_imports": custom_imports,
                        "uses_custom_library": bool(custom_imports),
                        "is_plain_manim_candidate": plain_candidate,
                        "requires_manual_conversion": not plain_candidate,
                    }
                )
    return cases


def import_repo_examples(manifest_path: Path, output_path: Path, metadata_path: Path | None = None) -> list[dict[str, Any]]:
    configs = _load_repo_manifest(manifest_path)
    all_cases: list[dict[str, Any]] = []
    clone_metadata: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        for config in configs:
            repo_dir = tmp_root / _repo_slug(config.repo_url)
            subprocess.run(
                ["git", "clone", "--depth", "1", config.repo_url, str(repo_dir)],
                check=True,
                capture_output=True,
                text=True,
            )
            if config.ref != "HEAD":
                subprocess.run(
                    ["git", "-C", str(repo_dir), "checkout", config.ref],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            revision = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            cases = _build_cases(config, repo_dir)
            all_cases.extend(cases)
            clone_metadata.append(
                {
                    "name": config.name,
                    "repo_url": config.repo_url,
                    "license": config.license,
                    "domain": config.domain,
                    "include_paths": config.include_paths,
                    "revision": revision,
                    "case_count": len(cases),
                }
            )
    ensure_parent(output_path)
    write_jsonl(output_path, all_cases)
    if metadata_path is not None:
        write_json(metadata_path, {"sources": clone_metadata, "total_cases": len(all_cases)})
    return all_cases


def filter_repo_candidates(
    input_path: Path,
    plain_output_path: Path,
    custom_output_path: Path | None = None,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    records = load_records(input_path)
    plain = [record for record in records if record.get("is_plain_manim_candidate")]
    custom = [record for record in records if not record.get("is_plain_manim_candidate")]
    ensure_parent(plain_output_path)
    write_jsonl(plain_output_path, plain)
    if custom_output_path is not None:
        ensure_parent(custom_output_path)
        write_jsonl(custom_output_path, custom)
    summary = {
        "input_path": str(input_path),
        "plain_candidate_count": len(plain),
        "custom_candidate_count": len(custom),
        "custom_library_breakdown": _count_custom_imports(custom),
    }
    if summary_path is not None:
        write_json(summary_path, summary)
    return summary


def _count_custom_imports(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        imports = record.get("custom_imports", [])
        if not imports:
            counts["none"] = counts.get("none", 0) + 1
            continue
        for name in imports:
            counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items()))
