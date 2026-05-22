"""Phase A guard (chunk-based map plan): confirm before tile coastline generation.

See canvases/harbours-chunk-based-gaming-map.canvas.tsx — Phase A is only this prompt,
not a full freeze of tooling.
"""
from __future__ import annotations

PHASE_A_MESSAGE = (
    "Chunk-map Phase A: prefer continuous chunked art over new Wang/tile coastline generation.\n"
    "Are you sure you want to run this anyway?"
)


def confirm_tile_generation(*, message: str | None = None, assume_yes: bool = False) -> bool:
    if assume_yes:
        return True
    try:
        answer = input(f"{message or PHASE_A_MESSAGE} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")
