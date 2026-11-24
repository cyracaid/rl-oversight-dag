#!/usr/bin/env bash
# Per-node mixture shrinkage (see role2_규리/PREREGISTER_SHRINK.md).
#
# Same corruption grid as corruption-v1/verify-v1, fresh graphs, one extra policy:
#   shrink = marginal on a per-node posterior that hedges between "the score came
#            from the clean distribution" and "the score was shifted by an unknown
#            delta". One scalar pi is fitted on 70000-70029; the policy itself is
#            unchanged (marginal, budget 16).
#
# Usage:
#   ./run_shrink.sh [start_seed] [graphs] [workers]
#
# Defaults: 3400 200 4
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROLE2="$ROOT/role2_규리"
START="${1:-3400}"
GRAPHS="${2:-200}"
WORKERS="${3:-4}"
OUT="$ROLE2/results/shrink-v1"

if [ -e "$OUT" ]; then
  echo "output already exists: $OUT" >&2
  echo "remove it first: rm -rf \"$OUT\"" >&2
  exit 1
fi

cd "$ROLE2"

echo "=== sweep: $GRAPHS graphs from seed $START, $WORKERS workers ==="
python3 evaluate_shrink.py --out "$OUT" --start "$START" --graphs "$GRAPHS" --workers "$WORKERS"

echo "=== report ==="
python3 report_shrink.py "$OUT"

echo
echo "done: $OUT/shrink.md"
