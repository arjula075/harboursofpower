# Biome: {biome_id}

Copy from `_template.md` for a new entry in [BIOMES.md](../../BIOMES.md).

**Season v1:** summer

## Palette (also set in config.json `biomes.{biome_id}`)

- Sea: deep navy open water `[R, G, B]` — must match `open_sea_rgb` in config
- Beach: sun-bleached sand `[R, G, B]` — `beach_rgb` in config
- Land: describe dominant ground colour and vegetation

## Features

- Coast: rocky boulder beach preferred over flat pool edge
- Inland: describe shrubs, rock, soil texture
- Avoid: cartoon style, picture frames, vignettes, ships, text

## Shores

- Coastline silhouette must meander at medium scale (not texture-only roughness)
- Broad coastal transition band; shallow submerged rocks follow irregular shore shape
- Cardinal shores: coast enters/exits opposite edges near midpoints with organic wobble between
- Corner shores: compact irregular bay in corner region — never triangle/wedge/straight split
- Terrain self-contained in tile; no landmarks or structures on borders

## Variation

- v01–v03 share tile exit connectivity; local shore shape and inland detail may vary
