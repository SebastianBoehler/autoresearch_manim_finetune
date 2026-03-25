from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from mac_pipeline.utils import ensure_dir


def render_review_candidate(
    *,
    code: str,
    scene_name: str | None,
    output_dir: Path,
    quality: str,
    timeout_seconds: int,
) -> dict[str, object]:
    ensure_dir(output_dir)
    script_path = output_dir / "scene.py"
    log_path = output_dir / "render.log"
    video_path = output_dir / "scene.mp4"
    script_path.write_text(code)

    if video_path.exists():
        return {
            "render_ok": True,
            "video_path": video_path,
            "script_path": script_path,
            "log_path": log_path if log_path.exists() else None,
            "render_log_tail": log_path.read_text()[-4000:] if log_path.exists() else "",
        }

    if not scene_name:
        log_path.write_text("Missing scene_name; cannot render candidate.\n")
        return {
            "render_ok": False,
            "video_path": None,
            "script_path": script_path,
            "log_path": log_path,
            "render_log_tail": "Missing scene_name; cannot render candidate.",
        }

    media_dir = ensure_dir(output_dir / "media")
    quality_flag = {"low": "-ql", "medium": "-qm", "high": "-qh"}.get(quality, "-ql")
    command = [
        sys.executable,
        "-m",
        "manim",
        quality_flag,
        "--disable_caching",
        "--media_dir",
        str(media_dir),
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
        output = (result.stdout + "\n" + result.stderr).strip()
    except subprocess.TimeoutExpired:
        output = f"render timed out after {timeout_seconds}s"
        log_path.write_text(output + "\n")
        return {
            "render_ok": False,
            "video_path": None,
            "script_path": script_path,
            "log_path": log_path,
            "render_log_tail": output,
        }

    log_path.write_text(output + "\n")
    source_video = _find_rendered_video(media_dir, scene_name)
    if result.returncode == 0 and source_video is not None:
        shutil.copy2(source_video, video_path)
        return {
            "render_ok": True,
            "video_path": video_path,
            "script_path": script_path,
            "log_path": log_path,
            "render_log_tail": output[-4000:],
        }
    return {
        "render_ok": False,
        "video_path": None,
        "script_path": script_path,
        "log_path": log_path,
        "render_log_tail": output[-4000:],
    }


def _find_rendered_video(media_dir: Path, scene_name: str) -> Path | None:
    preferred = sorted(media_dir.glob(f"**/{scene_name}.mp4"))
    if preferred:
        return preferred[0]
    fallback = sorted(media_dir.glob("**/*.mp4"))
    return fallback[0] if fallback else None
