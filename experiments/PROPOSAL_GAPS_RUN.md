# Run proposal extensions

From repository root, use Python with NumPy and PyTorch installed. Existing
boundary experiments use the same dependencies. Record exact installed versions
from `results.json` rather than assuming environments match.

## Quick verification

```bash
python3 -m unittest discover -s experiments -p test_proposal_gaps.py -v
python3 -m unittest discover -s experiments -p test_boundary.py -v
python3 experiments/test_semantics.py
python3 experiments/proposal_gaps.py --out runs/proposal-gaps-smoke-local --episodes 2 --seeds 1 --graphs 3 --bootstrap 20 --confidence normal noise oracle
```

The smoke runs all 24 combinations. Output-directory reuse is refused. Small
runs are explicitly labelled `smoke`; their CIs are debugging output only.

## Full development run (user executed)

```bash
python3 experiments/proposal_gaps.py --out runs/proposal-gaps-full-v1 --episodes 20000 --seeds 1 2 3 4 5 --graphs 200 --eval-start 1000 --bootstrap 10000 --confidence normal noise oracle
```

This is 24 methods/conditions ×5 seeds ×20,000 episodes: 2.4 million training
episodes, plus evaluation. It runs sequentially with one PyTorch thread. No
runtime estimate is established. For smaller separate jobs select one confidence,
feature or method and a unique output directory; preserve all requested cells.
No resume is implemented. Interrupted jobs retain completed checkpoints and an
`in_progress` JSON; they must not be treated as complete results.

`ac` uses a learned critic with full-horizon Monte Carlo targets. `nstep3` and
`nstep5` use a learned critic with 3/5-step bootstrap. `reinforce` uses an EMA
scalar baseline. All use gamma=1, terminal-only reward, identical masked GNN,
temperature schedule and gradient clip. Critic shares no policy parameters.
These are fresh baselines, not reproductions of legacy numerical tables.

Saved `results.json` contains config, source hashes, environment versions, every
training-episode error, checkpoint hashes, seed-by-graph outcomes and posterior
degeneracy counts. `results.md` is generated from the saved JSON. Intervals compare
each learned policy against belief greedy using crossed seed/graph bootstrap.
They are pointwise intervals, not multiplicity-corrected claims across the factorial.
Drift arrays are indexed by chronological position; bootstrap summaries describe
this fixed schedule, not uncertainty over possible drift processes. No automatic
model selection, success declaration or confirmatory run is performed.

## Independent reproduction

Teammate: clone repository into a new directory, checkout the published commit,
install dependencies in a fresh environment, run tests and the identical full
command with a fresh output directory. Return commit, command, Python/PyTorch/NumPy
versions, output/checkpoint SHA256 values, exit status and discrepancy notes.
Different hardware/versions may not reproduce bitwise; compare paired raw arrays
and explicitly explain deviations. Reproduction remains pending until returned.

Before using 2000–2199 as confirmation, freeze candidate, criteria and schedule in
a separate protocol. A CLI seed change alone does not make a run confirmatory.

## Scope and current status

Gain inputs, learned critic, n-step targets, real message-passing confidence
conditions and chronological true-error drift now have implementation and smoke
coverage. Full scientific runs, independent confirmation and teammate reproduction
remain pending. SciForge production integration is not implemented by this work.
Existing API 502 diagnostics are a separate workstream.
