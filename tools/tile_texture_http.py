"""Shared HTTP handlers for tile-texture map preview (used by review + port editor servers)."""
from __future__ import annotations

import sys
from functools import lru_cache
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

REPO_ROOT = Path(__file__).resolve().parents[1]
TILE_SCRIPTS = REPO_ROOT / "tools" / "tile-factory" / "scripts"
if str(TILE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(TILE_SCRIPTS))

GALLERY_HTML = REPO_ROOT / "tools" / "tile-factory" / "review" / "tile-texture-gallery.html"


def _import_render():
    from tile_texture_render import render_chart_area_png, texture_preview_meta

    return render_chart_area_png, texture_preview_meta


def _qs_int(qs: dict[str, list[str]], key: str, default: int) -> int:
    raw = (qs.get(key) or [""])[0]
    if not raw:
        return default
    return int(raw)


def _qs_optional_int(qs: dict[str, list[str]], key: str) -> int | None:
    raw = (qs.get(key) or [""])[0]
    if not raw:
        return None
    return int(raw)


@lru_cache(maxsize=32)
def _render_preview_cached(
    area_id: str,
    biome: str,
    season: str,
    variation: int,
    pool: str,
    scale: int,
    generation: int | None,
) -> bytes:
    render_chart_area_png, _ = _import_render()
    return render_chart_area_png(
        area_id,
        biome=biome,
        season=season,
        variation=variation,
        generation=generation,
        pool=pool,
        scale=scale,
    )


def handle_tile_texture_get(
    handler: SimpleHTTPRequestHandler,
    path: str,
    qs: dict[str, list[str]],
    *,
    json_response,
) -> bool:
    """Return True if the request was handled."""
    if path == "/api/tile-texture/meta":
        try:
            _, texture_preview_meta = _import_render()
            json_response(handler, HTTPStatus.OK, texture_preview_meta())
        except ImportError as exc:
            json_response(
                handler,
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"error": str(exc), "pillow_required": True},
            )
        except Exception as exc:
            json_response(handler, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
        return True

    if path.startswith("/api/tile-texture/preview/"):
        area_id = path.removeprefix("/api/tile-texture/preview/").strip("/")
        if not area_id or ".." in area_id:
            handler.send_error(HTTPStatus.BAD_REQUEST)
            return True
        try:
            _, texture_preview_meta = _import_render()
            meta = texture_preview_meta()
            defaults = meta.get("defaults") or {}
            biome = (qs.get("biome") or [defaults.get("biome", "sparse_olive")])[0]
            season = (qs.get("season") or [defaults.get("season", "summer")])[0]
            pool = (qs.get("pool") or [defaults.get("pool", "approved")])[0]
            if pool not in ("approved", "pending"):
                json_response(handler, HTTPStatus.BAD_REQUEST, {"error": "invalid pool"})
                return True
            variation = _qs_int(qs, "variation", int(defaults.get("variation", 1)))
            scale = _qs_int(qs, "scale", int(defaults.get("scale", 10)))
            generation = _qs_optional_int(qs, "generation")
            if generation is None and defaults.get("generation") is not None:
                generation = int(defaults["generation"])
            body = _render_preview_cached(
                area_id,
                str(biome),
                str(season),
                variation,
                str(pool),
                scale,
                generation,
            )
            handler.send_response(HTTPStatus.OK)
            handler.send_header("Content-Type", "image/png")
            handler.send_header("Content-Length", str(len(body)))
            handler.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            handler.end_headers()
            handler.wfile.write(body)
        except ImportError as exc:
            json_response(
                handler,
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"error": str(exc), "pillow_required": True},
            )
        except ValueError as exc:
            json_response(handler, HTTPStatus.NOT_FOUND, {"error": str(exc)})
        except FileNotFoundError as exc:
            json_response(handler, HTTPStatus.NOT_FOUND, {"error": str(exc)})
        except Exception as exc:
            json_response(handler, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
        return True

    if path in ("/tile-texture-gallery.html", "/tile-texture-gallery"):
        if GALLERY_HTML.is_file():
            data = GALLERY_HTML.read_bytes()
            handler.send_response(HTTPStatus.OK)
            handler.send_header("Content-Type", "text/html; charset=utf-8")
            handler.send_header("Content-Length", str(len(data)))
            handler.send_header("Cache-Control", "no-store")
            handler.end_headers()
            handler.wfile.write(data)
            return True
        handler.send_error(HTTPStatus.NOT_FOUND)
        return True

    return False
