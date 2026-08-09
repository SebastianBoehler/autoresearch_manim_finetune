from __future__ import annotations

import ast
import warnings
from collections import defaultdict
from typing import Any, Iterable


def versioned_system_prompt(manim_version: str) -> str:
    return (
        f"You write runnable Manim Community Edition {manim_version} Python files. "
        f"Use only APIs available in Manim Community Edition {manim_version}. "
        "Return only Python code, use `from manim import *`, and define exactly one scene class."
    )


def extract_api_usage(code: str, public_symbols: set[str]) -> dict[str, list[str]]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        tree = ast.parse(code)
    variable_types = _infer_variable_types(tree, public_symbols)
    symbols: set[str] = set()
    methods: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                name = _expression_name(base)
                if name in public_symbols:
                    symbols.add(name)
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id in public_symbols:
            symbols.add(node.func.id)
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        owner_type = _infer_expression_type(node.func.value, variable_types, public_symbols)
        if owner_type in public_symbols:
            symbols.add(owner_type)
            methods.add(f"{owner_type}.{node.func.attr}")

    return {
        "api_symbols": sorted(symbols),
        "api_methods": sorted(methods),
    }


def enrich_case_with_api_context(
    case: dict[str, Any],
    *,
    manim_version: str,
    python_version: str,
    renderer: str,
    public_symbols: set[str],
) -> dict[str, Any]:
    enriched = dict(case)
    enriched["system"] = versioned_system_prompt(manim_version)
    enriched["manim_version"] = manim_version
    enriched["python_version"] = python_version
    enriched["renderers_tested"] = [renderer]
    enriched["corpus_roles"] = infer_corpus_roles(case)
    enriched.update(extract_api_usage(str(case["completion"]), public_symbols))
    return enriched


def infer_corpus_roles(case: dict[str, Any]) -> list[str]:
    tags = set(case.get("tags", []))
    source_url = str(case.get("source_url") or "")
    roles: list[str] = []
    is_reference = bool(
        {"docs", "repo-import"} & tags
        or "docs.manim.community" in source_url
        or "source:repo" in tags
    )
    if is_reference:
        roles.append("api_reference")
    else:
        roles.append("pedagogical")
    if (
        {"composite", "fusion", "longform", "targeted"} & tags
        or int(case.get("target_duration_seconds") or 0) >= 25
    ):
        roles.append("composite")
    return roles


def build_api_coverage(
    cases: Iterable[dict[str, Any]],
    *,
    public_symbols: set[str],
) -> dict[str, Any]:
    symbol_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    method_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        for symbol in case.get("api_symbols", []):
            symbol_rows[symbol].append(case)
        for method in case.get("api_methods", []):
            method_rows[method].append(case)

    used_symbols = set(symbol_rows)
    return {
        "symbols": {
            symbol: _coverage_entry(rows)
            for symbol, rows in sorted(symbol_rows.items())
        },
        "methods": {
            method: _coverage_entry(rows)
            for method, rows in sorted(method_rows.items())
        },
        "unused_public_symbols": sorted(public_symbols - used_symbols),
        "summary": {
            "public_symbols": len(public_symbols),
            "used_symbols": len(used_symbols),
            "used_methods": len(method_rows),
        },
    }


def _coverage_entry(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "examples": len(rows),
        "case_ids": sorted(row["case_id"] for row in rows),
        "domains": sorted({str(row.get("source_domain") or "unknown") for row in rows}),
        "roles": sorted({role for row in rows for role in row.get("corpus_roles", [])}),
        "split_groups": len({row.get("split_group") for row in rows}),
    }


def _infer_variable_types(tree: ast.AST, public_symbols: set[str]) -> dict[str, str]:
    variable_types: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        inferred = _infer_expression_type(value, variable_types, public_symbols)
        if not inferred:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                variable_types[target.id] = inferred
    return variable_types


def _infer_expression_type(
    node: ast.AST,
    variable_types: dict[str, str],
    public_symbols: set[str],
) -> str:
    if isinstance(node, ast.Name):
        if node.id in public_symbols:
            return node.id
        return variable_types.get(node.id, "")
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in public_symbols:
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return _infer_expression_type(node.func.value, variable_types, public_symbols)
    if isinstance(node, ast.Attribute):
        return _infer_expression_type(node.value, variable_types, public_symbols)
    return ""


def _expression_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""
