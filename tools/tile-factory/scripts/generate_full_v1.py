"""Generate all v1 terrain — runs build-v1-mosaic (contract compositing pipeline)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from build_v1_mosaic import main


if __name__ == "__main__":
    sys.exit(main())
