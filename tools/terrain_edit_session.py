"""In-memory terrain edit sessions for the wang16 port map editor."""
from __future__ import annotations

import json
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[1]

from corner_wang16 import (  # noqa: E402
    LOG_H,
    LOG_W,
    boundary_corner_changes,
    corners_from_tiles,
    land_mask_from_corners,
    overlapping_chart_areas,
    paint_cell,
    render_area_preview_png,
    tiles_from_corners,
    wang_tile_name,
)

DOCS = REPO / "docs"
CHART_DIR = DOCS / "chart_area_tilemaps_and_maps_wang16_1px"
CHART_INDEX_PATH = CHART_DIR / "chart_area_index.json"
FULL_TILEMAP_PATH = DOCS / "mediterranean_recursive_tilemap_wang16_1px.json"
GLOBAL_MASK_PATH = DOCS / "mediterranean_recursive_tilemap_wang16_1px_mask.png"
PREVIEW_PATH = DOCS / "mediterranean_recursive_tilemap_wang16_1px_wang_preview.png"
CHUNKS_DIR = DOCS / "maps" / "chunks"
CHUNK_MANIFEST_PATH = REPO / "data" / "maps" / "chunk_manifest.json"
WORLD_PATH = REPO / "data" / "world_full.json"
EXPORT_PATH = REPO / "data" / "port_map_editor_wang16_1px_export.json"


@dataclass
class TerrainSession:
    area_id: str
    bounds: dict
    corners: np.ndarray
    baseline_corners: np.ndarray
    tiles: list[dict]
    tile_counts: Counter
    dirty: bool = False
    paint_count: int = 0
    preview_version: int = 0

    def recompute_tiles(self) -> None:
        x0, y0 = int(self.bounds["x0"]), int(self.bounds["y0"])
        self.tiles, self.tile_counts = tiles_from_corners(self.corners, x0=x0, y0=y0)

    def boundary_status(self, index: dict) -> dict[str, Any]:
        n = boundary_corner_changes(self.baseline_corners, self.corners)
        overlap = overlapping_chart_areas(self.area_id, index, self.bounds) if n > 0 else []
        return {
            "boundary_corners_changed": n,
            "overlapping_chart_areas": overlap,
            "cross_area_ripple": n > 0,
        }


_sessions: dict[str, TerrainSession] = {}


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_chart_index() -> dict:
    return _read_json(CHART_INDEX_PATH)


def get_session(area_id: str) -> TerrainSession | None:
    return _sessions.get(area_id)


def list_dirty_area_ids() -> list[str]:
    return [aid for aid, s in _sessions.items() if s.dirty]


def discard_session(area_id: str) -> None:
    _sessions.pop(area_id, None)


def ensure_session(area_id: str) -> TerrainSession:
    existing = _sessions.get(area_id)
    if existing is not None:
        return existing
    index = load_chart_index()
    bounds = None
    for a in index.get("chart_areas", []):
        if isinstance(a, dict) and a.get("id") == area_id:
            bounds = a.get("bounds")
            break
    if not bounds:
        raise KeyError(f"unknown chart area: {area_id}")
    tilemap_path = CHART_DIR / f"{area_id}_tilemap.json"
    data = _read_json(tilemap_path)
    tiles = data.get("tiles", [])
    if not isinstance(tiles, list):
        tiles = []
    x0, y0, x1, y1 = int(bounds["x0"]), int(bounds["y0"]), int(bounds["x1"]), int(bounds["y1"])
    corners = corners_from_tiles(tiles, x0=x0, y0=y0, x1=x1, y1=y1)
    session = TerrainSession(
        area_id=area_id,
        bounds=bounds,
        corners=corners,
        baseline_corners=corners.copy(),
        tiles=[],
        tile_counts=Counter(),
    )
    session.recompute_tiles()
    _sessions[area_id] = session
    return session


def paint_cell_global(area_id: str, gx: int, gy: int, *, land: bool) -> dict[str, Any]:
    session = ensure_session(area_id)
    x0, y0, x1, y1 = (
        int(session.bounds["x0"]),
        int(session.bounds["y0"]),
        int(session.bounds["x1"]),
        int(session.bounds["y1"]),
    )
    if gx < x0 or gx >= x1 or gy < y0 or gy >= y1:
        raise ValueError(f"({gx}, {gy}) outside chart area bounds")
    lx, ly = gx - x0, gy - y0
    before_name = next(
        (t["tile"] for t in session.tiles if int(t["x"]) == gx and int(t["y"]) == gy),
        None,
    )
    paint_cell(session.corners, lx, ly, land=land)
    session.recompute_tiles()
    session.dirty = True
    session.paint_count += 1
    session.preview_version += 1
    after_name = next(
        (t["tile"] for t in session.tiles if int(t["x"]) == gx and int(t["y"]) == gy),
        wang_tile_name(land, land, land, land),
    )
    index = load_chart_index()
    boundary = session.boundary_status(index)
    return {
        "gx": gx,
        "gy": gy,
        "terrain": "land" if land else "sea",
        "tile_before": before_name,
        "tile_after": after_name,
        "paint_count": session.paint_count,
        "preview_version": session.preview_version,
        **boundary,
    }


def preview_png(area_id: str) -> bytes:
    session = ensure_session(area_id)
    x0, y0, x1, y1 = (
        int(session.bounds["x0"]),
        int(session.bounds["y0"]),
        int(session.bounds["x1"]),
        int(session.bounds["y1"]),
    )
    return render_area_preview_png(session.tiles, x0=x0, y0=y0, x1=x1, y1=y1)


def _load_global_corners_from_tilemap() -> np.ndarray:
    if not FULL_TILEMAP_PATH.is_file():
        raise FileNotFoundError(FULL_TILEMAP_PATH)
    data = _read_json(FULL_TILEMAP_PATH)
    tiles = data.get("tiles", [])
    return corners_from_tiles(tiles, x0=0, y0=0, x1=LOG_W, y1=LOG_H)


def _merge_dirty_sessions_into_global(global_corners: np.ndarray) -> list[str]:
    applied: list[str] = []
    for area_id, session in _sessions.items():
        if not session.dirty:
            continue
        x0, y0, x1, y1 = (
            int(session.bounds["x0"]),
            int(session.bounds["y0"]),
            int(session.bounds["x1"]),
            int(session.bounds["y1"]),
        )
        global_corners[y0 : y1 + 1, x0 : x1 + 1] = session.corners
        applied.append(area_id)
    return applied


def _global_tiles_and_land(global_corners: np.ndarray) -> tuple[list[dict], Counter, np.ndarray]:
    tiles, counts = tiles_from_corners(global_corners, x0=0, y0=0)
    land = land_mask_from_corners(global_corners)
    return tiles, counts, land


def _resnap_ports_for_areas(area_ids: set[str], snap_index_factory) -> list[dict]:
    world = _read_json(WORLD_PATH)
    ports = world.get("ports", [])
    edits: list[dict] = []
    for p in ports:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id", ""))
        chart_area = str(p.get("chart_area_id", ""))
        if chart_area not in area_ids:
            continue
        mu, mv = p.get("map_u"), p.get("map_v")
        if mu is None or mv is None:
            continue
        gx = float(mu) * LOG_W
        gy = float(mv) * LOG_H
        inland = bool(p.get("inland_exception", False))
        idx = snap_index_factory(chart_area)
        cx, cy, tile = idx.nearest(gx, gy, inland)
        edits.append(
            {
                "id": pid,
                "name": str(p.get("name", pid)),
                "chart_area_id": chart_area,
                "map_u": cx / LOG_W,
                "map_v": cy / LOG_H,
                "global_x": round(cx),
                "global_y": round(cy),
                "snapped_tile": tile,
            }
        )
    return edits


def disk_terrain_save_status() -> dict[str, Any]:
    """Whether a terrain editor save has been committed to disk (for UI / diagnostics)."""
    out: dict[str, Any] = {
        "on_disk": False,
        "export_exists": EXPORT_PATH.is_file(),
        "full_tilemap_exists": FULL_TILEMAP_PATH.is_file(),
        "mask_exists": GLOBAL_MASK_PATH.is_file(),
    }
    if out["export_exists"]:
        try:
            export = _read_json(EXPORT_PATH)
            out["export_generated_at"] = export.get("generated_at")
            out["export_port_count"] = len(export.get("edits", []))
            out["export_terrain_save"] = bool(export.get("terrain_save"))
        except (OSError, json.JSONDecodeError):
            out["export_read_error"] = True

    if FULL_TILEMAP_PATH.is_file():
        out["full_tilemap_mtime"] = datetime.fromtimestamp(
            FULL_TILEMAP_PATH.stat().st_mtime, tz=timezone.utc
        ).isoformat()
        try:
            tail = FULL_TILEMAP_PATH.read_text(encoding="utf-8")[-4096:]
            if '"terrain_editor_save"' in tail:
                idx = tail.rfind('"terrain_editor_save"')
                snippet = tail[idx : idx + 400]
                # crude extract saved_at
                if '"saved_at"' in snippet:
                    start = snippet.index('"saved_at"') + len('"saved_at"')
                    rest = snippet[start:].lstrip(": \t")
                    if rest.startswith('"'):
                        end = rest.index('"', 1)
                        out["last_saved_at"] = rest[1:end]
                out["on_disk"] = True
            head = FULL_TILEMAP_PATH.read_text(encoding="utf-8")[:12000]
            if '"source_mode"' in head and "editor_terrain" in head:
                out["source_mode_editor_terrain"] = True
            elif '"source_mode"' in head and "3px_upscale" in head:
                out["source_mode"] = "3px_upscale"
        except OSError:
            out["full_tilemap_read_error"] = True

    out["on_disk"] = bool(
        out.get("on_disk")
        or (out.get("export_terrain_save") and out.get("export_exists"))
    )
    return out


def save_all(*, dry_run: bool, snap_index_factory, clear_snap_cache) -> dict[str, Any]:
    dirty_areas = [aid for aid, s in _sessions.items() if s.dirty]
    if not dirty_areas:
        return {
            "ok": True,
            "saved": False,
            "written_to_disk": False,
            "dry_run": dry_run,
            "no_edits": True,
            "message": "Nothing to save — paint at least one cell first (no unsaved terrain edits).",
            "disk_status": disk_terrain_save_status(),
        }

    global_corners = _load_global_corners_from_tilemap()
    applied = _merge_dirty_sessions_into_global(global_corners)
    tiles, counts, land = _global_tiles_and_land(global_corners)

    index = load_chart_index()
    overlap_warnings: list[dict] = []
    for aid in applied:
        session = _sessions[aid]
        st = session.boundary_status(index)
        if st["cross_area_ripple"]:
            overlap_warnings.append({"area_id": aid, **st})

    resnap_areas = set(applied)
    for w in overlap_warnings:
        resnap_areas.update(w.get("overlapping_chart_areas", []))

    port_edits = _resnap_ports_for_areas(resnap_areas, snap_index_factory)

    report: dict[str, Any] = {
        "ok": True,
        "saved": not dry_run,
        "written_to_disk": False,
        "dry_run": dry_run,
        "no_edits": False,
        "dirty_chart_areas": dirty_areas,
        "applied_chart_areas": applied,
        "cells_total": len(tiles),
        "tile_counts_sample": dict(counts.most_common(12)),
        "overlap_warnings": overlap_warnings,
        "ports_resnapped": len(port_edits),
        "port_edits_sample": port_edits[:8],
        "files_to_write": [
            str(FULL_TILEMAP_PATH.relative_to(REPO)),
            str(GLOBAL_MASK_PATH.relative_to(REPO)),
            str(PREVIEW_PATH.relative_to(REPO)),
            f"{CHART_DIR.name}/*_tilemap.json",
            f"{CHART_DIR.name}/*_map.png",
        ],
    }

    if dry_run:
        report["message"] = (
            f"Dry-run only — nothing written to disk. Would merge {len(applied)} chart area(s), "
            f"rewrite full map + mask + {len(index.get('chart_areas', []))} chart exports, "
            f"resnap {len(port_edits)} port(s)."
        )
        report["disk_status"] = disk_terrain_save_status()
        return report

    # Import build helpers lazily (scipy/PIL heavy).
    import sys

    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from build_recursive_tilemap_wang16_1px import (  # noqa: E402
        build_payload,
        collect_tile_types,
        write_area_map_png,
        write_chart_area_exports,
        write_mask_png,
        write_wang_preview,
    )

    src_label = "port_map_editor_terrain"
    source_mode = "editor_terrain"
    tile_types = collect_tile_types(counts)
    payload = build_payload(tiles, tile_types, counts, source_image=src_label, source_mode=source_mode)
    payload["terrain_editor_save"] = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "chart_areas": applied,
    }

    backup = FULL_TILEMAP_PATH.with_suffix(".json.bak")
    if FULL_TILEMAP_PATH.is_file():
        shutil.copy2(FULL_TILEMAP_PATH, backup)
        report["backup"] = str(backup.relative_to(REPO))

    with FULL_TILEMAP_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))

    write_mask_png(GLOBAL_MASK_PATH, land)
    write_wang_preview(PREVIEW_PATH, tiles)
    write_chart_area_exports(
        CHART_DIR,
        index,
        tiles,
        land,
        src_label=src_label,
        source_mode=source_mode,
    )

    from build_tile_pixel_chunks import build_tile_pixel_chunks

    chunk_manifest = build_tile_pixel_chunks(
        chunks_dir=CHUNKS_DIR,
        manifest_path=CHUNK_MANIFEST_PATH,
    )

    clear_snap_cache()
    for aid in applied:
        _sessions.pop(aid, None)

    export_doc = {
        "schema_version": 1,
        "description": "Port map_u/map_v after terrain save auto-resnap.",
        "global_grid_width": LOG_W,
        "global_grid_height": LOG_H,
        "tilemap_set": "chart_area_tilemaps_and_maps_wang16_1px",
        "shore_snap_rule": "corner_wang_coast_tiles_excluding_totally_sea_and_totally_land",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "terrain_save": True,
        "edits": port_edits,
    }
    EXPORT_PATH.write_text(json.dumps(export_doc, indent=2) + "\n", encoding="utf-8")
    report["export_path"] = str(EXPORT_PATH.relative_to(REPO))
    report["saved_at"] = payload["terrain_editor_save"]["saved_at"]
    report["written_to_disk"] = True
    report["verification"] = {
        "full_tilemap_bytes": FULL_TILEMAP_PATH.stat().st_size,
        "export_bytes": EXPORT_PATH.stat().st_size,
        "mask_bytes": GLOBAL_MASK_PATH.stat().st_size if GLOBAL_MASK_PATH.is_file() else 0,
        "backup": report.get("backup"),
        "chunks": len(chunk_manifest.get("chunks", [])),
    }
    report["base_data"] = {
        "mask_png": str(GLOBAL_MASK_PATH.relative_to(REPO)),
        "wang_preview_png": str(PREVIEW_PATH.relative_to(REPO)),
        "full_tilemap_json": str(FULL_TILEMAP_PATH.relative_to(REPO)),
        "chart_area_tilemaps": str(CHART_DIR.relative_to(REPO)),
        "chunk_manifest": str(CHUNK_MANIFEST_PATH.relative_to(REPO)),
        "chunk_webps": str(CHUNKS_DIR.relative_to(REPO)),
        "godot_chunk_map": "WorldMapChart reads chunk manifest + mask-derived WEBP chunks",
        "routes_basemap": "HarboursChartGrid.CHUNK_MASK_MASTER_PNG (same mask PNG)",
    }
    report["disk_status"] = disk_terrain_save_status()
    report["next_step"] = "python3 tools/apply_port_map_wang16_1px_export.py"
    report["message"] = (
        f"Saved to disk at {report['saved_at']}: {len(applied)} chart area(s), "
        f"{len(port_edits)} port(s) resnapped, game chunks refreshed. "
        f"Next: {report['next_step']}"
    )
    return report
