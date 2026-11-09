# Two tracks, one codebase: separating the RL course work from SciForge

> Written 2026-11-09 to answer the two questions raised in the group chat.
> Rule: **Track A must be finishable without any external partner. Track B may
> depend on SciForge. Nothing in B may block A's 11/23 talk.**

---

## 1. The split

| | **Track A — STA3145 (RL course)** | **Track B — SciForge / AI4Science** |
|---|---|---|
| Question | When does a learned review policy beat a model-based one on a dependency graph? | How should a real evidence chain record and prioritise human review? |
| Data | Synthetic DAGs (80 / 500), **open** transfer sets (KAIST, GO) | SciForge **audit chain** (review receipts); sleep queue as the worked example |
| Method | REINFORCE / PPO / DQN / CMDP, GNN scorer, belief-conditioned RL; belief greedy as the model-based baseline | Receipt schema, audit-chain granularity, review-cost model |
| Claim | Either "belief-conditioned PG wins" or "PG loses for a stated, testable reason" | "Review scheduling is information-bound; here is the ceiling and the cost" |
| Deliverable | Course paper + talk, 11/23 | Design docs → offline evaluation → (later) Nature Communications |
| External dependency | **None** | 郑心's audit chain; IRB for sleep data |
| Risk | RL may not win → answer is the analysis | Partner may not deliver receipts in time → ship the design + demo |

**Shared, and owned by A:** the synthetic environments, the ceiling analysis, the
evaluation protocol. B reuses them; B does not fork them.

**Status note on the DAG (2026-11-09).** SciForge's code still ships
`packages/domains/evidence-dag`, but the product surface was de-emphasised: a
September commit removed the DAG design docs and demos, and the chain owner says the
DAG is "not necessary". **Track B therefore depends on the audit chain, not the
graph.** Nothing in A depends on either.

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
| RL matches or beats greedy **after the `gain(i)` gate** | the loss was representational — note the belief posterior is *already* in the state (1.56 vs 1.56, −0.00 ± 0.08), so the missing quantity is the one-step value, not the belief | **Option 1**: RL is the method; belief greedy is the baseline it beats |
| RL still loses | the loss is credit assignment under sparse terminal reward, or the model-correct regime | **Option 2**: the analysis *is* the result; the experiment is the evidence |

Option 2 is not a failure state. For an RL course it is the stronger submission:
five RL variants, a model-based comparator, an information-equalized control, and
a stated mechanism that could be disproved.

---

## 3. Phase gates

| Phase | Window | Work | Gate |
|---|---|---|---|
| **P0** | Mon 11/09 → Wed 11/11 | `gain(i)`-feature and n-step/AC gates, **run in parallel on 11/10**; decision 11/11 | **G0**: does RL match greedy? decides Option 1 vs 2 |
| **P1** | Thu 11/12 → Sat 11/14 | Branch work + 2-step greedy control; numbers frozen | G1: every table reproducible from one script |
| **P2** | Sun 11/15 → Mon 11/16 | Draft, slides, ≥2 rehearsals | G2: talk ready |
| **P3** | Mon 11/23 | Final talk (11/17–11/22 polish only) | G3: delivered |
| **optional** | only if the week finishes early | One open transfer set (KAIST or GO), same protocol | does the ordering repeat (type ≫ within-type)? |
| **B1** | parallel, no deadline | Receipt schema + demo (done); 20-row sample from 郑心 | B-gate: real receipts exist |
| **B2** | after the course | Offline evaluation on the real chain; cost in minutes | B-gate: recall per hour reported |

**A never waits on B.** If B stalls, A still ships; B's design docs already exist.

---

## 4. One line each, for the chat

- **On data:** "We're not building our own labels — the course uses the synthetic
  graph plus an open transfer set; the sleep queue stays aggregate-only."
- **On the 75:** "They're participant data-entry mistakes; the pipeline is a rule
  engine, so it's flag triage, not AI-output review — that's the SciForge track."
- **On RL:** "The belief features are already in the state and it changed nothing
  (1.56 vs 1.56). The open gate is the one-step value `gain(i)` the greedy
  argmaxes, plus credit assignment. If it still loses, that becomes the result."
