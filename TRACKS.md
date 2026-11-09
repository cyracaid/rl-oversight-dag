# Two tracks, one codebase: separating the RL course work from SciForge

> Written 2026-11-09 to answer the two questions raised in the group chat.
> Rule: **Track A must be finishable without any external partner. Track B may
> depend on SciForge. Nothing in B may block A's 12/05 deadline.**

---

## 1. The split

| | **Track A — STA3145 (RL course)** | **Track B — SciForge / AI4Science** |
|---|---|---|
| Question | When does a learned review policy beat a model-based one on a dependency graph? | How should a real evidence chain record and prioritise human review? |
| Data | Synthetic DAGs (80 / 500), **open** transfer sets (KAIST, GO) | SciForge evidence queue + review receipts; sleep queue as the worked example |
| Method | REINFORCE / PPO / DQN / CMDP, GNN scorer, belief-conditioned RL; belief greedy as the model-based baseline | Receipt schema, audit-chain granularity, review-cost model |
| Claim | Either "belief-conditioned PG wins" or "PG loses for a stated, testable reason" | "Review scheduling is information-bound; here is the ceiling and the cost" |
| Deliverable | Course paper + talk, 12/05 | Design docs → offline evaluation → (later) Nature Communications |
| External dependency | **None** | 郑心's audit chain; IRB for sleep data |
| Risk | RL may not win → answer is the analysis | Partner may not deliver receipts in time → ship the design + demo |

**Shared, and owned by A:** the synthetic environments, the ceiling analysis, the
evaluation protocol. B reuses them; B does not fork them.

---

## 2. Answering the two questions directly

### Q1. "If the sleep data can't be shared, do we have to build our own dataset?"

**No.** Three separate things were being conflated:

1. **The synthetic DAG is already the course dataset** — generated in code, anyone
   can run it, and it carries the mechanism (propagation, budget, sparse reward).
2. **Open transfer sets exist** — KAIST sleep diary (1,372 rows / 49 adults,
   Figshare 28509740, CC BY) and GO annotations (IEA vs experimental) are public.
   These are the generalization tests; they need no permission.
3. **The sleep queue stays aggregate-only.** It is a worked example for Track B,
   not the course's evaluation set. Nothing in A depends on sharing it.

So the answer to "should we go through outputs and label our own errors?" is **no**
— self-labelled data is self-graded, and reviewers treat it as such.

### Q1b. "Are the 75 corrections AI errors, or participant data-entry mistakes?"

**Participant data-entry mistakes.** The pipeline is a **rule engine** (M1–M7) that
detects them and auto-corrects some (84 rows). So in the sleep data the "AI" is a
detector, not an author.

Consequence: **Track A cannot claim to study "AI output review".** It studies
**flag triage on an automated detector's queue**. The genuine AI-output instance is
Track B (SciForge claims), which is why B exists.

### Q2. "Where does RL fit — keep improving it, or present why it loses?"

**Neither, until one experiment decides it.** Equalize the information: feed the
belief posterior (marginal, entropy, reviewed mask) into the RL state. Then:

| Outcome | Reading | What we write |
|---|---|---|
| RL matches or beats belief greedy | the loss was a state-representation problem | **Option 1**: RL is the method; belief greedy is the baseline it beats |
| RL still loses | the loss is credit assignment under sparse terminal reward | **Option 2**: the analysis *is* the result; the experiment is the evidence |

Option 2 is not a failure state. For an RL course it is the stronger submission:
five RL variants, a model-based comparator, an information-equalized control, and
a stated mechanism that could be disproved.

---

## 3. Phase gates

| Phase | Window | Work | Gate |
|---|---|---|---|
| **P0** | now → 11/12 | Belief-conditioned RL run (5 seeds, paired held-out) | **G0**: does RL match greedy? decides Option 1 vs 2 |
| **P1** | 11/12 → 11/19 | Course paper skeleton; freeze synthetic env and numbers | G1: every table reproducible from one script |
| **P2** | 11/19 → 11/26 | One open transfer set (KAIST or GO), same protocol | G2: does the ordering repeat (type ≫ within-type)? |
| **P3** | 11/26 → 12/03 | Slides, ≥2 rehearsals, final tables | G3: talk delivered |
| **B1** | parallel, no deadline | Receipt schema + demo (done); 20-row sample from 郑心 | B-gate: real receipts exist |
| **B2** | after the course | Offline evaluation on the real chain; cost in minutes | B-gate: recall per hour reported |

**A never waits on B.** If B stalls, A still ships; B's design docs already exist.

---

## 4. One line each, for the chat

- **On data:** "We're not building our own labels — the course uses the synthetic
  graph plus an open transfer set; the sleep queue stays aggregate-only."
- **On the 75:** "They're participant data-entry mistakes; the pipeline is a rule
  engine, so it's flag triage, not AI-output review — that's the SciForge track."
- **On RL:** "One experiment decides it: give RL the same belief features. If it
  still loses, the reason is credit assignment, and that becomes the result."
