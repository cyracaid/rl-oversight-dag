#!/usr/bin/env bash
# Pre-registered probe-then-decide experiment (see role2_규리/PREREGISTER_VERIFY.md).
#
# Same corruption grid as corruption-v1, fresh graphs, one extra policy:
#   verify = probe 4 reviews only if the normal and rank-restored hypotheses
#            disagree by more than a calibrated threshold, commit once by the
#            probed flag likelihood ratio, and never fall back to the type prior.
#
# Usage:
#   ./run_verify.sh [start_seed] [graphs] [workers]
#
# Defaults: 3200 200 4
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROLE2="$ROOT/role2_규리"
START="${1:-3200}"
GRAPHS="${2:-200}"
WORKERS="${3:-4}"
OUT="$ROLE2/results/verify-v1"

if [ -e "$OUT" ]; then
  echo "output already exists: $OUT" >&2
  echo "remove it first: rm -rf \"$OUT\"" >&2
  exit 1
fi

cd "$ROLE2"

echo "=== sweep: $GRAPHS graphs from seed $START, $WORKERS workers ==="
python3 evaluate_verify.py --out "$OUT" --start "$START" --graphs "$GRAPHS" --workers "$WORKERS"

echo "=== report ==="
python3 report_verify.py "$OUT"

echo
echo "done: $OUT/verify.md"
