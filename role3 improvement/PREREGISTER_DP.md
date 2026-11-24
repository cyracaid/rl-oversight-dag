# Pre-registration — exact DP ceiling on the belief model the rule uses

Frozen 2026-11-24, before `exact_dp.py` was run for the first time. Written because
every other number in this repo went through the same gate: rules and verdicts fixed
before the seeds are spent.

## Question

The marginal rule is a *one-step* approximation: it scores nodes with the reverse
derivative of expected sink errors and takes the arg-max. Nobody has measured how far
that is from the **best possible policy inside its own model**. Two-step planning was
tested (`+0.035 [−0.025, +0.100]`, not supported) but two-step is a local probe, not a
ceiling.

So: on graphs small enough to solve exactly, what is the gap between

1. `marginal` — the deployed rule,
2. `greedy_exact` — one-step lookahead on the *exact* expected cost of the same model,
3. `dp_K` — the optimal finite-horizon policy of that model, budget `K`.

If `dp_K − marginal` is small, the saturation claim is not a property of the heuristic;
it is a property of the problem. If it is large, the rule is leaving value on the table
and the project's main negative result is about *our rule*, not about review scheduling.

## What model is solved, exactly

The mean-field belief MDP the environment already exposes:

- belief `base[i]` = P(local source error at `i` | confidence, type), from `initial_belief`;
- public effective risk by one forward pass over the topological order;
- cost of a belief state = expected number of wrong sink values, `sum_{sinks} p_eff`;
- review of node `a` flags with probability `p_catch · p_eff[a]`; a flag sets `base[a]=0`,
  a miss applies the node-local Bayes update `base[a] · (1−c) / (1 − c·base[a])`.

**Declared deviation.** The environment's miss-update uses the *inherited* risk
`p_eff[a]` in the denominator; the DP uses the *local* `base[a]` so that the belief is a
function of (reviewed set, flag pattern) and the state space stays enumerable. On source
nodes (no parents) the two are identical. This is a deviation in the belief update, not
in the cost function, and it is reported with the result rather than hidden.

This is **not** the true POMDP optimum. It is the exact optimum of the same approximate
model the deployed rule optimises greedily. That is the number a reviewer asks for, and
it is weaker than "optimal oversight".

## Seeds

Fresh block **60000–60023**, never used by anything in the repo.

- real family: 60000–60011 (12 graphs)
- ticket family: 60012–60023 (12 graphs)
- budgets `K ∈ {1, 2, 3, 4, 5}`; `n = 21` for both families
- `p_catch = 0.9`, confidence mode `normal`

## Frozen predictions

| # | Prediction | Falsified if |
|---|---|---|
| P1 | `greedy_exact` ≤ `marginal` in at least 10 of 12 graphs, mean gain ≤ 0.02 expected errors | mean gain > 0.05, or loses in ≥ 3 graphs |
| P2 | Value of planning, `dp_5 − greedy_exact`, ≤ 0.02 expected errors on real | > 0.05 |
| P3 | Value of planning grows sub-linearly in `K`: `dp_5 − dp_1` < `2 × (dp_3 − dp_1)` | ratio ≥ 2 |
| P4 | `dp_1` and `greedy_exact` agree to 1e-9 (sanity check on the implementation) | any cell differs |
| P5 | `dp_5 − marginal` < 0.10 on both families, i.e. the saturation claim survives the ceiling | ≥ 0.10 on either family |

P5 is the one that matters. If it fails, the honest conclusion changes from "review
scheduling is saturated" to "our rule is 0.1+ errors short of optimal", and the
saturation claim has to be re-scoped in `CROSS_IMPLEMENTATION_VALIDATION.md` §3.

## Verdict code

`exact_dp.py --report` writes `outputs/dp-ceiling/report.md` and evaluates P1–P5 from
the CSV. Predictions are not edited after the run; a failed prediction is kept with the
word `contradicted`, as in `scope-robust-v1`.
