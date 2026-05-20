# Terrain biomes (tile factory)

Canonical list for overworld tile generation. Each biome needs `style/biomes/{id}.md` before running `bootstrap-biome`.

| ID | Display name | Style bible | Status |
|----|----------------|-------------|--------|
| `dry_scrubland` | Dry rocky scrubland | [dry_scrubland.md](style/biomes/dry_scrubland.md) | v1 done |
| `sparse_olive` | Sparse olive-like trees | [sparse_olive.md](style/biomes/sparse_olive.md) | **v1 in progress** |
| `pine_clusters` | Pine clusters | `style/biomes/pine_clusters.md` | planned |
| `grassy_patches` | Grassy patches | `style/biomes/grassy_patches.md` | planned |
| `terraced_hillsides` | Terraced hillsides | `style/biomes/terraced_hillsides.md` | planned |

## Notes

- **ID** = folder name under `assets/tiles/{pending,approved}/` and key in `config.json` → `biomes`.
- **Seasons:** start with `summer` per biome; add `winter` / `spring` / `autumn` later as separate config runs.
- **Ports** are culture overlays, not biomes (Greek, Roman, etc.).

## Bootstrap a biome

```powershell
copy tools\tile-factory\style\biomes\_template.md tools\tile-factory\style\biomes\sparse_olive.md
# edit sparse_olive.md, then:
python tools/tile-factory/scripts/orchestrator.py bootstrap-biome --biome sparse_olive --season summer
python tools/tile-factory/scripts/orchestrator.py build-v1-mosaic --proof
```
