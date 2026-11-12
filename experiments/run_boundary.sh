#!/usr/bin/env bash
# Run from anywhere. Executes full data runs only when invoked by the user.
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
RUN_ROOT="${RUN_ROOT:-runs/boundary-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$RUN_ROOT"
printf 'Outputs: %s\n' "$RUN_ROOT"

# These independent training jobs run serially to bound memory use.
"$PYTHON" -u experiments/rl_distill.py --graphs 800 --bc-epochs 4 \
  --episodes 20000 --seeds 1 2 3 4 5 --heldout 200 --kl-beta 0 \
  --out-dir "$RUN_ROOT/bc" 2>&1 | tee "$RUN_ROOT/bc.log"
for variant in static observed; do
  "$PYTHON" -u experiments/rl_boundary.py train --variant "$variant" \
    --seeds 1 2 3 4 5 --episodes 20000 --out-dir "$RUN_ROOT/$variant" \
    2>&1 | tee "$RUN_ROOT/$variant.log"
done

# Four policies: threshold, belief greedy, static RL, observed RL; also BC/FT.
"$PYTHON" -u experiments/rl_boundary.py eval \
  --checkpoints "$RUN_ROOT/static/"*.pt "$RUN_ROOT/observed/"*.pt "$RUN_ROOT/bc/"*.pt \
  --heldout 200 --bootstrap 10000 --out-dir "$RUN_ROOT/misspec" \
  2>&1 | tee "$RUN_ROOT/misspec.log"

# Expensive planning control, initially matched-model development condition only.
"$PYTHON" -u experiments/rl_boundary.py eval --scenarios matched --two-step \
  --checkpoints "$RUN_ROOT/static/"*.pt "$RUN_ROOT/observed/"*.pt "$RUN_ROOT/bc/"*.pt \
  --heldout 200 --bootstrap 10000 --out-dir "$RUN_ROOT/planning" \
  2>&1 | tee "$RUN_ROOT/planning.log"
