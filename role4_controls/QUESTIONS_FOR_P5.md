# Person 4 → Person 5 (Cyra): did I do what you asked?

Branch `p4/role4-controls`. Answers `TEAM_REQUESTS_P4_P5.md` → Person 4. Everything below can be rerun with
`python3 role4_controls/reproduce.py --full --jobs 4`; it compares every output byte-for-byte with the committed file.

## What is in the branch

| Commit | What |
|---|---|
| `af29f1c` | v1 rules frozen (README "Frozen before outcomes"), pushed **before** any outcome |
| `31acdae`, `1377653` | v1 results: `controls.csv`, `controls_summary.csv`, `controls.md`, `benchmark_worst_of_n.csv` |
| `6eb215d` | post-hoc diagnostics made reproducible (`diagnostics.py`; numbers unchanged) |
| `7f58534` | **v2 amendment** frozen before any v2 outcome: hub-breaking rewire, 10 draws/graph, 3-level verdict (20 % margin) |
| `f2c2fbe`, `7b7e5dd` | v2 results (`results/v2/`) |
| `c07aedc` | fresh-block confirmation (7100–7199) frozen before running |
| `c5ebb06` | `reproduce.py`, `EXPLAINER_KO.md`, this file |
| latest | confirmation results `results/v2_confirm/` — 11/11 primary labels replicated |

Acceptance checks that passed: `intact` equals `outputs/v3/benchmark_role3.csv` on all 1,500 shared rows
(errors **and** action sequences); v2 `flatten` and rewire draw 0 equal v1 row by row; v1 was rerun on my own
machine (macOS, Python 3.13, numpy 2.5.5, networkx 3.7) with a clean `git status`.

## Headline (`marginal` vs `confidence`, paired over 100 graphs, mean [95 % CI], v2)

| family | intact | flatten | rewire_index (10 draws) | rewire_order (hub-breaking, 10 draws) |
|---|---|---|---|---|
| spike | +0.37 [+0.20, +0.56] | +0.09 [+0.03, +0.15] survives | −0.97 [−1.18, −0.76] | — |
| modular | +1.81 [+1.10, +2.56] | +0.01 [−0.10, +0.13] removed | −7.19 [−8.15, −6.24] | −7.97 [−8.89, −7.11] |
| BA | +9.52 [+4.25, +15.99] | −0.58 [−0.77, −0.38] removed | **+6.99 [+1.74, +13.42] survives** | −19.41 [−25.20, −13.03] |
| ER | +4.99 [+3.52, +6.61] | −0.35 [−0.48, −0.23] removed | **+1.54 [+0.40, +2.86] survives** | −11.63 [−13.04, −10.21] |
| real | +0.03 [+0.00, +0.07] | no intact advantage | no intact advantage | — |

My reading: the gain needs propagation (flatten) and the true structure (a wrong map hurts). On BA and ER the part
of the structure that matters is *who the hubs are*: a wrong map that keeps hub positions keeps most of the gain; one
that breaks them reverses it. The flip side is a limit: with a wrong graph, `marginal` is worse than ignoring the graph.

## Questions — please answer each with yes / no / what instead

**Q1. rewire semantics.** I implemented rewire as a *map mismatch*: the policy plans on the rewired graph, while errors
still travel on the true graph with the true edge coins (`MapMismatchEnv`, which equals the frozen env when
view = truth; selftest). My reason: if both policy and errors move to the rewired graph, it is just another random
graph that the policy knows exactly, so "the advantage survives rewire" could never be "a real problem", as your
request says it would be. Flatten, as you specified it (policy still sees edge probabilities), is also a mismatch.
Is that what you meant? If you meant the consistent version, I will pre-register and add it rather than replace this.

**Q2. Candidate pool deviation.** Your spec says parents are redrawn "from all other nodes (modular/BA/ER)". I used
*all nodes with a lower index*, because "all other nodes" can create cycles and `DAG()` rejects them. This choice
keeps hub positions on BA/ER (out-degree rank correlation 0.63 / 0.62, `results/diagnostics.csv`) and is what let
BA survive v1. Acceptable as v1, with v2's hub-breaking rule as the correction?

**Q3. The v2 amendment.** After reading v1 I froze and pushed v2 (`7f58534`) before running it: (a) the
hub-breaking `rewire_order`, (b) ten fixed-seed draws per graph, draw 0 = v1, (c) a three-level verdict with an
equivalence margin of ±20 % of the intact gain. v1 stays as reported. Is an amendment like this acceptable under
the repo's pre-registration rules, and is 20 % a margin you are comfortable with?

**Q4. Label for "clearly worse".** Under the frozen v2 rule, a control CI entirely *below* −margin is labelled
`inconclusive` (the label is reserved for "inside ±margin" = `removed`). Every wrong-map cell that makes `marginal`
clearly worse than `confidence` therefore reads `inconclusive`; `controls_v2.md` states the direction for each.
Keep the frozen label as is (my preference), or do you want a separate label in a later, separately pre-registered version?

**Q5. Fresh-block confirmation and the ledger.** Because v2's rules were chosen after seeing v1 on 90000–90099, I
pre-registered (`c07aedc`) and ran one confirmation of the unchanged v2 code on graph block **7100–7199**, which no
file in the repo used. **11 of 11 primary cells kept their label** (`results/v2_confirm/confirm.md`). Please add
7100–7199 (episodes 27100–27199) to the seed ledger as spent by role 4, or tell me if that block was reserved for you.
The rewire RNG streams `Random(4_040_000 + 100_000·k + seed)` and `Random(5_050_000 + 100_000·k + seed)` are draw
seeds, not graph blocks; list them too if you want.

**Q6. Where the result goes.** Your request says these controls belong in the abstract. `PAPER_DRAFT.md` and
`COURSE_FINAL_REPORT.md` do not mention flatten/rewire yet. Will you integrate, or should I draft the paragraph?
Suggested wording: *"Removing propagation removes the advantage (modular, BA, ER: within ±20 % of zero); a wrong map
removes or reverses it; on hub graphs the gain rests on hub identity — and with a wrong graph, graph-aware review is worse than ignoring the graph."*

## For information (decided, no answer needed)

- `benchmark_worst_of_n.csv` lives in `role4_controls/results/`, not next to the frozen summary, so nothing is written
  into `role3 improvement/outputs/v3/`.
- The 27/48 consensus split is dropped from Person 4's scope; it is not attempted.
- I will open the PR to `main` once all files are final; P1 does the code review, as for role 2.

