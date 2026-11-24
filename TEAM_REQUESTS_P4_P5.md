# Requests to Person 4 and Person 5 — what is actually missing

Written 2026-11-24 after auditing everything on `main`. Read this before starting: **parts of your assignment
are already done, and doing them again wastes the week.** What is missing is listed with an acceptance test,
so "done" is not a matter of opinion.

Deadline: **Wednesday's review.** Nothing below needs real data, an install, or a GPU.

---

## Status of the assignment as written

| Assignment item | Owner | Status on `main` |
|---|---|---|
| Five baselines (no-review, random, confidence, hub, structural) | P4 | **done, frozen** — `role3 improvement/outputs/v3/benchmark_summary.csv`, 5 graph shapes, paired CIs |
| Sixth baseline: marginal / belief-style value rule | P4 | **done** — same CSV |
| *flatten* control (remove the graph, treat nodes as independent) | P4 | **missing on v3** — exists only at the old N=80 setting in `experiments/` |
| *shuffle* control (rewire edges at random) | P4 | **missing everywhere.** `role2_규리/shuffle_control.py` is *not* this: it permutes confidence scores inside a node type. Do not count it. |
| worst-of-n next to the mean | P4 | **missing** |
| 27/48 consensus split | P4 | **blocked** — labels are P5's, still absent |
| Motivation numbers 75 / 13,990 / 76 % | P5 | numbers are settled with caveats; the slide exists |
| Tri-lingual sync in one commit | P5 | **manual and drifting** — no check exists |
| Glue scripts (timeline, table regeneration, figures) | P5 | **missing.** `tools/build_docs.py` renders pages; nothing regenerates a results table or checks a link |
| One-page SciForge ask with receipt fields | P5 | **missing.** `experiments/SCIFORGE_INTEGRATION_CONTRACT_MAP.md` is a source inspection, not an ask |

---

## Person 4 — the two structural controls and worst-of-n

### Why these two

The paper's claim is that the *graph* is doing the work. Right now nothing rules out the alternative that any
ordering over 80 nodes with a good prior would do as well. Flatten and rewire are the two cheapest ways to kill
that alternative — and they can also kill our result, which is why they belong in the abstract, not an appendix.

### What to build

New folder `role4_controls/`, three files:

1. `run_controls.py`
   - reuse `role3 improvement/dag_role3` as the environment (do not copy it, do not change it)
   - test seeds **90000–90099**, the same graphs as the frozen benchmark, so the two tables can sit side by side
   - policies: `confidence`, `structural`, `marginal` — only what the claim needs. Do not re-run the other three.
   - three episode conditions, each paired on the same graphs:
     - `intact` — as shipped
     - `flatten` — sample the episode, then replace `edge_coins` with an all-`False` dict of the same keys.
       Root errors, confidences and reviewer randomness stay identical. `propagate` already handles this.
     - `rewire` — permute the edge set: keep the number of edges per node and the node types, replace parents
       with a fixed-seed random draw from the previous layer (Spike) or from all other nodes (modular/BA/ER).
       Freeze the rule and the seed before looking at outcomes.
   - output `results/controls.csv` (one row per graph × policy × condition) and `results/controls_summary.csv`
     (mean, paired 95 % CI vs `confidence`, wins/ties/losses)

2. `results/controls.md` — the table plus **one line per control: what it rules out.**
   Example shape: "flatten removes the `marginal` advantage (+0.00 [−0.05, +0.05]), so the gain comes from
   propagation, not from the error prior."

3. `README.md` — how to run it, which seeds, what is frozen.

### Acceptance

- `python3 run_controls.py --out results/` runs end to end on a fresh clone with `numpy` only.
- Every cell in `controls.md` traces to `controls_summary.csv`, and every CI is paired on the same graphs.
- The `intact` row reproduces the frozen benchmark for the three policies it shares (same seeds ⇒ same means;
  if it does not, stop and report the discrepancy instead of adjusting anything).
- `controls.md` states, in one sentence each, what flatten and rewire rule out — including the case where our
  advantage survives rewire, which would be a real problem and must be written down as such.

### worst-of-n (same PR, small)

For every policy already in `benchmark_summary.csv`, add the fraction of graphs where the policy leaves **at
least one** sink error. `benchmark_role3.csv` already has the per-graph numbers; this is a groupby, not a rerun.
Append a `worst_of_n` column set to the summary CSV with a short note, or produce `benchmark_worst_of_n.csv`
next to it — do not overwrite the frozen file.

### Do not

- Do not retrain, do not touch `dag_role3/`, do not re-derive the baselines.
- Do not present rewire as a pass if the advantage merely shrinks; report the interval.
- Do not use the 27/48 split until P5 lands the labels. Say "blocked" rather than inventing a split.

---

## Person 5 — glue, one ask, and drift control

### Why

Three numbers on a slide, three languages, and a partner on someone else's schedule. All three fail silently:
a stale number looks exactly like a current one. The only defence is a script that fails loudly.

### What to build

1. `tools/check_links.py` (blocking, exit 1 on failure)
   - every relative markdown link in the tracked `*.md` resolves
   - every `https://cyracaid.github.io/rl-oversight-dag/...` target has a matching source file
   - allow an explicit ignore list with a reason string next to each entry

2. `tools/check_numbers.py` (blocking, exit 1 on failure)
   - a single table `tools/number_claims.tsv`: `claim_id`, `value`, `source_file`, `source_row_match`, `doc`
   - the script re-reads each source CSV/JSON and asserts the claimed value is still there
   - start with ten claims only: the six in `README.md` → "Headline results", plus 75/13,990/76 %
   - when a number moves, the check fails and names the doc that needs editing. That is the whole point.

3. `tools/regen_tables.py`
   - one entry point: `python3 tools/regen_tables.py --check` (no writes, exit 1 if stale) and without `--check`
     to rewrite the derived tables that are ours (`experiments/real_pipeline_table.md`,
     `role3 improvement/outputs/v3/benchmark_summary.csv`) from their sources
   - do not regenerate role2's tables: they are frozen measurement outputs

4. `SCIFORGE_ASK.md` — one page, no more
   - what we want: read-only, de-identified evidence-graph export; schema exactly as listed in
     `EVIDENCE_CHAIN_DESIGN.md` §9
   - what we return: a per-review receipt with `reviewed_at`, `verdict`, `duration`, `suggested_by`
   - what we will **not** ask for: write access, deployment date, their model weights
   - a one-line log of the reply and its date, updated in place
   - Korean and English in the same file, since the recipient reads one and the team reads the other

5. Tri-lingual sync: run `check_links.py` and `check_numbers.py` before **every** push that touches a number.
   Add the two commands to `README.md` under "How to reproduce". That is the sync mechanism — not memory.

### Acceptance

- Both checks fail on a deliberately broken input (show the failure in the PR description) and pass on `main`.
- `check_numbers.py` covers the ten claims and none of them is a hand-typed duplicate of its source.
- `SCIFORGE_ASK.md` exists, is one page, and has a reply log line (even if the line says "no reply yet").
- No real data, no participant identifiers, nothing from `*.rds` anywhere in the diff.

### Do not

- Do not put numbers in `number_claims.tsv` that you cannot point at a row in a committed CSV.
- Do not regenerate role2 or role3 frozen outputs to make a check pass. If they disagree, the check is right
  and the doc is wrong.
- Do not promise the partner a date.

---

## How both plug into the canonical line

`CROSS_IMPLEMENTATION_VALIDATION.md` says a number without a CSV is not evidence. P4 supplies the missing
control CSVs; P5 supplies the machine that keeps every quoted number attached to one. Neither touches the
frozen environment, so nothing here can invalidate the results already reported.

## 한국어 요약

- **4번(기준선·통제):** 다섯 기준선은 이미 동결되어 있으니 다시 돌리지 말 것. 남은 것은 (1) v3 환경에서의
  `flatten`·`rewire` 통제, (2) worst-of-n, (3) 27/48 분할(라벨 대기). `role2_규리/shuffle_control.py`는 유형 내
  신뢰도 순열이지 간선 재배선이 아니다.
- **5번(글루·요청서):** 링크 검사, 수치 대조(`number_claims.tsv`), 표 재생성, SciForge 요청 1장. 세 언어
  동기화는 기억이 아니라 스크립트로 강제한다.
- 두 사람 모두 `dag_role3/`와 동결 산출물은 건드리지 않는다. 실제 데이터는 쓰지 않는다. 마감은 수요일.
