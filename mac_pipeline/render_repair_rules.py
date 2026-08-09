from __future__ import annotations

import re

_SURROUNDING_RECT_LINE = re.compile(
    r"^(\s*)([A-Za-z_]\w*\s*=\s*)SurroundingRectangle\((.*)\)\s*$"
)


def repair_surrounding_rectangle_point_line(line: str) -> str:
    newline = "\n" if line.endswith("\n") else ""
    body = line[:-1] if newline else line
    match = _SURROUNDING_RECT_LINE.match(body)
    if match is None:
        return line

    first_arg, kwargs = _split_first_arg(match.group(3))
    if first_arg is None or not _looks_like_point_expression(first_arg):
        return line

    width = kwargs.pop("width", "0.5")
    height = kwargs.pop("height", "0.5")
    kwargs.pop("buff", None)
    rectangle_args = [f"width={width}", f"height={height}"]
    for key in ("color", "stroke_color", "fill_color", "fill_opacity", "stroke_opacity"):
        if key in kwargs:
            rectangle_args.append(f"{key}={kwargs[key]}")
    return (
        f"{match.group(1)}{match.group(2)}Rectangle("
        f"{', '.join(rectangle_args)}).move_to({first_arg}){newline}"
    )


def repair_number_range_between(line: str) -> str:
    pattern = re.compile(
        r"^(\s*)([A-Za-z_]\w*\s*=\s*)([A-Za-z_]\w*)\.number_range_between\(([^,]+),\s*([^)]+)\)\s*$"
    )
    newline = "\n" if line.endswith("\n") else ""
    body = line[:-1] if newline else line
    match = pattern.match(body)
    if match is None:
        return line
    receiver = match.group(3)
    start = match.group(4).strip()
    end = match.group(5).strip()
    return (
        f"{match.group(1)}{match.group(2)}["
        f"{receiver}.number_to_point({start}), {receiver}.number_to_point({end})]"
        f"{newline}"
    )


def remove_constructor_kwarg(line: str, constructor: str, kwarg: str) -> str:
    marker = f"{constructor}("
    start = line.find(marker)
    if start == -1 or f"{kwarg}=" not in line:
        return line
    args_start = start + len(marker)
    args_end = _find_matching_paren(line, args_start - 1)
    if args_end is None:
        return line
    args = line[args_start:args_end]
    parts = [part for part in _split_top_level(args) if not part.strip().startswith(f"{kwarg}=")]
    return line[:args_start] + ", ".join(parts) + line[args_end:]


def remove_repeated_kwarg(line: str, kwarg: str) -> str:
    matches = list(re.finditer(rf"{kwarg}\s*=", line))
    if len(matches) < 2:
        return line
    updated = line
    for match in reversed(matches[1:]):
        start = updated.rfind(",", 0, match.start())
        end = _kwarg_value_end(updated, match.end())
        if start == -1:
            continue
        updated = updated[:start] + updated[end:]
    return updated


def repair_matrix_set_matrix(line: str) -> str:
    return re.sub(
        r"(\b[A-Za-z_]\w*)\.animate\.set_matrix\(\[\[[^\n]*?\]\]\)",
        r"\1.animate.set_opacity(0.9)",
        line,
    )


def repair_curve_getters(line: str) -> str:
    updated = re.sub(
        r"\b[A-Za-z_]\w*\.get_y1\([^)]*\)\s*-\s*\b[A-Za-z_]\w*\.get_y0\([^)]*\)",
        "1.0",
        line,
    )
    updated = re.sub(r"\b[A-Za-z_]\w*\.get_y0\([^)]*\)", "0.5", updated)
    return re.sub(r"\b[A-Za-z_]\w*\.get_y1\([^)]*\)", "1.5", updated)


def repair_equilibrium_readouts(line: str) -> str:
    updated = line.replace("equilibrium_curve", "demand_curve")
    if "DecimalNumber(" not in updated:
        return updated
    if ".get_y(" in updated:
        return _replace_decimal_first_arg(updated, "2.8")
    if ".x_data[0]" in updated:
        return _replace_decimal_first_arg(updated, "5.0")
    return updated


def _replace_decimal_first_arg(line: str, value: str) -> str:
    start = line.find("DecimalNumber(")
    if start == -1:
        return line
    args_start = start + len("DecimalNumber(")
    args_end = _find_matching_paren(line, args_start - 1)
    if args_end is None:
        return line
    parts = _split_top_level(line[args_start:args_end])
    if not parts:
        return line
    parts[0] = value
    return line[:args_start] + ", ".join(parts) + line[args_end:]


def _split_first_arg(args: str) -> tuple[str | None, dict[str, str]]:
    parts = _split_top_level(args)
    if not parts:
        return None, {}
    kwargs: dict[str, str] = {}
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        kwargs[key.strip()] = value.strip()
    return parts[0].strip(), kwargs


def _split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    for index, char in enumerate(text):
        if quote:
            if char == quote and text[index - 1 : index] != "\\":
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _looks_like_point_expression(expression: str) -> bool:
    return "number_to_point(" in expression or ".n2p(" in expression


def _kwarg_value_end(text: str, value_start: int) -> int:
    depth = 0
    quote: str | None = None
    for index in range(value_start, len(text)):
        char = text[index]
        if quote:
            if char == quote and text[index - 1 : index] != "\\":
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char in "([{":
            depth += 1
        elif char in ")]}":
            if depth == 0:
                return index
            depth -= 1
        elif char == "," and depth == 0:
            return index
    return len(text)


def _find_matching_paren(text: str, open_index: int) -> int | None:
    depth = 0
    quote: str | None = None
    for index in range(open_index, len(text)):
        char = text[index]
        if quote:
            if char == quote and text[index - 1 : index] != "\\":
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    return None
