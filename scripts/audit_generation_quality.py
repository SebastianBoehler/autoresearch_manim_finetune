from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mac_pipeline.generation_quality import analyze_generation_quality
from mac_pipeline.utils import write_json


def audit_eval_file(input_path: Path, output_path: Path) -> dict:
    payload = json.loads(input_path.read_text())
    cases = []
    for case in payload.get("cases", []):
        code = case.get("final_code") or case.get("code") or case.get("generated_code") or ""
        report = analyze_generation_quality(code).to_dict()
        cases.append(
            {
                "case_id": case.get("case_id"),
                "syntax_ok": case.get("syntax_ok"),
                "render_ok": case.get("render_ok"),
                "weighted_score": case.get("weighted_score"),
                "quality": report,
            }
        )
    warning_counts: dict[str, int] = {}
    for case in cases:
        for warning in case["quality"]["warnings"]:
            warning_counts[warning] = warning_counts.get(warning, 0) + 1
    result = {
        "input_path": str(input_path),
        "num_cases": len(cases),
        "warning_counts": warning_counts,
        "cases": cases,
    }
    write_json(output_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = audit_eval_file(Path(args.input).resolve(), Path(args.output).resolve())
    print(json.dumps({"num_cases": result["num_cases"], "warning_counts": result["warning_counts"]}, indent=2))


if __name__ == "__main__":
    main()
