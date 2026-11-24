#!/usr/bin/env bash
# Two-level scope model (see role2_규리/PREREGISTER_SCOPE_V2.md).
#
# Same corruption grid as shrink-v1, fresh graphs, one extra policy:
#   scope = marginal on a posterior that competes "nothing moved" against
#           "a fraction q of the nodes moved by one shared delta". The fraction and
#           the delta are graph-level, because that is what the corruption generator
#           does. One scalar p0 is fitted on 70000-70029; the policy itself is
#           unchanged (marginal, budget 16).
#
# Usage:
#   ./run_scope.sh [start_seed] [graphs] [workers]
#
# Defaults: 3600 200 4
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROLE2="$ROOT/role2_규리"
START="${1:-3600}"
GRAPHS="${2:-200}"
WORKERS="${3:-4}"
OUT="$ROLE2/results/scope-v1"

if [ -e "$OUT" ]; then
  echo "output already exists: $OUT" >&2
  echo "remove it first: rm -rf \"$OUT\"" >&2
  exit 1
fi

cd "$ROLE2"

echo "=== sweep: $GRAPHS graphs from seed $START, $WORKERS workers ==="
python3 evaluate_scope.py --out "$OUT" --start "$START" --graphs "$GRAPHS" --workers "$WORKERS"

echo "=== report ==="
python3 report_scope.py "$OUT"

echo
echo "done: $OUT/scope.md"
