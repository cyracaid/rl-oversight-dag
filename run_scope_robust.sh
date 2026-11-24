#!/usr/bin/env bash
# Boundary of the scope model (see role2_규리/PREREGISTER_SCOPE_ROBUST.md).
#
# No new model and no refitting: p0 = 0.20 and pi = 0.15 are the values already
# fitted in scope-v1 and shrink-v1. The same frozen scope policy is run on two
# conditions that break its assumptions:
#   off_grid    one locality, one delta, but the delta sits between grid points
#   two_delta   source and sink moved by different amounts at the same time
#
# Usage:
#   ./run_scope_robust.sh [start_seed] [graphs] [workers]
#
# Defaults: 3800 100 4
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROLE2="$ROOT/role2_규리"
START="${1:-3800}"
GRAPHS="${2:-100}"
WORKERS="${3:-4}"
OUT="$ROLE2/results/scope-robust-v1"

if [ -e "$OUT" ]; then
  echo "output already exists: $OUT" >&2
  echo "remove it first: rm -rf \"$OUT\"" >&2
  exit 1
fi

cd "$ROLE2"

echo "=== sweep: $GRAPHS graphs from seed $START, $WORKERS workers ==="
python3 evaluate_scope_robust.py --out "$OUT" --start "$START" --graphs "$GRAPHS" --workers "$WORKERS"

echo "=== report ==="
python3 report_scope_robust.py "$OUT"

echo
echo "done: $OUT/scope_robust.md"
