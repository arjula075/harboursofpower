#!/usr/bin/env python3
"""Local HTTP server for the 1px corner-Wang-16 port map editor.

Run from repo root:
  python3 tools/port_map_editor_wang16_1px_server.py
  python3 tools/port_map_editor_wang16_1px_server.py --port 8770

Or set the port via environment variable:
  PORT_MAP_EDITOR_WANG16_PORT=8770 python3 tools/port_map_editor_wang16_1px_server.py
"""
from __future__ import annotations

import argparse
import json
import math
import mimetypes
import os
import sys
from datetime import datetime, timezone
from functools import lru_cache
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import TCPServer
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

STATIC_DIR = REPO_ROOT / "tools" / "port_map_editor_wang16_1px"
TILE_SCRIPTS = REPO_ROOT / "tools" / "tile-factory" / "scripts"
if str(TILE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(TILE_SCRIPTS))
from tile_texture_http import handle_tile_texture_get  # noqa: E402
DOCS_MAPS = REPO_ROOT / "docs" / "chart_area_tilemaps_and_maps_wang16_1px"
WORLD_PATH = REPO_ROOT / "data" / "world_full.json"
EXPORT_PATH = REPO_ROOT / "data" / "port_map_editor_wang16_1px_export.json"
CHART_INDEX_PATH = DOCS_MAPS / "chart_area_index.json"
GLOBAL_MASK_PATH = REPO_ROOT / "docs" / "mediterranean_recursive_tilemap_wang16_1px_mask.png"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8766

MERGE_EXPORT_ON_LOAD = os.environ.get("PORT_MAP_EDITOR_WANG16_MERGE_EXPORT", "").strip() in (
    "1",
    "true",
    "yes",
)

FULL_LAND = "totally_land"
FULL_SEA = "totally_sea"
BUCKET_CELL = 32


def _is_shore(tile: str) -> bool:
    return tile not in (FULL_LAND, FULL_SEA)


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


class SnapIndex:
    """Spatial buckets for nearest shore / land snap at 1px resolution."""

    def __init__(self, tiles: list[dict], tile_size: int = 1) -> None:
        self.tile_size = tile_size
        half = tile_size / 2.0
        shore: list[tuple[float, float, str]] = []
        land: list[tuple[float, float, str]] = []
        for t in tiles:
            if not isinstance(t, dict):
                continue
            typ = str(t.get("tile", ""))
            cx = float(t["x"]) + half
            cy = float(t["y"]) + half
            if typ == FULL_LAND:
                land.append((cx, cy, typ))
            elif _is_shore(typ):
                shore.append((cx, cy, typ))
        self.shore_buckets = self._bucket(shore)
        self.land_buckets = self._bucket(land)
        self.shore_count = len(shore)
        self.land_count = len(land)

    @staticmethod
    def _bucket(points: list[tuple[float, float, str]]) -> dict[tuple[int, int], list[tuple[float, float, str]]]:
        buckets: dict[tuple[int, int], list[tuple[float, float, str]]] = {}
        for cx, cy, typ in points:
            key = (int(cx) // BUCKET_CELL, int(cy) // BUCKET_CELL)
            buckets.setdefault(key, []).append((cx, cy, typ))
        return buckets

    def nearest(self, gx: float, gy: float, inland: bool) -> tuple[float, float, str]:
        buckets = self.land_buckets if inland else self.shore_buckets
        if not buckets:
            return gx, gy, FULL_LAND if inland else "unknown"
        bx, by = int(gx) // BUCKET_CELL, int(gy) // BUCKET_CELL
        best_d = math.inf
        best: tuple[float, float, str] | None = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for cx, cy, typ in buckets.get((bx + dx, by + dy), []):
                    d = (cx - gx) ** 2 + (cy - gy) ** 2
                    if d < best_d:
                        best_d = d
                        best = (cx, cy, typ)
        if best is None:
            # Fallback: scan all (should not happen if buckets non-empty)
            pool = []
            for cell in buckets.values():
                pool.extend(cell)
            for cx, cy, typ in pool:
                d = (cx - gx) ** 2 + (cy - gy) ** 2
                if d < best_d:
                    best_d = d
                    best = (cx, cy, typ)
        return best if best else (gx, gy, FULL_LAND if inland else "unknown")


def clear_snap_cache() -> None:
    _snap_index_for_area.cache_clear()
    _load_global_land_mask.cache_clear()


def _snap_index_for_area_editing(area_id: str) -> SnapIndex:
    """Snap index using in-memory terrain session tiles when that area is dirty."""
    from terrain_edit_session import get_session

    session = get_session(area_id)
    if session is not None and session.dirty:
        return SnapIndex(session.tiles, tile_size=1)
    return _snap_index_for_area(area_id)


@lru_cache(maxsize=1)
def _load_global_land_mask():
    """Bool (LOG_H, LOG_W) land mask from the full-map mask PNG."""
    import numpy as np
    from PIL import Image

    if not GLOBAL_MASK_PATH.is_file():
        raise FileNotFoundError(GLOBAL_MASK_PATH)
    rgb = np.array(Image.open(GLOBAL_MASK_PATH).convert("RGB"))
    # land tan ≈ (180,160,120); sea ≈ (26,74,110)
    return (rgb[:, :, 0] > 140) & (rgb[:, :, 2] < 130)


def _snap_counts_from_tilemap_data(data: dict) -> tuple[int, int]:
    """Shore/land snap target counts without loading every tile into memory."""
    counts = data.get("tile_counts") or {}
    if not isinstance(counts, dict):
        return 0, 0
    land = int(counts.get(FULL_LAND, 0))
    shore = sum(int(v) for k, v in counts.items() if k not in (FULL_LAND, FULL_SEA))
    return shore, land


def _mask_version_token() -> str:
    if GLOBAL_MASK_PATH.is_file():
        return str(int(GLOBAL_MASK_PATH.stat().st_mtime))
    return "0"


def _render_area_map_png(bounds: dict) -> bytes:
    import io

    import numpy as np
    from PIL import Image

    land = _load_global_land_mask()
    x0, y0, x1, y1 = bounds["x0"], bounds["y0"], bounds["x1"], bounds["y1"]
    sub = land[y0:y1, x0:x1]
    img = np.zeros((sub.shape[0], sub.shape[1], 3), dtype=np.uint8)
    img[sub] = (190, 170, 130)
    img[~sub] = (30, 80, 120)
    buf = io.BytesIO()
    Image.fromarray(img, mode="RGB").save(buf, format="PNG")
    return buf.getvalue()


@lru_cache(maxsize=16)
def _snap_index_for_area(area_id: str) -> SnapIndex:
    tilemap_path = DOCS_MAPS / f"{area_id}_tilemap.json"
    data = _read_json(tilemap_path)
    tiles = data.get("tiles", [])
    if not isinstance(tiles, list):
        tiles = []
    tile_size = int(data.get("coordinate_system", {}).get("final_tile_size", 1))
    return SnapIndex(tiles, tile_size=tile_size)


class PortMapEditorWang16Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def end_headers(self) -> None:
        path = urlparse(self.path).path
        if path.endswith((".js", ".html", ".css")) or path in ("", "/", "/index.html"):
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if handle_tile_texture_get(self, path, parse_qs(parsed.query), json_response=_json_response):
            return

        if path == "/api/terrain/status":
            try:
                from terrain_edit_session import disk_terrain_save_status, list_dirty_area_ids

                dirty = list_dirty_area_ids()
                _json_response(
                    self,
                    HTTPStatus.OK,
                    {
                        "unsaved_sessions": dirty,
                        "disk": disk_terrain_save_status(),
                    },
                )
            except Exception as exc:
                _json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        if path == "/api/bootstrap":
            try:
                from terrain_edit_session import disk_terrain_save_status

                index = _read_json(CHART_INDEX_PATH)
                areas = index.get("chart_areas", [])
                ports = _load_ports()
                merge_export = MERGE_EXPORT_ON_LOAD or (
                    parsed.query.strip() in ("merge_export=1", "merge_export=true")
                )
                if merge_export:
                    ports = _merge_export(ports)
                _json_response(
                    self,
                    HTTPStatus.OK,
                    {
                        "chart_areas": areas,
                        "ports": ports,
                        "source": "world_full.json"
                        + (" + port_map_editor_wang16_1px_export.json" if merge_export else ""),
                        "export_path": str(EXPORT_PATH.relative_to(REPO_ROOT)),
                        "export_exists": EXPORT_PATH.is_file(),
                        "merge_export_on_load": merge_export,
                        "global_grid_width": 2000,
                        "global_grid_height": 1000,
                        "tilemap_set": "chart_area_tilemaps_and_maps_wang16_1px",
                        "final_tile_size": 1,
                        "shore_snap_rule": "corner_wang_coast_tiles_excluding_totally_sea_and_totally_land",
                        "basemap": "land_sea_mask_crop",
                        "mask_version": _mask_version_token(),
                        "mask_path": str(GLOBAL_MASK_PATH.relative_to(REPO_ROOT)),
                        "terrain_disk": disk_terrain_save_status(),
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
                index = _read_json(CHART_INDEX_PATH)
                bounds = None
                for a in index.get("chart_areas", []):
                    if isinstance(a, dict) and a.get("id") == area_id:
                        bounds = a.get("bounds")
                        break
                if bounds is None:
                    bounds = data.get("chart_bounds") or data.get("classification_pipeline", {}).get(
                        "chart_bounds"
                    )
                shore_n, land_n = _snap_counts_from_tilemap_data(data)
                counts = data.get("tile_counts") or {}
                _json_response(
                    self,
                    HTTPStatus.OK,
                    {
                        "chart_area_id": area_id,
                        "bounds": bounds,
                        "coordinate_system": data.get("coordinate_system"),
                        "tile_counts": counts,
                        "shore_snap_targets": shore_n,
                        "land_snap_targets": land_n,
                        "map_image_url": f"/api/map-image/{area_id}?v={_mask_version_token()}",
                    },
                )
            except Exception as exc:
                print(f"tilemap {area_id} error: {exc}")
                _json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        if path.startswith("/api/terrain/preview/"):
            area_id = path.removeprefix("/api/terrain/preview/").strip("/")
            if not area_id or ".." in area_id:
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            try:
                from terrain_edit_session import ensure_session, get_session, preview_png

                session = get_session(area_id) or ensure_session(area_id)
                body = preview_png(area_id)
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Preview-Version", str(session.preview_version))
                self.end_headers()
                self.wfile.write(body)
            except Exception as exc:
                print(f"terrain preview {area_id} error: {exc}")
                self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path.startswith("/api/map-image/"):
            area_id = path.removeprefix("/api/map-image/").strip("/")
            if not area_id or ".." in area_id:
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            try:
                img_path = DOCS_MAPS / f"{area_id}_map.png"
                if img_path.is_file():
                    body = img_path.read_bytes()
                else:
                    index = _read_json(CHART_INDEX_PATH)
                    bounds = None
                    for area in index.get("chart_areas", []):
                        if isinstance(area, dict) and area.get("id") == area_id:
                            bounds = area.get("bounds")
                            break
                    if not bounds:
                        self.send_error(HTTPStatus.NOT_FOUND)
                        return
                    body = _render_area_map_png(bounds)
                ctype = "image/png"
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                self.end_headers()
                self.wfile.write(body)
            except Exception as exc:
                print(f"map-image {area_id} error: {exc}")
                self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path in ("", "/"):
            self.path = "/index.html"
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "invalid JSON body"})
            return

        if parsed.path == "/api/snap":
            area_id = str(body.get("area_id", ""))
            if not area_id or ".." in area_id:
                _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "invalid area_id"})
                return
            try:
                gx = float(body.get("gx", 0))
                gy = float(body.get("gy", 0))
                inland = bool(body.get("inland"))
                idx = _snap_index_for_area_editing(area_id)
                cx, cy, tile = idx.nearest(gx, gy, inland)
                _json_response(
                    self,
                    HTTPStatus.OK,
                    {"gx": cx, "gy": cy, "tile": tile, "global_x": round(cx), "global_y": round(cy)},
                )
            except OSError as exc:
                _json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        if parsed.path == "/api/terrain/session":
            area_id = str(body.get("area_id", ""))
            if not area_id or ".." in area_id:
                _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "invalid area_id"})
                return
            try:
                from terrain_edit_session import ensure_session, get_session, load_chart_index

                session = get_session(area_id) or ensure_session(area_id)
                index = load_chart_index()
                boundary = session.boundary_status(index)
                _json_response(
                    self,
                    HTTPStatus.OK,
                    {
                        "area_id": area_id,
                        "dirty": session.dirty,
                        "paint_count": session.paint_count,
                        "preview_version": session.preview_version,
                        "preview_url": f"/api/terrain/preview/{area_id}",
                        **boundary,
                    },
                )
            except Exception as exc:
                _json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        if parsed.path == "/api/terrain/paint":
            area_id = str(body.get("area_id", ""))
            terrain = str(body.get("terrain", "")).lower()
            if not area_id or ".." in area_id:
                _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "invalid area_id"})
                return
            if terrain not in ("land", "sea"):
                _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "terrain must be land or sea"})
                return
            try:
                from terrain_edit_session import paint_cell_global

                gx = int(round(float(body.get("gx", 0))))
                gy = int(round(float(body.get("gy", 0))))
                result = paint_cell_global(area_id, gx, gy, land=terrain == "land")
                _json_response(self, HTTPStatus.OK, result)
            except ValueError as exc:
                _json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                _json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        if parsed.path == "/api/terrain/discard":
            area_id = str(body.get("area_id", ""))
            if area_id and ".." not in area_id:
                from terrain_edit_session import discard_session

                discard_session(area_id)
            _json_response(self, HTTPStatus.OK, {"ok": True})
            return

        if parsed.path == "/api/terrain/save":
            dry_run = bool(body.get("dry_run", False))
            label = "dry-run" if dry_run else "SAVE"
            print(f"[terrain] {label} requested")
            try:
                from terrain_edit_session import save_all

                report = save_all(
                    dry_run=dry_run,
                    snap_index_factory=_snap_index_for_area_editing,
                    clear_snap_cache=clear_snap_cache,
                )
                print(f"[terrain] {label} ok: {report.get('message', '')[:120]}")
                _json_response(self, HTTPStatus.OK, report)
            except Exception as exc:
                import traceback

                print(f"[terrain] {label} FAILED: {exc}")
                traceback.print_exc()
                _json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        if parsed.path != "/api/export":
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        edits = body.get("edits")
        if not isinstance(edits, list):
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "edits must be an array"})
            return

        payload = {
            "schema_version": 1,
            "description": (
                "Port map_u/map_v from wang16 1px port_map_editor. "
                "Merge into data/world_full.json ports[] by id."
            ),
            "global_grid_width": 2000,
            "global_grid_height": 1000,
            "tilemap_set": "chart_area_tilemaps_and_maps_wang16_1px",
            "final_tile_size": 1,
            "shore_snap_rule": "corner_wang_coast_tiles_excluding_totally_sea_and_totally_land",
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


def _resolve_host_port(args: argparse.Namespace) -> tuple[str, int]:
    host = args.host
    if host is None:
        host = os.environ.get("PORT_MAP_EDITOR_WANG16_HOST", DEFAULT_HOST)
    port = args.port
    if port is None:
        port = int(os.environ.get("PORT_MAP_EDITOR_WANG16_PORT", str(DEFAULT_PORT)))
    return host, port


class _ReuseAddrTCPServer(TCPServer):
    allow_reuse_address = True


def _dependency_help() -> str:
    venvs = (
        REPO_ROOT / "tools" / "tile-factory" / ".venv",
        REPO_ROOT / ".venv",
    )
    lines = [
        "Missing Pillow and/or numpy for the port map editor.",
        "",
        "Option A — use an existing project venv (from repo root):",
    ]
    for v in venvs:
        py = v / "bin" / "python3"
        if py.is_file():
            lines.append(f"  {py.relative_to(REPO_ROOT)} tools/port_map_editor_wang16_1px_server.py --port 8770")
    lines += [
        "",
        "Option B — create tile-factory venv and install deps:",
        "  python3 -m venv tools/tile-factory/.venv",
        "  tools/tile-factory/.venv/bin/pip install -r tools/tile-factory/requirements.txt",
        "  tools/tile-factory/.venv/bin/python3 tools/port_map_editor_wang16_1px_server.py --port 8770",
    ]
    return "\n".join(lines)


def main() -> None:
    try:
        import numpy  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        raise SystemExit(_dependency_help()) from exc

    ap = argparse.ArgumentParser(description="Wang-16 1px port map editor HTTP server")
    ap.add_argument(
        "--host",
        default=None,
        help=f"Bind host (default: PORT_MAP_EDITOR_WANG16_HOST or {DEFAULT_HOST})",
    )
    ap.add_argument(
        "--port",
        type=int,
        default=None,
        help=(
            f"Bind port (default: PORT_MAP_EDITOR_WANG16_PORT env var or {DEFAULT_PORT}). "
            "Example: PORT_MAP_EDITOR_WANG16_PORT=8770"
        ),
    )
    args = ap.parse_args()
    host, port = _resolve_host_port(args)

    if not STATIC_DIR.is_dir():
        raise SystemExit(f"Missing static dir: {STATIC_DIR}")
    if not CHART_INDEX_PATH.is_file():
        raise SystemExit(f"Missing wang16 chart index: {CHART_INDEX_PATH}")
    os.chdir(STATIC_DIR)
    clear_snap_cache()
    try:
        httpd = _ReuseAddrTCPServer((host, port), PortMapEditorWang16Handler)
    except OSError as exc:
        if exc.errno == 48:  # Address already in use (macOS / BSD)
            raise SystemExit(
                f"Port {port} is already in use on {host}.\n"
                f"Pick another port, e.g.:\n"
                f"  PORT_MAP_EDITOR_WANG16_PORT=8770 python3 tools/port_map_editor_wang16_1px_server.py\n"
                f"  python3 tools/port_map_editor_wang16_1px_server.py --port 8770"
            ) from exc
        raise
    with httpd:
        url = f"http://{host}:{port}/"
        print(f"Port map editor (wang16 1px) at {url}")
        print("Terrain API: POST /api/terrain/save  GET /api/terrain/status  (build map-wrap-input-14, ?debug=1)")
        print("Tile textures: GET /api/tile-texture/meta  /tile-texture-gallery.html")
        print(f"Tilemaps: {DOCS_MAPS}")
        print(f"Export file: {EXPORT_PATH}")
        print("Ctrl+C to stop.")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
