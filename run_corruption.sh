#!/usr/bin/env bash
# Locality/magnitude sweep for the confidence-corruption boundary.
#
# Corrupts only the PUBLIC confidence scores of a deterministic subset of nodes
# (sigmoid(logit(c) + shift)), then compares the global-mean signal gate against
# trusting the scores, the type prior, and the feedback loop.
#
# Usage:
#   ./run_corruption.sh [start_seed] [graphs] [workers]
#
# Defaults: 3000 200 4  (graph seeds 3000..3199, untouched by earlier runs)
#
# Outputs, all under role2_규리/results/corruption-v1:
#   episodes.csv    one row per graph/cell/policy (re-derives every interval)
#   manifest.json   seeds, grid, signal-gate centres, source SHA-256
#   corruption.md   Korean report
#   corruption.json machine-readable summary
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROLE2="$ROOT/role2_규리"
START="${1:-3000}"
GRAPHS="${2:-200}"
WORKERS="${3:-4}"
OUT="$ROLE2/results/corruption-v1"

if [ -e "$OUT" ]; then
  echo "output already exists: $OUT" >&2
  echo "remove it first: rm -rf \"$OUT\"" >&2
  exit 1
fi

cd "$ROLE2"

echo "=== sweep: $GRAPHS graphs from seed $START, $WORKERS workers ==="
python3 evaluate_corruption.py --out "$OUT" --start "$START" --graphs "$GRAPHS" --workers "$WORKERS"

echo "=== report ==="
python3 report_corruption.py "$OUT"

echo
echo "done: $OUT/corruption.md"
