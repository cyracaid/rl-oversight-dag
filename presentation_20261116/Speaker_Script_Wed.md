# Team 6 — speaker script for the merged deck (Wed update)

Deck: `Team6_Proposal_with_feedback.pptx` — **14 slides**, rebuilt 2026-11-24.
Structure: 1–2 motivation, **3–5 new feedback slides (A1–A3)**, 6–10 main line, 11–13 backup, **14 A4 denominator caveat (backup only)**.

Target: **5:00** main talk (1–10), 15 s of transitions. A 6:00 variant is marked with `[+30s]`.
Slides 11–14 are not spoken unless asked.

Two rules for this talk:

1. Never say "ticketing system". The environments are 5 synthetic graph families plus the real sleep DAG (N=21).
2. Say the negative result before anyone asks: greedy wins, and that is the finding, not a failure to hide.

---

## Slide 1 — title (15 s)

We study where a limited human review budget should go, when pipeline outputs depend on each other.
One wrong upstream value can corrupt several conclusions, so "check the most suspicious row" is not automatically the right move.
The question is narrow: **does a learned review order beat a strong one-step rule, and when?**

## Slide 2 — motivation (25 s)

A research pipeline parses inputs, derives metrics, and writes conclusions. Errors travel along that chain.
In the real sleep extract, humans corrected 75 values out of 13,990 daily records — 0.54 % — and 76 % of those corrections were time-order errors.
So the interesting quantity is not how many rows we read, but **which link we read first**.

## Slide 3 — A1: what counts as an error (30 s)

An error here is **a wrong output value, not a code bug**. Code bugs are caught by tests; a reviewer never sees them.

Concretely: a wake-up timestamp earlier than sleep onset, AM/PM flipped, a gap over 24 hours. That family is 57 of 75 corrections. The rest are derived-gap, metric-spike, and zero-length-sleep errors.

One honesty note built into this slide: 0.54 %, 6.5 %, and 76 % have three different denominators. And the per-node base rates — 0.35 for order errors, 0.05 to 0.15 for the rest — are a **model prior mapped from those shares, not a per-node measurement**.

## Slide 4 — A2: nodes and terms (30 s)

Every output of every stage is a node: 21 in total across collect, preprocess, analyze, conclude.
Eight leaves are raw fields, five are derived gaps, four are metrics, and four are conclusions.

Three terms the teacher asked about:
- **hidden error** — whether this node's own value is wrong. The policy cannot see it; it sees type, confidence, sink reach, reviewed, and the belief.
- **stage node** — any node in the four layers. The conclusion layer is the sink layer, and our reward counts only those four sinks.
- **state** — per node those features plus remaining budget, with horizon equal to budget.

Conclusion nodes can be wrong themselves. A review clears that node's own error and recomputes everything downstream — that is why one check can protect several conclusions.

## Slide 5 — A3: three requirements, one MDP (35 s)

This is the mapping the teacher asked for. The three literatures are not sitting side by side; they are three components of the same loop.

- **Deferral** gives the action and the terminal reward: review one unreviewed node, inspection may miss with probability 0.1, reward is minus residual sink errors.
- **Budgeted allocation** gives the horizon: budget lives in the state, the episode ends when it is spent.
- **Error cascade** gives the graph and the transitions: a DAG with parents and sinks, a belief over hidden errors, and repair that recomputes downstream.

Remove any one and the ranking is undefined: deferral without the graph cannot tell that fixing one row saves several conclusions; allocation without a belief cannot rank by probability times impact; cascade without a budget never says which link to inspect.

## Slide 6 — MDP (30 s)

Formally: partially observable, particle belief over hidden errors. State is graph plus confidence, review history plus belief, and remaining budget. Action picks an unreviewed node. The outcome repairs or not, and updates the belief. Sixteen decisions per episode, terminal reward is minus the sink-error count, gamma equals one.

## Slide 7 — baseline (25 s)

The baseline is belief greedy: update the posterior, estimate immediate benefit, take the largest one. Learned policies share a GNN encoder and differ in input set and learning target: REINFORCE, Monte Carlo critic, three-step, five-step. Same budget, same graphs.

## Slide 8 — result (45 s)

The completed run trained 120 policies, 2.4 million episodes. In the primary condition, belief greedy leaves **1.020** sink errors. The best learned mean is **1.255** — about 23 % worse. Zero of eight learned candidates beat greedy, and every multiplicity-adjusted interval is above zero.

State it plainly: **this is a negative result for the current implementation**, not evidence that RL can never help. The MDP has sequential structure; that does not by itself buy an RL advantage.

## Slide 9 — next (30 s)

One exploratory signal: under noisy confidence, observed three-step shows 3.477 errors against 3.965 for greedy. But noise changes both confidence and the derived belief, and the particle filter sometimes degenerates. So the next step is diagnosis — action traces, belief failures, information parity — before another large training run. This is a proposed follow-up, not a robustness claim.

## Slide 10 — deliverable (20 s)

The contribution is a reproducible boundary: diagnose, specify one hypothesis, validate on held-out graphs and seeds. **Success is a reliable boundary even if greedy remains best.** Thank you.

`[+30s]` If time allows, add: "Our replication receipts are in the repo; the strong rule itself reaches 0.66 against 1.03 for confidence ordering in a separate environment — different budget, so it is not comparable to 1.020."

---

## Backup slides

**Slide 11 — every primary candidate.** Differences are learned minus greedy; all eight adjusted intervals above zero. Five training seeds limit precision.

**Slide 12 — anticipated questions.** Short answers below.

**Slide 13 — references.** Sutton & Barto chapters 7, 9, 13; Williams 1992; Kipf & Welling 2017; frozen analysis protocol and hashes.

**Slide 14 — A4 denominators.** Three rates, three denominators. Also: on the real graph N=21 only heuristics were run — no review 2.12, random 1.88, confidence 0.50 — so that is the bar any learned policy must clear. Belief greedy was not run at that size.

---

## Q&A — four answers, memorised

**"If greedy wins, why use RL at all?"**
Because the question is when learning is worth its complexity. We now have a clean negative under matched information, and one unresolved noise clue. Reporting that boundary is the deliverable.

**"Does the noisy-confidence result prove robustness?"**
No. It is exploratory, the signal and the belief move together, and posterior degeneracy is unresolved. We will not present it as a gain.

**"Is this validated on real workflows?"**
No. Policy performance is from synthetic graphs plus the real sleep DAG structure. No deployment, no independent confirmation, no clean-clone reproduction yet.

**"What about more compute / more episodes?"**
We already ran the 10× arm: 1,000 to 10,000 episodes. Validation error stopped at 0.94, 0.96, 0.98 against a rule at 0.885, and the gap only narrowed from +0.377 to +0.262. More compute is not the missing piece.

---

## 中文速记（讲前 30 秒扫一眼）

- 顺序：问题 → 真实错误 → 新三页（错误定义 / 节点术语 / 三要素映射）→ MDP → 基准 → 负结果 → 下一步。
- 第 3 页必须说："0.54 / 6.5 / 76 三个分母，不能混"；base rate 是先验不是实测。
- 第 5 页必须说："三个少一个，排序就定义不出来"。
- 第 8 页必须说："0/8，全区间 > 0，这是负结果"。
- 不要说票务；不要说"RL 更好"；不要把 0.66 和 1.020 放同一句比较。
- 超时先砍第 6 页细节和第 9 页诊断清单，别砍第 8 页。
