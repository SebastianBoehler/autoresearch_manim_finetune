from __future__ import annotations

import re

_IMPLICIT_NUMERIC_MULTIPLY = re.compile(r"(?<=\d)([A-Za-z_]\w*)\b")


def repair_syntax_generated_code(code: str, syntax_error: str) -> tuple[str, list[str]]:
    if "invalid decimal literal" not in syntax_error:
        return code, []

    updated = _IMPLICIT_NUMERIC_MULTIPLY.sub(r"*\1", code)
    updated = re.sub(r"(?<![\w.])exp\(", "np.exp(", updated)
    updated = updated.replace("ShowCreation(", "Create(")
    updated, converted = _convert_lambda_vgroup_to_list(updated, "functions")

    notes: list[str] = []
    if updated != code:
        notes.append("repair invalid numeric expression syntax")
    if converted:
        notes.append("rewrite lambda VGroup as plain function list")
    return updated, notes


def _convert_lambda_vgroup_to_list(code: str, variable: str) -> tuple[str, bool]:
    lines = code.splitlines(keepends=True)
    output: list[str] = []
    in_block = False
    base_indent = ""
    converted = False
    start_pattern = re.compile(rf"^(\s*){variable}\s*=\s*VGroup\(\s*$")

    for line in lines:
        if not in_block:
            match = start_pattern.match(line)
            if match:
                base_indent = match.group(1)
                output.append(f"{base_indent}{variable} = [\n")
                in_block = True
                converted = True
                continue
            output.append(line)
            continue

        if line.strip() == ")" and line.startswith(base_indent):
            output.append(f"{base_indent}]\n")
            in_block = False
            continue
        output.append(line)

    return "".join(output), converted
