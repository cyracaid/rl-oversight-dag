# Local full-v1 artifact receipt

Repository: `cyracaid/rl-oversight-dag`, worktree branch
`feat/proposal-gap-experiments`. Training source commit:
`1197e4bc2c05e56bf17d3507dfeeedab8a6ca943`.

Artifacts remain local under `runs/`; no checkpoints, raw training curves or
step traces are included in Git. This receipt identifies existing files, not a
public download location. Ask the run owner for artifacts before checkpoint replay.

## SHA256

| Local path | SHA256 |
|---|---|
| `runs/proposal-gaps-full-v1/results.json` | `1eea7b52a7912b2ddd6f8195975662fa67f1f215597f657b25a0fc7379d9c66f` |
| `runs/proposal-gaps-full-v1/analysis.json` | `f4e549fd735d3e05234a22c0a276af3b7fea95396e2223250d6493e512d0815d` |
| `experiments/diagnose_proposal_gaps.py` | `e3a63ff908e4873437a68876bf6b1f93566f21163000110088f0ba9594e035ca` |
| `runs/proposal-gaps-diagnosis-v1/summary.json` | `b44b7830489580cbd6525c374f551d3e069497b1cecc043e92e34ba3885add7e` |
| `runs/proposal-gaps-diagnosis-v1/summary.csv` | `d99aaa045b9ea428f9f916546f45c03ab71979336086dec5b951764388d43a18` |
| `runs/proposal-gaps-diagnosis-v1/episodes.csv` | `1d04ac753d4b042f2e2f8351761d46e1b3aa1308f060ddbcfeb4b09b1307abaa` |
| `runs/proposal-gaps-diagnosis-v1/steps.jsonl.gz` | `caeafdd24bd86c928cfa56251202119596d8492472467762c03ec09d1e83c2ee` |

Original `results.json` contains all 120 checkpoint SHA256 values and the source
manifest. Diagnostic `manifest.json` contains the 30 replayed checkpoint hashes,
environment versions, graph IDs, script hash, input hash and output hashes. Verify
those receipts against actual files before use. Gzip container hashes may differ
on a fresh replay; compare decoded records and original outcome arrays as well.

## Evidence and limits

Full-v1: 120 checkpoints, 2.4 million training episodes, five seeds, six evaluation
conditions, development graphs 1000–1199. Frozen analyzer completed; all eight
primary adjusted intervals favor belief greedy.

Diagnostic replay: selected observed/nstep3 and gain/nstep3, all five seeds, all
six conditions, plus one greedy trajectory per graph. Completed 13,200 episodes
and 211,200 steps; every final error and degeneracy count matches its original.
These are same-environment replay checks. Independent confirmation, clean-clone
reproduction and real-system acceptance are not established.
