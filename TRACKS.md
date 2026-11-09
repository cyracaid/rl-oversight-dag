# Two stages: what we decide, and what belongs to SciForge

> Written 2026-11-09. Replaces the "tracks" framing with a staged one, because the
> question "who decides?" has different answers on each side of 12/05.
> Rule: **Stage 1 needs no external approval. Stage 2 is their system; we propose,
> they decide. Nothing in Stage 2 may block Stage 1.**

---

## 0. The two stages

| | **Stage 1 — STA3145 group project** | **Stage 2 — Evidence audit / SciForge** |
|---|---|---|
| When | now → 12/05 | after the course, or in parallel only as design work |
| Question | When does a learned review policy beat a model-based one on a dependency graph? | How should a real evidence chain record and prioritise human review? |
| Who decides | **us, the five of us** | **the system owners** (郑心, Zhangyang Gao), plus IRB for sleep data |
| Data | synthetic DAGs + **open** transfer sets (KAIST, GO); sleep queue only as aggregates | SciForge **audit chain** (review receipts); de-identified exports |
| Output | course paper + talk | design docs → offline evaluation → (later) Nature Communications |

**Nothing in Stage 1 waits for Stage 2.** The only external item Stage 1 touches is
the IRB question "may we report aggregate numbers from the sleep queue" — a data-use
question, not a design decision.

---

## 1. Stage 1 — the decisions are ours

These are the calls the five of us make, and nobody outside can block them:

| Decision | Owner | Why it is ours |
|---|---|---|
| What the paper claims (Option 1 vs Option 2) | P2 with P1 | it follows from G0, which we run |
| Scope: synthetic main experiment + one open transfer set | P1 | the course allows it; no partner needed |
| The method stack: REINFORCE / PPO / DQN / CMDP + belief arms | P2 | our compute, our seeds |
| The evaluation protocol: paired CI, ≥5 seeds, 10 pp resolution | P1 | a standard we impose on ourselves |
| Which open dataset to use first (SYNERGY or GO) | P5 | licence and load cost, not permission |
| Whether the sleep queue appears at all, and only as aggregates | P5 + P1 | IRB sets the boundary; the choice to include it is ours |
| What goes in the slides | P1 + P5 | — |

**What we do not need from anyone else:** approval of the direction, permission to
run synthetic experiments, sign-off on the method stack, or a partner's dataset to
finish the course deliverable.

---

## 2. Stage 2 — the evidence audit, and what is theirs

How *we* do it (our work, no permission needed):

1. **Design the receipt schema.** Field-level granularity, two timestamps, verdict,
   hash chain. Already written and demoed (`triage_bench/AUDIT_CHAIN_DESIGN.md`).
2. **Build the offline evaluator.** Receipts → cost model → recall per minute.
   Already running (`run_audit_demo.py`).
3. **Make the suggester read-only by construction.** No write, no receipt, no stamp.
4. **Ship the ask as a system question, not a request for a decision**
   (`triage_bench/SCIFORGE_ASK.md`).

What is theirs, and only theirs:

| Who | What they own | What we do about it |
|---|---|---|
| **郑心** (evidence-chain owner) | whether a suggester output may ever be recorded in the audit chain; the receipt fields; the granularity of their chain | propose a default, adapt to their answer, never assume it |
| **Zhangyang Gao** (SciForge) | whether any of this enters the product | keep Stage 2 a design + offline result until they want more |
| **Maia ten Brink** (sleep lab) | how the sleep data may be used and reported | aggregates only, IRB first |

The distinction that matters: **they decide what happens inside their system; they do
not decide what we claim in our course project.** A "no" from any of them closes a
Stage 2 option, never Stage 1.

---

## 3. Answers to the two questions raised in the group chat

### Q1. "If the sleep data can't be shared, do we have to build our own dataset?"

**No.** Three things were being conflated:

1. **The synthetic DAG is already the course dataset** — generated in code, anyone can run it.
2. **Open transfer sets exist** — KAIST sleep diary (1,372 rows / 49 adults, Figshare
   28509740, CC BY) and GO annotations (IEA vs experimental). No permission needed.
3. **The sleep queue stays aggregate-only** — a worked example, not the evaluation set.

Self-labelling our own outputs is self-grading and reviewers treat it as such.

### Q1b. "Are the 75 corrections AI errors, or participant data-entry mistakes?"

**Participant data-entry mistakes.** The pipeline is a **rule engine** (M1–M7) that
detects them and auto-corrects 84 rows. In the sleep data the "AI" is a detector, not
an author.

Consequence: **Stage 1 cannot claim to study "AI output review".** It studies **flag
triage on an automated detector's queue**. The genuine AI-output instance is Stage 2
(SciForge claims), which is why Stage 2 exists.

### Q2. "Keep improving RL, or present why it loses?"

**Neither, until one experiment decides it.** G0 now has two arms:

| Arm | Question | Outcome |
|---|---|---|
| **A** | does RL lose on state representation? | RL ≥ belief greedy → Option 1; otherwise Option 2 |
| **B** | does belief greedy depend on a *correct* model? | perturb λ and the calibration; if belief degrades and RL does not, RL has a niche |

Option 2 is not a failure state. For an RL course it is the stronger submission: five
RL variants, a model-based comparator, an information-equalized control, and a stated
mechanism that could be disproved.

---

## 4. Gates

| Phase | Window | Work | Gate |
|---|---|---|---|
| **S1-P0** | now → 11/16 | G0 Arm A + Arm B (5 seeds, paired held-out) | **G0 decided** |
| **S1-P1** | 11/17 → 11/23 | freeze env; one open transfer set | every table from one script |
| **S1-P2** | 11/24 → 12/03 | draft, figures, slides, rehearsals | talk delivered |
| **S2-B1** | parallel, no deadline | receipt schema + demo (done); 20-row sample from 郑心 | real receipts exist |
| **S2-B2** | after the course | offline evaluation on the real chain; cost in minutes | recall per hour reported |

---

## 5. One line each, for the chat

- **On data:** "We're not building our own labels — Stage 1 uses the synthetic graph
  plus an open transfer set; the sleep queue stays aggregate-only."
- **On the 75:** "They're participant data-entry mistakes; the pipeline is a rule
  engine, so it's flag triage, not AI-output review — that's Stage 2."
- **On RL:** "G0 decides it: same belief features for RL, plus a model-misspecification
  arm. If RL still loses, the reason is credit assignment, and that becomes the result."
