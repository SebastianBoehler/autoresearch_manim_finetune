from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mac_pipeline.utils import ensure_parent, load_records

STATIC_DIR = Path(__file__).resolve().parent / "static"


def serve_review_app(*, session_dir: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    session_path = session_dir / "session.json"
    ratings_path = session_dir / "ratings.jsonl"
    if not session_path.exists():
        raise FileNotFoundError(f"Missing review session: {session_path}")

    class ReviewHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/session":
                session = json.loads(session_path.read_text())
                ratings = _load_ratings(ratings_path)
                self._send_json(_public_session(session, ratings))
                return
            if parsed.path.startswith("/session/"):
                self._serve_file(session_dir / parsed.path.removeprefix("/session/"))
                return
            asset_path = STATIC_DIR / ("index.html" if parsed.path == "/" else parsed.path.lstrip("/"))
            self._serve_file(asset_path)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/ratings":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            session = json.loads(session_path.read_text())
            ratings = _load_ratings(ratings_path)
            payload = self._read_json()
            review_id = payload.get("review_id")
            if not isinstance(review_id, str):
                self.send_error(HTTPStatus.BAD_REQUEST, "review_id is required")
                return
            if review_id in {rating["review_id"] for rating in ratings}:
                self.send_error(HTTPStatus.CONFLICT, "review already exists")
                return
            item = next((entry for entry in session["items"] if entry["review_id"] == review_id), None)
            if item is None:
                self.send_error(HTTPStatus.NOT_FOUND, "review item not found")
                return
            try:
                record = _rating_record(item, payload)
            except ValueError as exc:
                self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            ensure_parent(ratings_path)
            with ratings_path.open("a") as handle:
                handle.write(json.dumps(record) + "\n")
            self._send_json({"ok": True, "record": record}, status=HTTPStatus.CREATED)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

        def _read_json(self) -> dict[str, Any]:
            size = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(size).decode("utf-8") if size else "{}"
            return json.loads(body or "{}")

        def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _serve_file(self, path: Path) -> None:
            if not path.exists() or not path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            data = path.read_bytes()
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer((host, port), ReviewHandler)
    print(f"Serving blind review app for {session_dir} at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _load_ratings(path: Path) -> list[dict[str, Any]]:
    return load_records(path) if path.exists() else []


def _public_session(session: dict[str, Any], ratings: list[dict[str, Any]]) -> dict[str, Any]:
    rated_ids = {rating["review_id"] for rating in ratings}
    items = []
    for item in session["items"]:
        options = []
        for option in item["options"]:
            options.append(
                {
                    "slot": option["slot"],
                    "render_ok": option["render_ok"],
                    "scene_name": option["scene_name"],
                    "video_url": f"/session/{option['video_relpath']}" if option["video_relpath"] else None,
                    "render_log_tail": option["render_log_tail"],
                }
            )
        items.append(
            {
                "review_id": item["review_id"],
                "case_id": item["case_id"],
                "prompt": item["prompt"],
                "rated": item["review_id"] in rated_ids,
                "options": options,
            }
        )
    return {
        "session_name": session["session_name"],
        "created_at": session["created_at"],
        "total": len(items),
        "rated": len(rated_ids),
        "remaining": max(len(items) - len(rated_ids), 0),
        "items": items,
    }


def _rating_record(item: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    verdict = payload.get("verdict")
    if verdict not in {"A", "B", "both_good", "both_bad", "skip"}:
        raise ValueError("invalid verdict")
    slot_map = {option["slot"]: option for option in item["options"]}
    preferred = slot_map.get(verdict) if verdict in {"A", "B"} else None
    return {
        "review_id": item["review_id"],
        "case_id": item["case_id"],
        "prompt": item["prompt"],
        "verdict": verdict,
        "confidence": payload.get("confidence"),
        "notes": payload.get("notes", "").strip(),
        "slot_a_label": slot_map["A"]["label"],
        "slot_b_label": slot_map["B"]["label"],
        "slot_a_render_ok": slot_map["A"]["render_ok"],
        "slot_b_render_ok": slot_map["B"]["render_ok"],
        "preferred_label": preferred["label"] if preferred else None,
        "preferred_slot": preferred["slot"] if preferred else None,
    }
