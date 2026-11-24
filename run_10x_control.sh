#!/usr/bin/env bash
# 10x compute control for the "RL loses to the marginal rule" negative result.
#
# Trains three Spike GNN seeds at 10x the canonical budget (10000 vs 1000
# episodes), then evaluates them on the SAME untouched confirmation set
# (graph seeds 2000..2199) with the SAME paired bootstrap as results/confirm-v1.
#
# Read results/confirm-10x/comparison.md and compare the "marginal 대비 차이"
# (vs marginal) column against results/confirm-v1/comparison.md.
#
# Verdict rule:
#   - still positive with a CI excluding 0 -> the negative result is not an
#     undertraining artefact; the objection is closed.
#   - CI includes 0 or turns negative -> the earlier negative result was
#     compute-bound; the README must be rewritten, not the run re-tuned.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROLE3="$ROOT/role3 improvement"
ROLE2="$ROOT/role2_규리"
OUT="$ROLE2/results/confirm-10x"

if [ -e "$OUT" ]; then
  echo "output already exists: $OUT" >&2
  echo "remove it first: rm -rf \"$OUT\"" >&2
  exit 1
fi

EPISODES=10000
VALIDATION_EVERY=250
EVAL_SEEDS=50

for SEED in 1 2 3; do
  echo "=== training seed $SEED ($EPISODES episodes) ==="
  ( cd "$ROLE3" && python3 train_gnn.py \
      --family spike \
      --episodes "$EPISODES" \
      --seed "$SEED" \
      --variant observed \
      --eval-seeds "$EVAL_SEEDS" \
      --validation-every "$VALIDATION_EVERY" \
      --out "outputs/v3_10x/train_$SEED" )
done

echo "=== evaluating on untouched confirmation seeds 2000-2199 ==="
( cd "$ROLE2" && python3 evaluate_conditions.py \
    --out results/confirm-10x \
    --confirm \
    --checkpoints \
      "../role3 improvement/outputs/v3_10x/train_1/gnn_spike_observed.pt" \
      "../role3 improvement/outputs/v3_10x/train_2/gnn_spike_observed.pt" \
      "../role3 improvement/outputs/v3_10x/train_3/gnn_spike_observed.pt" )

( cd "$ROLE2" && python3 report_conditions.py results/confirm-10x )

echo
echo "done: $OUT/comparison.md"
echo "compare with: $ROLE2/results/confirm-v1/comparison.md"
