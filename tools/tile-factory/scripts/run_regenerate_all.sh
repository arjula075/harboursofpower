#!/usr/bin/env bash
# Regenerate all v1 tiles into a NEW generation folder (g002, g003, …) per biome.
# Pass --overwrite to replace files in the current/legacy layout instead.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PY="${ROOT}/.venv/bin/python3"
SCRIPTS="${ROOT}/tools/tile-factory/scripts"
mkdir -p "${ROOT}/tools/tile-factory/reports"

if [[ -z "${OPENAI_API_KEY:-}" ]] && [[ ! -f "${ROOT}/.env" ]]; then
  echo "Set OPENAI_API_KEY or add it to ${ROOT}/.env" >&2
  exit 1
fi

cd "${SCRIPTS}"
DEFAULT_ARGS=(--new-generation)
echo "=== dry_scrubland ==="
"${PY}" regenerate_all_v1.py --biomes dry_scrubland --season summer "${DEFAULT_ARGS[@]}" "$@"
echo "=== sparse_olive ==="
"${PY}" regenerate_all_v1.py --biomes sparse_olive --season summer "${DEFAULT_ARGS[@]}" "$@"
echo "=== lake review ==="
"${PY}" build_lake_review.py
echo "Done. Open tools/tile-factory/review/index.html"
