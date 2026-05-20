# Tile factory (Harbours of Power)

Generates **512×512 WebP** overworld tiles for Godot: v1 Wang shore set, procedural compositing, sail masks.

**Terrain biomes:** see [BIOMES.md](BIOMES.md) (`dry_scrubland`, `sparse_olive`, `pine_clusters`, `grassy_patches`, `terraced_hillsides`).

## Two commands (new biome)

```powershell
cd D:\Users\ari19\WebstormProjects\HarboursOfPower
.\.venv-tiles\Scripts\Activate.ps1
pip install -r tools\tile-factory\requirements.txt
```

**1. Bootstrap** (no API — specs + config check):

```powershell
python tools/tile-factory/scripts/orchestrator.py bootstrap-biome --biome your_biome --season summer
```

**2. Build** (API + compositing → lake mosaic review):

```powershell
# Cheap proof first (~9 API images)
python tools/tile-factory/scripts/orchestrator.py build-v1-mosaic --proof

# Full v1 set (v01–v03)
python tools/tile-factory/scripts/orchestrator.py build-v1-mosaic --variations 1 2 3
```

Open `tools/tile-factory/review/index.html` and `tools/tile-factory/reports/lake_mosaic_5x5.png`.

**Tweak compositor only** (no API):

```powershell
python tools/tile-factory/scripts/orchestrator.py refresh-mosaic
```

## Before you start

| Requirement | |
|-------------|--|
| Style bible | `tools/tile-factory/style/biomes/{biome}.md` (copy from `biomes/_template.md`) |
| API key | `OPENAI_API_KEY` in repo-root `.env` |
| Palette (optional) | `config.json` → `biomes.{biome}.open_sea_rgb` / `beach_rgb` (bootstrap adds defaults) |

Pre-flight runs automatically and prints API call count + cost estimate before any generation.

## Command reference

| Command | API? | Purpose |
|---------|------|---------|
| `bootstrap-biome` | No | Set biome/season, palette stub, enqueue specs |
| `build-v1-mosaic --proof` | Yes (~9) | v01 only: land + 8 shores + lake mosaic |
| `build-v1-mosaic` | Yes (~27 for v1×3) | Full pipeline |
| `build-v1-mosaic --skip-generate` | No | Re-composite + lake only |
| `refresh-mosaic` | No | Alias for `--skip-generate` |
| `build-v1-mosaic --validate` | — | Also run tile validator after build |
| `approve <id>` | No | pending → approved |

### Cost guide (rough, gpt-image-1)

| Run | API images | Est. USD |
|-----|------------|----------|
| `--proof` | 9 (1 land + 8 shores) | $0.20–0.55 |
| `--variations 1` | 10 | $0.20–0.60 |
| `--variations 1 2 3` | 28 | $0.55–1.70 |

Sea tiles are procedural (no API). `totally_sea` is not generated via OpenAI.

## What `build-v1-mosaic` does

1. **Pre-flight** — style bible, API key, specs, cost estimate  
2. **`totally_land/v01`** → land anchor in `pending/`  
3. **Raw PNGs** — shores (+ land v02/v03 unless `--proof`)  
4. **Procedural `totally_sea`**  
5. **`reenforce`** — `shore_composite.py` (flat sea, land anchor, beach, v01 coast detail)  
6. **`stitch_check_lake`** + **`build_lake_review`** (5×5 mosaic)

Prompts: single source in `scripts/prompts.py`.

## Approve tiles

```powershell
python tools/tile-factory/scripts/orchestrator.py approve dry_scrubland/summer/horizontal_top_land/v01
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Missing biome style` | Create `style/biomes/{biome}.md` from `_template.md` |
| `OPENAI_API_KEY not set` | Add key to repo-root `.env` |
| `Land anchor missing` | Run full build without `--skip-generate` |
| `Missing spec` | Run `bootstrap-biome` |
| Lake has `?` cells | Run `build-v1-mosaic --proof` or check pending paths |
| Odd tubular sea | Use `refresh-mosaic` after pulling latest compositor |
| Stitch check warnings | Check `scripts/stitch_check_lake.py` output (mask alignment) |

## Layout

| Path | Purpose |
|------|---------|
| `style/biomes/` | Per-biome art bible + `_template.md` |
| `config.json` | `biome`, `season`, `biomes.{id}` palettes |
| `specs/` | Per-tile job JSON |
| `raw/` | Model output (gitignored) |
| `assets/tiles/pending/` | Built tiles awaiting approval |
| `review/index.html` | Lake mosaic gallery |

## Legacy (deprecated for v1)

These print a deprecation warning and use the old edge-compositing path:

- `phase1`
- `compose` / `compose-all`
- `publish-raw` (raw only, no contract compositor)

Use **`build-v1-mosaic`** instead (`edge_compose_mode: none` in config).
