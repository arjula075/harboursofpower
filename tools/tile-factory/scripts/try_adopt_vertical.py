"""Try to adopt an existing raw PNG (e.g. old totally_sea v01) as vertical_right_land if it passes checks."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from common import load_config, repo_path, spec_path
from regenerate import content_errors, publish_raw_spec
from generate_sail_mask import write_mask_for_tile


def main() -> int:
    cfg = load_config()
    biome = cfg["biome"]
    season = cfg["season"]
    src_id = f"{biome}/{season}/totally_sea/v01"
    dst_id = f"{biome}/{season}/vertical_right_land/v01"
    src_spec_path = spec_path(src_id)
    dst_spec_path = spec_path(dst_id)
    if not src_spec_path.is_file() or not dst_spec_path.is_file():
        print("Missing spec files")
        return 1
    with src_spec_path.open(encoding="utf-8") as f:
        src_spec = json.load(f)
    with dst_spec_path.open(encoding="utf-8") as f:
        dst_spec = json.load(f)
    raw_src = Path(src_spec["raw_path"])
    if not raw_src.is_file():
        print(f"No raw at {raw_src}")
        return 1
    dst_raw = Path(dst_spec["raw_path"])
    dst_raw.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(raw_src, dst_raw)
    fake_spec = {**dst_spec, "raw_path": str(dst_raw)}
    errs = content_errors(fake_spec, dst_raw, cfg)
    if errs:
        print(f"Cannot adopt: {', '.join(errs)}")
        return 1
    publish_raw_spec(dst_spec, cfg)
    write_mask_for_tile(Path(dst_spec["pending_path"]), "vertical_right_land", cfg)
    print(f"Adopted {src_id} -> {dst_id} (sea west, land east; N/S aligned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
