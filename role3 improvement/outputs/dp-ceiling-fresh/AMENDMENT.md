# Amendment — the first DP run reported on a block that was not fresh

Date: 2026-11-25, one day after the first run and after the ceiling had been folded into
`BENCHMARK_SPEC.md`, `REPO_UPDATE_*` and the course report.

## What was wrong

`PREREGISTER_DP.md` §"seed block" says the ceiling is computed on

> Fresh block **60000–60023**, never used by anything in the repo.

That sentence was false. `dag_role3/training.py` evaluates every trained model on
`range(60000, 60000 + count)` through `BestValidation`, and `PREREGISTER_PPO.md` names
60000–60029 as the validation block. So 60000–60023 is the **model-selection** block: GNN,
DQN and PPO all used it to choose their checkpoint. `BENCHMARK_SPEC.md` §3 had it recorded
that way at the time (row `validation | 60000–60029 | model selection only`), and the DP
pre-registration did not check that row.

Nothing leaked into the DP numbers themselves — the ceiling is an analytic optimum of the
belief model and never touches a trained network. What broke is the one thing that makes
the result citable under this repo's rules: **a block is spent once it has been used to
choose a method or a threshold**, and the reported graphs were sitting on a spent block.

## What is rerun, and where

Same model, same code path, same five frozen predictions from `PREREGISTER_DP.md`; only the
graphs change to a block nothing has used:

| family | block | graphs |
|---|---|---|
| `real` | 5000–5011 | 12 |
| `ticket` | 5012–5023 | 12 |

5000–5023 is the free range the ledger names. 5200–5399 is reserved by
`PREREGISTER_PLANNING_V2.md`, and 5400–5599 by `PREREGISTER_SUPERVISOR.md` — an earlier
attempt at this rerun was started on 5400–5423 and abandoned after ten graphs when that
reservation was found; those rows were deleted rather than reported. The old run in
`outputs/dp-ceiling/` is kept unchanged as a sensitivity check; it is **not** deleted and
**not** rewritten.

## What is frozen and what is not

Frozen, untouched: `PREREGISTER_DP.md`, its five predictions, its thresholds (P2
falsification at 0.05), the model definition, the budget set, `p_catch = 0.9`, and
`exact_dp.py`'s policy code. The only code change is that the seed block is now a command
line argument (`--seed-starts`) instead of a constant that a reader has to trust — the
failure was caused by a constant nobody checked against the ledger.

The acceptance rule, written before the rerun:

- the rerun is reported in full, whichever way it comes out;
- if it disagrees with the first run on a verdict, both are reported and the disagreement
  is the finding;
- the first run is cited only as a sensitivity check on a spent block, with that stated.

## Rerun

Command (block on the command line, not in a constant):

```
cd "role3 improvement"
python3 exact_dp.py --seed-starts real=5000,ticket=5012 --out outputs/dp-ceiling-fresh
python3 exact_dp.py --report --out outputs/dp-ceiling-fresh
```

All five frozen predictions hold again, on graphs nothing had used:

| # | prediction | first run (60000–60023, spent block) | rerun (5000–5023) |
|---|---|---|---|
| P1 | `greedy_exact` ≤ `marginal` in ≥10/12 graphs, mean ≤ 0.02 | mean +0.0001, 12/12 | mean +0.0006, 12/12 |
| P2 | planning value ≤ 0.02, falsified above 0.05 | +0.0219 (nominal miss 0.0019) | +0.0283 (nominal miss 0.0083) |
| P3 | sub-linear in K | ratio 1.73 | ratio 1.81 |
| P4 | `dp1 == greedy_exact` | 0.00e+00 | 0.00e+00 |
| P5 | `dp5 − marginal` < 0.10 on both families | −0.0219 / −0.0059 | −0.0299 / −0.0017 |

The size moved and the direction did not:

| family | `marginal`@K=5 | `dp5 − marginal` | share of the rule's own errors |
|---|---:|---|---:|
| `real` | 0.705 | −0.030 [−0.065, −0.008] | **4.2 %** (first run: 2.5 % of 0.873) |
| `ticket` | 0.404 | −0.002 [−0.003, −0.000] | **0.5 %** (first run: 1.4 % of 0.419) |

Reading: on the clean block the in-model optimum is worth **4.2 %** of the rule's residual errors on `real`
and 0.5 % on `ticket`, both intervals excluding zero, against an `oracle` gap that asks for a third to a half
of those errors. The rerun therefore makes the claim slightly **weaker** than the first run did on `real`
(4.2 % vs 2.5 % of a smaller base) and still leaves it in single-digit percent. Everything cited in the docs
now uses the rerun; the first run is quoted only as a sensitivity check.

## Where the old numbers still appear on purpose

Two frozen documents still carry the first run's figures and were **not** edited:

- `PREREGISTER_DP.md` — the false "never used by anything" sentence and the block name stay
  exactly as committed, because a pre-registration that is silently corrected is worth less
  than one that is wrong and annotated. This file is the annotation.
- `PREREGISTER_SUPERVISOR.md` — its motivation paragraph quotes "0.022 errors per graph
  against a 5–7 error gap (`outputs/dp-ceiling/`)". The number it quotes has moved to 0.030
  on a clean block; the direction and the order of magnitude did not, and the supervisor
  result does not depend on it. Left frozen, recorded here.

Everything else in the repository — course report (all three languages), paper draft (all
three), `BENCHMARK_SPEC.md`, `README.md`, `REPO_UPDATE_*`, `CROSS_IMPLEMENTATION_VALIDATION*`
— cites 5000–5023 and the rerun's numbers.

