# Supervisor axis — what a delivery can say about its own coverage

Block 5400–5599, p_catch 0.9, pre-registered in `PREREGISTER_SUPERVISOR.md`.

Policy register: `v1:p_catch>=0.90:statuses=4:perspectives=6:constructs=2` — the adjudicated objects this report is rendered under, frozen in `AUDIT_POLICY.md` v1. A different register would describe a different delivery, so the string is quoted rather than implied.

`declared share` = of the sink errors that survive the budget, the fraction the honest receipt labels `partial` or `untouched`. The rest sit inside sinks whose every upstream source was reviewed — that is `p_catch < 1`, not a reporting bug.

| family | policy | errors/graph | surviving sink errors | declared | false-inspected | declared share | verdict |
|---|---|---:|---:|---:|---:|---:|---|
| spike | marginal | 0.965 | 193 | 188 | 5 | 0.974 | load-bearing |
| spike | oracle | 0.725 | 145 | 124 | 21 | 0.855 | weak |
| modular | marginal | 8.835 | 1767 | 1587 | 180 | 0.898 | weak |
| modular | oracle | 3.895 | 779 | 663 | 116 | 0.851 | weak |
| real | marginal | 0.450 | 90 | 88 | 2 | 0.978 | load-bearing |
| real | oracle | 0.365 | 73 | 57 | 16 | 0.781 | weak |
| ticket | marginal | 0.275 | 55 | 46 | 9 | 0.836 | weak |
| ticket | oracle | 0.245 | 49 | 29 | 20 | 0.592 | weak |

## Predictions

| | prediction | outcome |
|---|---|---|
| P1 | identical actions with and without the receipt | holds (0 mismatching runs) |
| P2 | honest fidelity 1.0 everywhere | holds (min 1.000) |
| P3 | some family has false-inspected sinks | holds — modular, real, spike, ticket |
| P4 | declared share ≥ 0.90 on spike and modular | spike 0.974, modular 0.898 — fails |
| P5 | oracle's declared share < marginal's on modular | 0.851 vs 0.898 — holds |

## The one prediction this block falsified

P4 asked for a declared share of at least 0.90 on `modular` and got 0.898 — short by 0.002 (1587 of 1767). The threshold is not moved. So on the 500-node family about one surviving error in ten sits in a sink whose every upstream source was reviewed and whose catch still missed. Better coverage makes that bucket *bigger*, not smaller: 10.2 % under the rule, 14.9 % under `oracle`. Coverage and correctness pull apart exactly as `p_catch = 0.9` predicts, and a delivery that reports only coverage would overstate itself more, not less, when it reviews more.

## The deletion test, as a number

The `silent` arm runs the identical policy on the identical episode. Its `declared_gap` and `uninspected_errors` columns are empty, because the delivery has no field for them: the question "how many of the surviving errors did we not cover" has no answer, not a bad one. The `overclaim` arm does answer, and its answer is wrong by exactly the number of surviving errors: it equals the surviving errors in every cell.

So the three arms differ in nothing but the statement, and the statement is what turns a count of errors into a count of *uncovered* errors.

## Bound on this claim

* `p_catch` is 0.9, so `inspected` cannot mean `clean`. Every false-inspected sink in the table is that gap, not a bug.
* No escalation policy is preregistered: `judged` is 1.0 on every row, so no refusal inflates fidelity.
* Nothing here is about calibration. The receipt is about scope, never truth.
* `modular`/`spike` sinks may be structurally unreachable within the budget; that is exactly what `untouched` reports, and it is a finding about the budget, not about the receipt.

## Provenance

The report is a rendering, not a computation: every number above is read from `summary.json`, which was written once on the block named at the top. What produced it is quoted here so a reader does not have to trust the prose.

| item | value |
|---|---|
| policy register | `v1:p_catch>=0.90:statuses=4:perspectives=6:constructs=2` |
| block / episode offset | 5400–5599 / 20000 |
| p_catch | 0.9 |
| budgets | spike 16, modular 50, real 8, ticket 8 |
| python / numpy | 3.13.5 / 2.4.4 |
| `dag_role3/environment.py` | `c9844ed5b4cf7f2387db986d4f2cfc372e461c6d6660dd93088af743ba76d9dd` |
| `dag_role3/supervisor.py` | `d28af44ab459a525ec5102524c24de90c6f15b948d09ba4c2711631f3d201c41` |
| `run_supervisor_check.py` | `da6c311ef31c2b3efe88f56a136a40547c784230f8236f5d0d45a3d39fffd920` |

Deleting this report leaves `outputs/supervisor-v1/summary.json` intact — the counts survive, the *statement about what they cover* does not. That asymmetry is the deletion test in `CLAIM_GRAPH_CONTRACT.md`, and it is why this file quotes the register it was rendered under.
