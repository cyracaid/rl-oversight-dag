# Run BC, model misspecification and planning controls

Run from repository root. Requirements: Python 3, NumPy, PyTorch (existing scripts
already require these). No network/data download needed. No agent runs full data.

Read `experiments/BOUNDARY_PREREG.md` before execution. Historical BC table remains
untouched and unverified. New results use CRN and cannot be spliced into old tables.

## One command, all development runs

```bash
bash experiments/run_boundary.sh
```

Optional explicit output root/interpreter:

```bash
RUN_ROOT=runs/boundary-full-v1 PYTHON=python3 bash experiments/run_boundary.sh
```

Each child output directory must be new. Existing outputs fail rather than
overwrite. Pipeline errors propagate through tee. Long jobs run serially; open
separate terminals for independent training if memory permits. No time estimate
is promised. All-action depth-2 lookahead is substantially slower than one-step.

## Separate terminals / staged execution

```bash
# Terminal 1: BC + ordinary FT, five seeds; checkpoints saved before evaluation.
python3 -u experiments/rl_distill.py --graphs 800 --bc-epochs 4 \
  --episodes 20000 --seeds 1 2 3 4 5 --heldout 200 --kl-beta 0 \
  --out-dir runs/boundary-v1/bc

# Terminal 2: static REINFORCE.
python3 -u experiments/rl_boundary.py train --variant static \
  --seeds 1 2 3 4 5 --episodes 20000 --out-dir runs/boundary-v1/static

# Terminal 3: observed REINFORCE.
python3 -u experiments/rl_boundary.py train --variant observed \
  --seeds 1 2 3 4 5 --episodes 20000 --out-dir runs/boundary-v1/observed
```

After all three finish:

```bash
python3 -u experiments/rl_boundary.py eval \
  --checkpoints runs/boundary-v1/static/*.pt runs/boundary-v1/observed/*.pt runs/boundary-v1/bc/*.pt \
  --heldout 200 --bootstrap 10000 --out-dir runs/boundary-v1/misspec

python3 -u experiments/rl_boundary.py eval --scenarios matched --two-step \
  --checkpoints runs/boundary-v1/static/*.pt runs/boundary-v1/observed/*.pt runs/boundary-v1/bc/*.pt \
  --heldout 200 --bootstrap 10000 --out-dir runs/boundary-v1/planning
```

Other scenarios can be explicitly supplied to `--scenarios` for the planning
control if development data identify a candidate niche. Lock condition/candidate
before confirmation; use ONLY its five checkpoints, `--two-step --start 2000
--heldout 200 --scenarios CONDITION`, and a new output directory. Do not run all
conditions on confirmation data then pick a winner.

## Artifacts and verification

- `results.json`: configurations, source hashes, graph IDs, seed×graph outcomes.
- `results.md`: generated paired bootstrap contrasts, including FT−BC or
  learned−2-step when available. CI covers zero ≠ equivalence.
- `*.pt`: seed-specific weights, features, training config and provenance.
- Eval JSON additionally records checkpoint hashes, degeneracies and runtime.
- BC JSON records completed vs requested seeds and BC/FT training curves.

BC checkpoints and results are saved per completed seed. Interrupted runs can be
inspected as partial, but are not a full five-seed result. Training resume is not
implemented; use a new directory for reruns and record why. Failed/incomplete seed
selection is not a valid final comparison.

Regenerate a table without evaluation:

```bash
python3 experiments/rl_boundary.py report runs/boundary-v1/bc/results.json
python3 -m unittest discover -s experiments -p 'test_*.py'
bash -n experiments/run_boundary.sh
```

Send back `bc/results.json`, `misspec/results.json`, `planning/results.json`
and logs on failures. Smoke numbers are execution checks only, never findings.
