# Why the confidence channel cannot carry the guarantee

Status: **argument + one measured instance**. Written 2026-11-25. Companion to `BENCHMARK_SPEC.md` §9
and `CLAIM_GRAPH_CONTRACT.md`.

This file answers one question: the rule ranks vertices with a belief, and the delivery reports what it
covered. Can the belief also decide **whether the delivery's statement is true**? Answer: no, and the
reason is algebraic, not a matter of tuning or more data.

| Claim | Status |
|---|---|
| Entropy is invariant under relabelling, so it cannot separate "right answer on top" from "wrong answer on top" | proven, three lines |
| Any rule that assigns status from entropy alone has an error floor equal to the mass of same-entropy/different-truth pairs | proven, corollary |
| The measured `false_inspected` bucket is an estimate of that mass | measured, `supervisor-v1` |
| Raising coverage does not lower that floor | follows from the floor's definition |
| Entropy minimisation at test time must drift | argued here; the experiment is **not run** (see §7) |
| Entropy is useless | **not claimed** — it is a difficulty signal, see §6 |

---

## 1. The three facts

**(i) Permutation invariance.** For any relabelling σ of the answer set,

```
H(p) = H(σp)
```

Both sides sum the same terms. Take `p = (0.9, 0.1)` and `p = (0.1, 0.9)`: both are 0.469 bits, and they
assert opposite things. Entropy is blind to *which* label holds the mass. This is not a defect of an
estimator; it is the definition of a sum over labels.

**(ii) Scalar collapse.** `H` maps the `K−1`-simplex onto one real number. Same `H`, arbitrary content.
So `H` can order *prediction difficulty* for a fixed model, and cannot order *support* once the model may
be wrong. The two orderings agree only when the model is already correct — and that is the thing the
ordering was supposed to establish, so the argument is circular.

**(iii) The KL reference is the uniform distribution, not the truth.**

```
H(p) = log K − KL(p ‖ u)
```

"Low entropy" means *far from uniform*, i.e. confident. No term in this identity refers to the correct
answer. Every confidence measure in this family is a distance from `u`, never a distance from `y*`.

Consequence used everywhere below: **confidence information and guarantee information are different
objects.** The first is a functional of the model's own output; the second is a relation between that
output and the world.

## 2. Lemma: the error floor

Let `F` be any status rule that sees only `H(p)` (or any strictly monotone function of it).

Because `H(p) = H(σp)`, `F` assigns the same status to both. Pick a pair `(x₁, x₂)` with
`p(·|x₁) = σ p(·|x₂)` where `y*(x₁)` makes the claim true and `y*(x₂)` makes it false. `F` is wrong on at
least one member of every such pair. Hence

```
error(F) ≥ mass{ pairs x₁, x₂ : H equal, truth opposite }   (up to one per pair)
```

Two properties matter:

- the floor is a property of the **reference**, not of the sample size, the model, or the calibration
  method;
- **coverage does not enter the floor.** Reviewing more vertices adds more pairs of the same kind.

The floor can be measured without resolving individual pairs: it is the rate at which a confident verdict
is nonetheless false. That is exactly what `supervisor-v1` reports as `false_inspected`.

## 3. The measured instance

From `role3 improvement/outputs/supervisor-v1/receipt_vs_silent.md`, `modular`, budgeted, N=500:

| policy | declared share | false-inspected | of surviving errors |
|---|---|---|---|
| `marginal` (the rule) | 0.898 | 180 / 1767 | **10.2 %** |
| `oracle` (true coverage) | 0.851 | — | **14.9 %** |

Same episode, same budget. Better coverage makes the false bucket **larger**: 10.2 % → 14.9 %. That is
not a bug and not a threshold that moved. Every source upstream of those sinks was reviewed, and the
catch still missed, because `p_catch = 0.9`, so `inspected ≠ clean`.

Read through §2: the 10.2 % is the **discrete analogue** of that mass on this family — the rate at which a
*reviewed* verdict is nonetheless false, which is what a status rule reads as "entropy low". It is the
floor priced in the only unit the receipt has. It is not an entropy measurement, and a reviewer should not
read it as one: it measures the consequence, not the statistic.

The `spike` and `real` families declare 0.974 and 0.978 respectively and do pass the 0.90 bar, so the
floor is family-dependent. It is smallest where the catch is most reliable, which is the correct
behaviour: the floor is a function of the reference's quality, not of the router's.

## 4. Bit budget: why "review more" cannot repair this

If the per-vertex belief is `K`-valued, one vertex supplies at most `log₂K` bits (three statuses: 1.585
bits). A claim is a conjunction over its ancestor **sources**, not over a vertex cut: with `m` sources the
statement needs `m` judgements.

The bits scale with `m`; the **missing reference does not**. `m` bits that are each invariant to
relabelling are still invariant to relabelling when added together. Capacity was never the bottleneck.

This is the formal version of the sentence in the receipt:

> Coverage and correctness pull apart exactly as `p_catch = 0.9` predicts, and a delivery that reports
> only coverage would overstate itself **more**, not less, when it reviews more.

## 5. Which quantities can be referenced

| quantity | reference | can ground a guarantee | why |
|---|---|---|---|
| `H(p)` | uniform `u` | no | §1(i), §1(ii): no `y*` in the term |
| `KL(p ‖ q_prior)` | a prior | no | reference is still not the world |
| PRPD | `p` vs `p∘T` under a nuisance rearrangement | **necessary condition only** | the reference lies outside the model |
| reviewer outcome | a second party's verdict | partially — bounded by `p_catch` | reference is external, but imperfect; §3 is that bound |
| human adjudication receipt | a signed, versioned decision | yes | reference is external and separated (§8) |

PRPD is the only model-side quantity whose reference is external, because invariance under `T` is a
property the world can falsify. It is a necessary condition: a supported claim should survive a nuisance
rearrangement. It is not sufficient, and its blind spot is known — rearrange-invariance tests sensitivity
to **structure**, while attribution evidence puts a large share of confident errors on **background**
features, which a structural rearrangement does not move. So PRPD can pass exactly the failures it was
meant to catch.

## 6. What is *not* claimed

Entropy is not useless. It is an excellent **routing** signal: it is cheap, label-free, and monotone in
difficulty for a fixed and correct model. Everything in §1–§4 says only that it cannot be the **ground**
of a guarantee, because a ground has to refer to the world.

Equivalently: `H` may decide *what to look at*. It may not decide *what the delivery is allowed to
assert*.

## 7. Test-time adaptation: drift is forced, not incidental

Entropy minimisation at test time pushes `p` toward a vertex of the simplex — that is, it maximises
distance from `u`. By §1(i) the gradient of `H` contains no `y*`. **Which vertex it drives toward is
chosen by the model being audited.**

So the standard failure mode of test-time adaptation — error accumulation under pseudo-label feedback —
is not a nuisance to be mitigated here; it is the predicted consequence of letting a permutation-invariant
quantity steer. In this repository's terms:

> an auditor whose criterion is invariant to relabelling, and whose output feeds back into the object it
> audits, has no way to detect that it has converged on the wrong vertex.

**Not claimed:** no closed-loop experiment has been run. The pre-registerable prediction, if one is run, is
that `false_inspection` under feedback grows monotonically with graph depth and is at least 1.5× the
open-loop value at depth 3 — anchored on the measured single-step drift 10.2 % → 14.9 %. Any such run must
use a fresh block (≥ 5600) and be labelled a subgraph task.

## 8. Consequence for the receipt: separation

The delivered layer is designed so that the receipt is post-hoc and changes no action; measured, the
action is identical on 800 of 800 episodes (`supervisor-v1`, P1).

§1–§7 supply the reason that design is required rather than merely convenient:

**The objectivity of a guarantee depends on separating the auditor from the audited object.**

A machine may route on procedural signals, including entropy and disagreement. It may not update its own
guarantee status from those signals, because the signals are invariant to the very thing the status is
about. Status, perspective set, independence threshold (`p_catch`), and construct mapping (`inspected` vs
`clean`) are therefore outside the machine's authority and require a versioned human adjudication receipt.
The audit policy is frozen for the duration of the evaluation.

Under this reading P1 is not a limitation to be relaxed later. It is the compliance evidence.

## 9. Where this leaves Gap D

`BENCHMARK_SPEC.md` §9.4 previously read: "confidence is synthetic; no measured calibration exists." That
framing implies the gap closes when real calibration data arrives. §1–§3 say it cannot close that way.

The gap is a **signal-class** result, not a data gap:

- the inversion is between subgroups, and calibration is a marginal operation, so no calibration map
  repairs it;
- the floor in §2 is set by the reference, and a better-estimated `H` has the same reference.

So the honest statement is: *the confidence channel is routing-only by construction; the architecture's
refusal to let it drive status is correct, and the 10.2 % / 14.9 % pair is the measured price of
pretending otherwise.*

This makes the limitation stronger, not weaker: it is a reason the layer is shaped this way, rather than
an apology for a missing dataset.

---

## Reproduction of the quoted numbers

```bash
cd "role3 improvement"
python3 run_supervisor_check.py    # block 5400-5599, writes outputs/supervisor-v1/
```

The per-family table at the top of `outputs/supervisor-v1/receipt_vs_silent.md`; P1 in its Predictions
section and P5 in the falsification note. Bit arithmetic in §1(i) and §4 is exact, not measured.
