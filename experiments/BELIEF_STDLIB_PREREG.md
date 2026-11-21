# Standard-library belief: protocol frozen before the full run

Date: 2026-11-21. Status: implementation validated by unit tests (exact enumeration, comparison with the numpy original) and a
tiny smoke run only. **No full-run numbers exist and none are asserted here.** The user executes the full run.

Purpose: OpenSpec change `add-belief-review-ranking`, tasks 1.1-1.3 and the dependency decision 0.2. evidence-dag's Python runtime is
standard-library only (`dependencies = []`), while `belief.py` uses numpy for sampling, packing and resampling. `belief_stdlib.py`
is a numpy-free port with the same model and public methods. Before any belief ranking enters the product it must (a) give the same
review outcomes as the original and (b) be fast enough. Everything here is synthetic; real evidence graphs are not used.

## Discipline

Same as `BOUNDARY_PREREG.md`: every claim traces to saved raw results, configuration and source hashes; tables come from saved JSON;
never hide a failure, choose the best seed, overwrite a run or rewrite a hypothesis after seeing results. **Agents run only
`--smoke` and unit tests.** The output directory must be new.

## What was already checked by unit tests (not part of the gate)

On a four-node graph with seven binary sources of uncertainty, the prior error probabilities, the base probabilities, the gain of
every node, the posterior after a flag, after a clean review and after a sequence of two observations, and the greedy action all
agree with **exact enumeration** within Monte-Carlo tolerance, and the numpy original agrees with the port on the same model.
Degenerate observations (a flag no particle explains; an observation the model excludes) are counted, not a division by zero.
The two implementations draw **different particles for the same seed**, so they cannot be compared bitwise.

## Equivalence (gated)

- Graphs: the 200 development graphs (graph seeds 1000-1199), N = 80, budget 16, 1,024 particles, propagation 0.6, catch 0.9.
- For each graph both implementations run the adaptive belief-greedy policy against the same hidden errors and the same
  reviewer randomness; the primary outcome is residual sink errors after the budget (lower is better).
- Statistic: paired difference (stdlib − numpy), mean and a 95% bootstrap interval over graphs (10,000 draws, seed 20261121).
- **E1 (gate).** The interval lies inside ±0.10, the equivalence margin used for earlier non-inferiority comparisons. This
  does not claim bitwise identity, and 200 graphs cannot resolve differences much smaller than the margin.
- Diagnostics (not gated): degenerate-observation counts, share of graphs where the first chosen action agrees, seconds per graph.

## Latency (gated)

- Graphs of 80, 200 and 500 nodes (same generator, 4 layers), 1,024 particles, median of 5 repeats of: construction, computing
  the gain of every node (what a ranking needs, run once per scientific state), and one observation.
- **L1 (gate).** Median time to compute every node's gain with the standard-library implementation: at most **0.5 s at 80
  nodes** and at most **5 s at 500 nodes**. The ranking is computed once per compile in the background, next to model calls that take
  seconds; these limits are judgement calls and may be revised only before the first full run, with the reason committed.
  The 200-node row is reported, not gated.

## Verdict rule

**The port passes only if E1 and L1 (both sizes) hold.** If it passes, the standard-library implementation is the one to port
into evidence-dag (decision 0.2, option A) and numpy is not added as a runtime dependency. If it fails on latency, reduce particles
or restrict the ranking to a candidate subset and write a new protocol before running; if it fails on equivalence, diagnose from the
saved per-graph errors and degenerate counts and write a new protocol. Do not relax the margin or the limits after seeing results.

## Command (run from the repository root)

```bash
cd ~/Documents/강화학습 && python3 -u experiments/compare_belief_stdlib.py --out-dir runs/belief-stdlib-v1
```

No time estimate is promised: it runs both implementations on 200 graphs. Tiny harness check: `--smoke` (not evidence).

## What a pass means and does not mean

A pass means the port reproduces the original's decisions on synthetic graphs of the development set and ranks every node fast
enough at the tested sizes. It does **not** show that the belief ranking helps on real evidence graphs (earlier experiments
established it only on synthetic graphs, development set), that the port's latency holds for larger or denser real graphs, or that
node priors and edge probabilities in a real chain are calibrated (see the propagation-recovery protocols).
