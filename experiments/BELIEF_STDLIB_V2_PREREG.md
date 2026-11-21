# Standard-library belief v2: protocol frozen before the full run

Date: 2026-11-21. Status: harness validated by unit tests and a tiny smoke run only.
**No v2 numbers exist and none are asserted here.** The user executes the full run.

History. v1 (`BELIEF_STDLIB_PREREG.md`, verdict in `BELIEF_STDLIB_V1_INTERPRETATION.md`) did not pass its equivalence gate: the
200-graph interval for (stdlib − numpy) was [−0.175, +0.045] against a ±0.10 margin, because the paired sd was 0.79 and a
200-graph interval therefore cannot be narrower than about ±0.11. Its latency gate was met trivially on four-layer graphs.
v1 code and results are unchanged. **v2 was designed after seeing v1**; the sd, the share of differing graphs (14.5%) and the
allowance below come from v1's development graphs, so only a pass on the new, unseen seeds is new evidence.

## Discipline

Same as v1 and `BOUNDARY_PREREG.md`. **Agents run only `--smoke` and unit tests.** The output directory must be new.

## What changes from v1

| item | v1 | v2 |
|---|---|---|
| graphs | 200 (seeds 1000-1199) | **1,000 new graphs (seeds 5000-5999)**; the reserved confirmation seeds 2000-2199 stay untouched |
| noise floor | none | each graph is also run with the numpy original under a **different particle seed** |
| equivalence criteria | E1 only | **E1** and **E2** (below) |
| latency graphs | 4 layers | 4, 10 and 20 layers (the generator needs the layer count to divide the node count) |
| latency gates | rank every node at N = 80 (0.5 s) and 500 (5 s) | rank every node at 80 nodes / 10 layers within 0.5 s, at 500 nodes / 20 layers within 5 s, and **one observation at 500 nodes / 20 layers within 0.5 s** |

Unchanged: model, 1,024 particles, budget 16, propagation 0.6, catch 0.9, belief-greedy policy, shared hidden errors and reviewer
randomness between implementations, bootstrap with 10,000 draws.

## Gated criteria

- **E1 (equivalence).** The 95% bootstrap CI of the paired mean difference (stdlib − numpy) lies inside ±0.10. With about 1,000
  graphs and a paired sd near 0.8 the half-width is about 0.05, so the criterion can be met when the true difference is small.
- **E2 (noise floor).** The share of graphs whose outcome differs between the port and the original is at most the share that
  differs between the original and a reseeded copy of itself **plus 0.05**. The port may change outcomes on at most five points
  more graphs than ordinary particle noise does. The 0.05 allowance is a judgement call informed by v1.
- **L (latency, stdlib implementation, median of 5 repeats).** Rank every node: ≤ 0.5 s at 80 nodes / 10 layers, ≤ 5 s at 500 nodes
  / 20 layers. One observation: ≤ 0.5 s at 500 nodes / 20 layers. The other rows are reported, not gated.

Limits may be revised only before the first v2 full run, with the reason committed.

## Verdict rule

**v2 passes only if E1, E2 and all three latency gates hold.** If it passes, the standard-library implementation is the one to port
into evidence-dag (decision 0.2, option A) and numpy is not added as a runtime dependency. If it fails, diagnose from the saved per-graph
errors, the noise floor and the latency table, change one thing and write a v3 protocol before running. Do not relax the margins after
seeing results.

## Command (run from the repository root)

```bash
cd ~/Documents/강화학습 && python3 -u experiments/compare_belief_stdlib_v2.py --out-dir runs/belief-stdlib-v2
```

No time estimate is promised: it runs three policy simulations per graph on 1,000 graphs. Tiny harness check: `--smoke` (not evidence).

## What a pass means and does not mean

A pass means the port reproduces the original's decisions on 1,000 unseen synthetic graphs to within particle noise and that ranking and
updating stay within the limits on graphs up to 500 nodes and 20 layers. It does **not** show that the ranking helps on real evidence
graphs, that latency holds for graphs larger or denser than those tested, or that real node priors and edge probabilities are calibrated.
