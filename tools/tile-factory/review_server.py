#!/usr/bin/env python3
"""Local HTTP server for tile set review and approval.

Run from repo root:
  python3 tools/tile-factory/review_server.py
  python3 tools/tile-factory/review_server.py --port 8768

Map preview (gallery) needs Pillow — use the tile-factory venv if system python has no PIL:
  tools/tile-factory/.venv/bin/python3 tools/tile-factory/review_server.py

Open http://127.0.0.1:8768/
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import threading
import uuid
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import TCPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "tools"
SCRIPTS = Path(__file__).resolve().parent / "scripts"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from review_lib import (  # noqa: E402
    approve_tile,
    build_mosaic,
    discover_sets,
    get_prompt_detail,
    list_tiles,
    run_regenerate_tile,
    save_prompt_layers,
)
from tile_texture_http import handle_tile_texture_get  # noqa: E402

_REGEN_JOBS: dict[str, dict[str, Any]] = {}
_REGEN_LOCK = threading.Lock()

REVIEW_DIR = Path(__file__).resolve().parent / "review"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8768


def _json(handler: SimpleHTTPRequestHandler, status: int, payload: object) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


class ReviewHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        if args and str(args[0]).startswith("GET /assets"):
            return
        super().log_message(fmt, *args)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if handle_tile_texture_get(self, path, qs, json_response=_json):
            return

        if path == "/api/sets":
            _json(self, 200, {"sets": discover_sets()})
            return

        if path == "/api/tiles":
            biome = (qs.get("biome") or [""])[0]
            season = (qs.get("season") or [""])[0]
            pool = (qs.get("pool") or ["pending"])[0]
            var_raw = (qs.get("variation") or [""])[0]
            variation: int | None = None
            if var_raw and var_raw != "all":
                try:
                    variation = int(var_raw)
                except ValueError:
                    _json(self, 400, {"error": "invalid variation"})
                    return
            gen_raw = (qs.get("generation") or [""])[0]
            generation: int | None = None
            if gen_raw:
                try:
                    generation = int(gen_raw)
                except ValueError:
                    _json(self, 400, {"error": "invalid generation"})
                    return
            if not biome or not season:
                _json(self, 400, {"error": "biome and season required"})
                return
            _json(
                self,
                200,
                {"tiles": list_tiles(biome, season, pool=pool, variation=variation, generation=generation)},
            )
            return

        if path == "/api/prompt":
            tid = (qs.get("id") or [""])[0].strip()
            if not tid:
                _json(self, 400, {"error": "id required"})
                return
            try:
                _json(self, 200, get_prompt_detail(tid))
            except FileNotFoundError as exc:
                _json(self, 404, {"error": str(exc)})
            except Exception as exc:
                _json(self, 500, {"error": str(exc)})
            return

        if path.startswith("/api/regenerate/"):
            job_id = path.removeprefix("/api/regenerate/").strip("/")
            with _REGEN_LOCK:
                job = _REGEN_JOBS.get(job_id)
            if job is None:
                _json(self, 404, {"error": "unknown job"})
                return
            _json(self, 200, job)
            return

        if path == "/api/mosaic":
            biome = (qs.get("biome") or [""])[0]
            season = (qs.get("season") or [""])[0]
            pool = (qs.get("pool") or ["pending"])[0]
            try:
                variation = int((qs.get("variation") or ["1"])[0])
            except ValueError:
                _json(self, 400, {"error": "invalid variation"})
                return
            gen_raw = (qs.get("generation") or [""])[0]
            generation: int | None = None
            if gen_raw:
                try:
                    generation = int(gen_raw)
                except ValueError:
                    _json(self, 400, {"error": "invalid generation"})
                    return
            if not biome or not season:
                _json(self, 400, {"error": "biome and season required"})
                return
            _json(self, 200, build_mosaic(biome, season, variation, pool=pool, generation=generation))
            return

        if path.startswith("/assets/"):
            rel = path.removeprefix("/assets/")
            file_path = (REPO_ROOT / "assets" / rel).resolve()
            assets_root = (REPO_ROOT / "assets").resolve()
            if not str(file_path).startswith(str(assets_root)) or not file_path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            ctype, _ = mimetypes.guess_type(str(file_path))
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", ctype or "application/octet-stream")
            self.send_header("Content-Length", str(file_path.stat().st_size))
            self.end_headers()
            self.wfile.write(file_path.read_bytes())
            return

        if path in ("/", "/index.html"):
            index = REVIEW_DIR / "index.html"
            if index.is_file():
                self._serve_file(index)
                return

        rel = path.lstrip("/").split("?")[0]
        static = (REVIEW_DIR / rel).resolve()
        if str(static).startswith(str(REVIEW_DIR.resolve())) and static.is_file():
            self._serve_file(static)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/prompt":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = self._read_json_body()
        if body is None:
            return
        tid = str(body.get("id", "")).strip()
        if not tid:
            _json(self, 400, {"ok": False, "error": "id required"})
            return
        layers_in = body.get("layers")
        layers = layers_in if isinstance(layers_in, dict) else None
        try:
            detail = save_prompt_layers(
                tid,
                layers,
                generation_prompt=body.get("generation_prompt"),
                clear_full_override=bool(body.get("clear_full_override")),
            )
            _json(self, 200, {"ok": True, "prompt": detail})
        except FileNotFoundError as exc:
            _json(self, 404, {"ok": False, "error": str(exc)})
        except Exception as exc:
            print(f"save prompt {tid} error: {exc}", flush=True)
            _json(self, 500, {"ok": False, "error": str(exc)})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/regenerate":
            body = self._read_json_body()
            if body is None:
                return
            tid = str(body.get("id", "")).strip()
            if not tid:
                _json(self, 400, {"ok": False, "error": "id required"})
                return
            job_id = str(uuid.uuid4())
            with _REGEN_LOCK:
                _REGEN_JOBS[job_id] = {
                    "job_id": job_id,
                    "tile_id": tid,
                    "status": "running",
                    "log": "",
                    "ok": None,
                }

            def _work() -> None:
                try:
                    result = run_regenerate_tile(tid)
                    status = "done" if result.get("ok") else "failed"
                    payload = {
                        "job_id": job_id,
                        "tile_id": tid,
                        "status": status,
                        "log": str(result.get("log", "")),
                        "ok": bool(result.get("ok")),
                    }
                except Exception as exc:
                    payload = {
                        "job_id": job_id,
                        "tile_id": tid,
                        "status": "failed",
                        "log": str(exc),
                        "ok": False,
                    }
                with _REGEN_LOCK:
                    _REGEN_JOBS[job_id] = payload

            threading.Thread(target=_work, daemon=True).start()
            _json(self, 202, {"ok": True, "job_id": job_id, "status": "running"})
            return
        if parsed.path != "/api/approve":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = self._read_json_body()
        if body is None:
            return
        tid = str(body.get("id", "")).strip()
        if not tid:
            _json(self, 400, {"ok": False, "error": "id required"})
            return
        try:
            result = approve_tile(tid)
        except Exception as exc:
            print(f"approve {tid} error: {exc}", flush=True)
            _json(self, 500, {"ok": False, "error": str(exc)})
            return
        _json(self, 200 if result.get("ok") else 400, result)

    def _read_json_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
            return body if isinstance(body, dict) else {}
        except json.JSONDecodeError:
            _json(self, 400, {"ok": False, "error": "invalid JSON"})
            return None

    def _serve_file(self, file_path: Path) -> None:
        ctype, _ = mimetypes.guess_type(str(file_path))
        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype or "text/html")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    class Server(TCPServer):
        allow_reuse_address = True

    venv_py = REPO_ROOT / "tools" / "tile-factory" / ".venv" / "bin" / "python3"
    try:
        import PIL  # noqa: F401

        print("Map preview: Pillow available.")
    except ImportError:
        print("Tile review: OK without Pillow.")
        if venv_py.is_file():
            print(f"Map preview: use {venv_py.relative_to(REPO_ROOT)} (Pillow installed there).")
        else:
            print("Map preview: pip install -r tools/tile-factory/requirements.txt (Pillow).")

    with Server((args.host, args.port), ReviewHandler) as httpd:
        url = f"http://{args.host}:{args.port}/"
        print(f"Tile review server at {url}")
        print(f"Map preview gallery: {url}tile-texture-gallery.html")
        print("Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
