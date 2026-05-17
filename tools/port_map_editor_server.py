#!/usr/bin/env python3
"""Local HTTP server for the port map coordinate editor.

Run from repo root:
  python3 tools/port_map_editor_server.py

Then open http://127.0.0.1:8765/
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import TCPServer
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = REPO_ROOT / "tools" / "port_map_editor"
DOCS_MAPS = REPO_ROOT / "docs" / "chart_area_tilemaps_and_maps"
WORLD_PATH = REPO_ROOT / "data" / "world_full.json"
EXPORT_PATH = REPO_ROOT / "data" / "port_map_editor_export.json"
CHART_INDEX_PATH = DOCS_MAPS / "chart_area_index.json"

HOST = os.environ.get("PORT_MAP_EDITOR_HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT_MAP_EDITOR_PORT", "8765"))

# Source of truth on load: data/world_full.json only. Set to 1 to overlay export file (legacy).
MERGE_EXPORT_ON_LOAD = os.environ.get("PORT_MAP_EDITOR_MERGE_EXPORT", "").strip() in ("1", "true", "yes")


def _json_response(handler: SimpleHTTPRequestHandler, status: int, payload: object) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(path: Path) -> object:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _load_ports() -> list[dict]:
    world = _read_json(WORLD_PATH)
    ports: list[dict] = []
    for p in world.get("ports", []):
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id", ""))
        if not pid:
            continue
        mu = p.get("map_u")
        mv = p.get("map_v")
        ports.append(
            {
                "id": pid,
                "name": str(p.get("name", pid)),
                "chart_area_id": str(p.get("chart_area_id", "")),
                "map_u": float(mu) if mu is not None else None,
                "map_v": float(mv) if mv is not None else None,
            }
        )
    return ports


def _merge_export(ports: list[dict]) -> list[dict]:
    if not EXPORT_PATH.is_file():
        return ports
    try:
        export = _read_json(EXPORT_PATH)
    except (OSError, json.JSONDecodeError):
        return ports
    edits = export.get("edits", [])
    if not isinstance(edits, list):
        return ports
    by_id = {p["id"]: dict(p) for p in ports}
    for e in edits:
        if not isinstance(e, dict):
            continue
        pid = str(e.get("id", ""))
        if pid not in by_id:
            continue
        if e.get("map_u") is not None:
            by_id[pid]["map_u"] = float(e["map_u"])
        if e.get("map_v") is not None:
            by_id[pid]["map_v"] = float(e["map_v"])
    return list(by_id.values())


class PortMapEditorHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/bootstrap":
            try:
                index = _read_json(CHART_INDEX_PATH)
                areas = index.get("chart_areas", [])
                ports = _load_ports()
                merge_export = MERGE_EXPORT_ON_LOAD or (
                    parsed.query.strip() in ("merge_export=1", "merge_export=true")
                )
                if merge_export:
                    ports = _merge_export(ports)
                export_exists = EXPORT_PATH.is_file()
                _json_response(
                    self,
                    HTTPStatus.OK,
                    {
                        "chart_areas": areas,
                        "ports": ports,
                        "source": "world_full.json"
                        + (" + port_map_editor_export.json" if merge_export else ""),
                        "export_path": str(EXPORT_PATH.relative_to(REPO_ROOT)),
                        "export_exists": export_exists,
                        "merge_export_on_load": merge_export,
                        "global_grid_width": 2000,
                        "global_grid_height": 1000,
                    },
                )
            except OSError as exc:
                _json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        if path.startswith("/api/tilemap/"):
            area_id = path.removeprefix("/api/tilemap/").strip("/")
            if not area_id or ".." in area_id:
                _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "invalid area id"})
                return
            tilemap_path = DOCS_MAPS / f"{area_id}_tilemap.json"
            if not tilemap_path.is_file():
                _json_response(self, HTTPStatus.NOT_FOUND, {"error": "tilemap not found"})
                return
            try:
                data = _read_json(tilemap_path)
                _json_response(self, HTTPStatus.OK, data)
            except OSError as exc:
                _json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        if path in ("", "/"):
            self.path = "/index.html"
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/export":
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "invalid JSON body"})
            return

        edits = body.get("edits")
        if not isinstance(edits, list):
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "edits must be an array"})
            return

        payload = {
            "schema_version": 1,
            "description": (
                "Port map_u/map_v from port_map_editor. Merge into data/world_full.json ports[] by id."
            ),
            "global_grid_width": 2000,
            "global_grid_height": 1000,
            "shore_snap_rule": "partial_coast_tiles_excluding_totally_sea_and_totally_land",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "edits": edits,
        }
        try:
            EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            with EXPORT_PATH.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
                f.write("\n")
        except OSError as exc:
            _json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        _json_response(
            self,
            HTTPStatus.OK,
            {
                "ok": True,
                "path": str(EXPORT_PATH.relative_to(REPO_ROOT)),
                "count": len(edits),
            },
        )


def main() -> None:
    if not STATIC_DIR.is_dir():
        raise SystemExit(f"Missing static dir: {STATIC_DIR}")
    os.chdir(STATIC_DIR)
    with TCPServer((HOST, PORT), PortMapEditorHandler) as httpd:
        url = f"http://{HOST}:{PORT}/"
        print(f"Port map editor at {url}")
        print(f"Export file: {EXPORT_PATH}")
        print("Ctrl+C to stop.")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
