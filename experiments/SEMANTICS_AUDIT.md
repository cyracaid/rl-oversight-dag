# Semantics audit: what a review actually does

> Written 2026-11-09 after an external review flagged `belief.py`. Short version:
> **the reviewer found a real inconsistency, but between the docs and the code, not
> between the belief and the simulator.** Belief and simulator agree with each other;
> the documentation was wrong. The doc claims are now corrected, the semantics are
> pinned by tests, and one genuine bug (common random numbers) was confirmed and
> fixed behind a flag.

---

## 1. The claim, and what the code does

The external review quoted `belief.gain()`:

```python
x = 0
for p, e in self.in_edges[i]:
    x |= err[p] & coin[e]
new[i] = x
```

and concluded that a review does not implement `do(X_v = 1)`, so belief's expected
gain, the posterior, and the greedy-vs-RL comparison might all be wrong.

**The observation is correct; the consequence is not.** Compare the simulator
(`experiments/spike_active_selection.py:99`):

```python
def review_step(a, base, err, nodes, topo, coins, rng):
    flagged = err[a] and rng.random() < CFG["p_catch"]
    if flagged:
        base[a] = False                     # clear a's own error
        err = compute_err(base, nodes, topo, coins)   # re-propagate
```

and `compute_err`: `err[i] = base[i]`, then propagate from parents. So a review
clears **the node's own source error** and re-propagates; an error inherited from a
still-wrong parent survives.

That is exactly what `belief.gain()` models (`new[i]` rebuilt from parents, base
discarded), and exactly what `observe()` does (`B[i, :] = False`). **The belief and
the simulator implement the same rule.** There is no belief-vs-environment mismatch.

What *was* wrong is the documentation: `do(X_v = 1)`, "force $X_v = 1$", "causal
intervention" — in eight places across EN/CN/KO. A do-operator would overwrite the
node's state; the code does not. Those sentences are now replaced with the actual
semantics.

## 2. Why this still matters

The implemented rule is defensible — fixing a value does not fix its cause — but it
changes what the method claims:

- A review only helps when the node is (or may be) the **source** of an error.
  `belief.gain()` already encodes this: it returns 0 when no particle has a base error
  at that node.
- The paper cannot say "a review is a causal intervention"; it must say "a review
  removes the node's own error and lets the graph re-propagate".
- Reviewing a node whose error is purely inherited is wasted budget. That is a real
  property of the setting, and it should be stated, not hidden.

## 3. Tests that pin it (run them)

```bash
python3 experiments/test_semantics.py     # 5/5 passed
```

| Test | What it locks |
|---|---|
| `test_fix_base_error` | a node with its own error and a clean parent becomes correct |
| `test_inherited_error_persists` | reviewing an inherited error flags it but does not fix it |
| `test_mixed_source_and_inherited` | base cleared, inherited part remains |
| `test_belief_gain_is_zero_without_base_error` | `gain()` agrees with the simulator |
| `test_crn_independent_of_order` | the CRN uniform stream is order-independent |

## 4. The one real bug: common random numbers

`review_step` used to draw `rng.random()` **inside** a short-circuiting `and`:

```python
flagged = err[a] and rng.random() < CFG["p_catch"]
```

Policies review different nodes in different orders, so they consume different numbers
of draws from the same seeded stream. The same seed therefore does **not** give the
same reviewer outcome for the same node across policies, and the paired comparison is
noisier than it claims.

Fix: one Uniform per node, drawn before any review.

```python
u = episode_uniforms(rng, len(nodes))   # one draw per node
flagged = err[a] and u[a] < CFG["p_catch"]
```

It is behind `CFG["crn"]`, default **False**, because turning it on changes every
number. To adopt it:

```python
CFG["crn"] = True     # in spike_active_selection.py
```

then re-run and replace every table. Do not mix CRN and non-CRN numbers in one table.

## 5. What the review got right, and what to do next

| Point | Verdict |
|---|---|
| belief does not implement `do(X_v = 1)` | **right** — docs, not code; fixed |
| belief greedy is model-based and has an advantage | **right** — that is why WP1 now has Arm B (misspecification) |
| CRN is not strict | **right** — implemented behind `CFG["crn"]` |
| GNN is thin (1 layer, terminal reward) | fair, but lower priority than misspecification |
| Reproduce before citing | right, and already the repo's stated discipline |

Priority order it implies, unchanged from `GENERALIZATION_PLAN.md`: (1) semantics
tests, (2) independent reproduction, (3) CRN rerun, (4) misspecification arm,
(5) fewer doc entry points.
