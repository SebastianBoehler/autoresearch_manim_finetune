from __future__ import annotations

import json
from pathlib import Path

SYSTEM = (
    "You write runnable Manim Community Edition Python files. Return only Python code, "
    "use `from manim import *`, and define exactly one scene class."
)


def main() -> None:
    output_dir = Path("artifacts/datasets/category-balanced-fresh-eval")
    output_dir.mkdir(parents=True, exist_ok=True)
    records = [_record(*case) for case in _cases()]
    (output_dir / "test.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records)
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "purpose": "fresh raw generation benchmark, not training data",
                "counts": {"test": len(records)},
                "source": "scripts/build_category_balanced_fresh_eval.py",
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"output_dir": str(output_dir), "num_records": len(records)}, indent=2))


def _record(
    case_id: str,
    prompt: str,
    tags: list[str],
    must_contain: list[str],
    must_not_contain: list[str],
) -> dict:
    return {
        "case_id": case_id,
        "system": SYSTEM,
        "prompt": prompt,
        "tags": ["fresh-eval", *tags],
        "entry_scene": None,
        "must_contain": must_contain,
        "must_not_contain": [
            ", opacity=",
            "alpha=",
            "tick_frequency=",
            "axis.c2p(",
            "ORANGE_D",
            *must_not_contain,
        ],
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
    }


def _cases() -> list[tuple[str, str, list[str], list[str], list[str]]]:
    return [
        (
            "fresh_binary_search_interval_band",
            "Create a concise Manim scene that shows binary search narrowing a NumberLine interval from [0, 16] to [8, 12]. Use translucent interval bands and label the kept half.",
            ["math", "algorithm", "numberline", "duration:10s"],
            ["NumberLine(", "Rectangle(", "fill_opacity=", ".n2p("],
            [],
        ),
        (
            "fresh_fraction_equivalence_panel",
            "Create a Manim scene that compares 1/2 and 2/4 on the same unit interval with colored segments and fraction labels.",
            ["math", "fraction", "numberline", "duration:10s"],
            ["NumberLine(", "MathTex(", "Line(", ".n2p("],
            [],
        ),
        (
            "fresh_confidence_interval_axis_band",
            "Create a Manim scene explaining a confidence interval on a horizontal axis with an estimate dot, a filled uncertainty band, and a short caption.",
            ["statistics", "confidence-interval", "duration:10s"],
            ["NumberLine(", "Dot(", "Rectangle(", "fill_opacity="],
            [],
        ),
        (
            "fresh_matrix_entry_update_panel",
            "Create a Manim scene showing one entry in a 2x2 matrix being updated, with a separate background panel and a highlighted cell.",
            ["math", "matrix", "highlight", "duration:10s"],
            ["Matrix(", "BackgroundRectangle(", "SurroundingRectangle("],
            ["background_color="],
        ),
        (
            "fresh_finance_dca_comparison",
            "Create a Manim scene comparing lump-sum investing and dollar-cost averaging using two simple line graphs and a clean explanatory side label.",
            ["finance", "graph", "duration:15s"],
            ["Axes(", "plot_line_graph(", "Text("],
            [],
        ),
        (
            "fresh_chem_titration_threshold",
            "Create a Manim scene showing titration pH rising toward an equivalence threshold with a graph, a vertical threshold line, and a tracker label.",
            ["chemistry", "graph", "tracker", "duration:15s"],
            ["Axes(", "ValueTracker(", "always_redraw("],
            [],
        ),
        (
            "fresh_ml_activation_comparison",
            "Create a Manim scene comparing sigmoid and ReLU activations with two plotted curves and labels that do not overlap the graph.",
            ["ml", "activation", "graph", "duration:10s"],
            ["Axes(", "plot(", "MathTex("],
            [],
        ),
        (
            "fresh_3d_surface_camera_panel",
            "Create a Manim ThreeDScene with axes, a smooth surface, and a fixed text label describing the camera angle.",
            ["docs", "3d", "surface", "duration:10s"],
            ["ThreeDScene", "ThreeDAxes(", "Surface(", "add_fixed_in_frame_mobjects("],
            [],
        ),
    ]


if __name__ == "__main__":
    main()
