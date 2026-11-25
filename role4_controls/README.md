# role4_controls — structural controls and worst-of-n (Person 4)

Answers `TEAM_REQUESTS_P4_P5.md` → Person 4. The claim under test: **the graph is doing the
work** — `marginal` (and `structural`) beat sort-by-confidence because they use how errors travel,
not because any ordering with a good error prior would do as well.

## How to run

```bash
pip install numpy networkx          # networkx: the frozen graph generator imports it (BA/ER)
python3 run_controls.py --selftest  # invariants only; prints no control outcome
python3 run_controls.py --out results/
```

No GPU, no torch, no real data. About 3 minutes on one CPU core.
`results/controls.md` is written by hand **from** `results/controls_summary.csv`; every number in it
is a cell of that file.

Acceptance note: the request says "numpy only". The frozen `dag_role3/graphs.py` imports
`networkx`, so numpy alone is not enough for any script that builds these graphs. Nothing else is needed.

## What is frozen

| Item | Value |
|---|---|
| Environment | `role3 improvement/dag_role3`, tag `role3-env-v3`, imported, not copied or changed |
| Graphs | `generate_graph(family, seed)`, seeds **90000–90099**, the frozen benchmark's graphs |
| Episodes | `sample_episode(graph, 20000 + seed)`, as in `run_benchmark.py` |
| Budget | spike 16, real 8, modular/BA/ER 50, as in `run_benchmark.py` |
| Policies | `confidence`, `structural`, `marginal` |
| CI | paired bootstrap copied verbatim from `run_benchmark.interval` (seed 411, 20 × 100) |

## Frozen before outcomes

This section, `run_controls.py` and the selftest were committed **before** any flatten or rewire
outcome was computed. The commit that adds results comes after it.

### Conditions (all paired on the same graph and the same episode)

- **intact** — `run_public_policy(graph, snapshot, ...)`, exactly the frozen benchmark call.
  Acceptance: errors *and* action sequences must equal `outputs/v3/benchmark_role3.csv` row by row;
  otherwise the script stops with exit code 2 and writes nothing.
- **flatten** — the same snapshot with every `edge_coins` value set to `False`. Source errors,
  confidences, reviewer draws and the edge probabilities the policy sees are unchanged. Errors stay
  where they start; the policy still plans as if they travel.
- **rewire** — the policy plans on a rewired copy of the graph; errors keep travelling on the true
  graph with the true edge coins. This is the version that tests the claim: if a *wrong* map does as
  well as the right one, the specific structure is not doing the work. (If policy and errors both
  moved to the rewired graph, it would be just another random graph and the control would test
  nothing about our structure.)

  Rewire rule, per graph, `rng = random.Random(4_040_000 + graph_seed)`, nodes in index order:
  - every node keeps its **number of parents**, its **type**, and the **sink set** is kept;
  - spike: new parents drawn without replacement from the **previous layer** (the generator's rule);
  - real: from all nodes in **strictly lower layers**;
  - modular / BA / ER: from **all nodes with a lower index** (the originals are oriented by index;
    "all other nodes", as the request words it, would allow cycles).

  Because each node keeps its parent count, `sample_episode(rewired, same seed)` consumes the random
  stream identically: source errors, confidences and reviewer draws are asserted identical.
  `MapMismatchEnv` recomputes only the hidden error state on the true graph; with view = truth it
  reproduces the frozen environment exactly (selftest).

### Statistic and verdict

`gain = errors(confidence) − errors(policy)` per graph (positive = policy better), mean with paired
95 % CI. `gain_removed_vs_intact = gain(intact) − gain(control)`, paired CI.

Label per (family, control, policy), fixed in `verdict()`:

| Label | Rule | Reading |
|---|---|---|
| `no-intact-advantage` | intact CI lower bound ≤ 0 | nothing to explain; the control is uninformative for this cell |
| `removed` | intact lower > 0 and control lower ≤ 0 | the advantage does not survive the control |
| `survives` | intact lower > 0 and control lower > 0 | the advantage survives — for **rewire this is a problem** and is reported as one, even if it shrank |

Primary cells: `marginal` on spike, modular, BA, ER. `real` is expected to be uninformative
(frozen gain +0.03 [0.00, 0.07]); it is run and reported, not used for the verdict.

## worst-of-n

`results/benchmark_worst_of_n.csv`: for every policy already in `benchmark_summary.csv`, the fraction
of the 100 graphs where the policy leaves **at least one** sink error (`worst_of_n`), the count, the
maximum and the 95th percentile. It is a groupby over `outputs/v3/benchmark_role3.csv`; the frozen
files are not touched. `worst_of_n = 1 − zero_error_rate` of the frozen summary by construction.

## Blocked

27/48 consensus split — waiting for P5's labels. Not attempted, no split invented.
