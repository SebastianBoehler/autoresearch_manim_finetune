from __future__ import annotations

from pathlib import Path

from mac_pipeline.review import (
    build_review_session,
    promote_candidate_cases,
    render_candidate_cases,
    serve_review_app,
)


def cmd_build_review_session(args) -> None:
    payload = build_review_session(
        left_eval_path=Path(args.left).resolve(),
        right_eval_path=Path(args.right).resolve(),
        output_dir=Path(args.output_dir).resolve(),
        left_label=args.left_label,
        right_label=args.right_label,
        seed=args.seed,
        limit=args.limit,
        quality=args.quality,
        timeout_seconds=args.timeout_seconds,
        include_failed_renders=args.include_failed_renders,
    )
    print(f"Review session written to {Path(args.output_dir).resolve() / 'session.json'}")
    print(f"Ready items: {len(payload['items'])}")
    print(f"Skipped items: {len(payload['skipped'])}")


def cmd_serve_review_app(args) -> None:
    serve_review_app(
        session_dir=Path(args.session_dir).resolve(),
        host=args.host,
        port=args.port,
    )


def cmd_render_review_candidates(args) -> None:
    payload = render_candidate_cases(
        input_path=Path(args.input).resolve(),
        output_dir=Path(args.output_dir).resolve(),
        quality=args.quality,
        timeout_seconds=args.timeout_seconds,
    )
    print(f"Candidate render summary written to {Path(args.output_dir).resolve() / 'summary.json'}")
    print(f"Rendered {payload['num_rendered']} / {payload['num_cases']} cases successfully")


def cmd_promote_review_candidates(args) -> None:
    payload = promote_candidate_cases(
        input_path=Path(args.input).resolve(),
        review_path=Path(args.review).resolve(),
        promoted_path=Path(args.promoted_output).resolve(),
        remove_promoted=not args.keep_promoted_in_input,
        promoted_tier=args.promoted_tier,
    )
    print(f"Promoted {payload['num_promoted']} candidates into {Path(args.promoted_output).resolve()}")
    print(f"Canonical dataset rebuilt at {payload['canonical_dataset_path']}")
