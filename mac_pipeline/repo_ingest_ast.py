from __future__ import annotations

import ast

SCENE_BASES = {"Scene", "ThreeDScene", "MovingCameraScene", "ZoomedScene"}


def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def scene_classes(tree: ast.AST) -> list[str]:
    classes: list[str] = []
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.ClassDef) and any(_base_name(base) in SCENE_BASES for base in node.bases):
            classes.append(node.name)
    return classes


def collect_imports(tree: ast.AST) -> tuple[list[str], list[str]]:
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


def extract_scene_module(code: str, scene_name: str) -> str:
    tree = ast.parse(code)
    selected: list[ast.stmt] = []
    module_docstring = ast.get_docstring(tree, clean=False)
    if module_docstring:
        selected.append(ast.Expr(value=ast.Constant(value=module_docstring)))

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            selected.append(node)
            continue
        if isinstance(node, ast.ClassDef) and any(_base_name(base) in SCENE_BASES for base in node.bases):
            if node.name == scene_name:
                selected.append(node)
            continue
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.Assign,
                ast.AnnAssign,
                ast.AugAssign,
                ast.ClassDef,
                ast.Try,
                ast.With,
                ast.If,
            ),
        ):
            selected.append(node)

    module = ast.Module(body=selected, type_ignores=[])
    module = ast.fix_missing_locations(module)
    return ast.unparse(module).rstrip() + "\n"
