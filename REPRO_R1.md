# REPRO_R1 — second-person reproduction receipt

R1 asks for a decisive result, five seeds, and **a second person**. This file is the slot for that
second person. Fill in the receipt at the bottom and commit it; a chat log is not a receipt.

## What an assistant run does and does not prove

Someone who wrote the code can clone it and re-run it, but that is still the same author on the same
machine. It proves the artifacts are not hand-edited. It does **not** satisfy R1, which needs a reader
who did not write the code and will say "I could not make this run" if that is what happened.

A prior assistant-run clean room (2026-11-26, fresh clone, fresh venv) reproduced everything below
byte-for-byte. Treat that as a smoke test that the instructions work, not as the gate passing.

## Environment floor

- **Python ≥ 3.10.** On 3.9 the suite does not even collect: `dag_role3/policies.py:46` uses
  `random.Random | None`, which is a `TypeError` before 3.10. Nine test modules fail this way.
- **`torch` is required for the full suite.** Without it, `tests/test_contrastive.py`,
  `tests/test_models.py` and `tests/test_v3.py` fail at collection — they do not skip.
- Versions used in the recorded clean room: Python 3.14.0, numpy 2.5.5, scipy 1.18.1, networkx 3.7,
  scikit-learn 1.9.1, pytest 9.2.0, torch 2.15.0. Other versions in range are presumably fine; say
  which ones you used.
- **Run the role3 suite from inside `role3 improvement/`, not from the repo root.** Several tests import
  loose top-level modules (`belief_decomposition`, `report_value`, `make_demo`), which only resolve when
  that directory is the working directory. From the root the suite stops at collection with ten
  `ImportError`s. That is a property of the layout, not a broken clone — `cd` and retry before reporting
  a failure.

## Step 0 — clone and confirm you are on the same tree

```bash
git clone git@github.com:cyracaid/rl-oversight-dag.git r1-check
cd r1-check
git checkout 9379db7
git status --porcelain | wc -l      # must print 0
python3 --version                   # must be >= 3.10
```

Do not run anything on a dirty tree. If `git status` is not empty, stop and report.

## Step 1 — suite (2 minutes with torch installed)

`.github/workflows/tests.yml` runs exactly this on every push; the commands below are the local equivalent,
so a red check and a failed local run mean the same thing. As a reference point, run #1 on `59852c4` is green
([run 45778539596](https://github.com/cyracaid/rl-oversight-dag/actions/runs/45778539596), 71 s): if you get a
different result locally, the difference is your environment, and that is worth reporting.

```bash
python3 -m venv /tmp/r1-venv && . /tmp/r1-venv/bin/activate
pip install numpy scipy networkx scikit-learn pytest torch
cd "role3 improvement"
python3 -m pytest -q
```

Expected: `160 passed, 27 subtests passed`. Then, separately:

```bash
cd ../role2_규리 && python3 -m pytest -q     # 4 passed, 6 subtests passed
```

## Step 2 — one full recompute (the decisive one, ~3 s)

This is the only chain below that rebuilds episodes from scratch rather than re-rendering a frozen CSV.

```bash
cd "role3 improvement"
python3 run_ordered_gate_v21.py --out /tmp/out-v21
shasum -a 256 /tmp/out-v21/gate.json
```

Expected readout: `R = 0.821 [0.630, 0.964]  gap 0.467  kept 15/60  H1 holds  H2 holds`

| Artifact | Expected sha256 |
|---|---|
| `gate.json` | `5822ee7b6222fc01a2f2538283c5acaa8c981a856553f40018c7c4da484c696a` |
| `gate.md` | `188d23f12946ed49be7cb7bb18b94cc2bab04a5291131eea81565c8be14030db` |

## Step 3 — renders from frozen artifacts (deterministic, not recomputation)

Three of these read a committed CSV and write markdown. Identical bytes here prove the renderer is
deterministic. They do **not** prove the numbers underneath are reproducible — Step 2 does that.

```bash
cd "role3 improvement"
python3 exact_dp.py --report --out outputs/dp-ceiling-fresh
python3 report_p_catch.py --dir outputs/p-catch-v1
python3 analyse_information_budget.py
shasum -a 256 outputs/dp-ceiling-fresh/report.md \
              outputs/p-catch-v1/report.md \
              outputs/information-v1/information.json
```

| Artifact | Expected sha256 |
|---|---|
| `outputs/dp-ceiling-fresh/report.md` | `77a0bba43370070062f068fbe8ed2cb8b7c8ebed2818855316c6acc0173e3563` |
| `outputs/p-catch-v1/report.md` | `91411d2d494fc0184f418b4056102992ea7ac7992d20573865cf54f1192853de` |
| `outputs/information-v1/information.json` | `0fa07d2f2264f2cbc716a09a2e52b149211e73d58c3f948acf2abfa65ea1a2ea` |

`git status` should still be empty afterwards. If a file changed, that is a finding, not a commit.

## Step 4 — optional: the published table, on a block that is already spent

`BENCHMARK_SPEC.md` §3 allocates `90000–90099` to the reported table and records it as spent once.
Re-running it here is a **determinism check, not new evidence**:

- Whatever it prints may never be quoted as a new result, and may not replace a published number.
- A mismatch is filed as a defect (hash, command, log), never as a correction of the value.
- Do not re-run it a second time looking for a better draw.

```bash
cd "role3 improvement"
python3 run_benchmark.py --seeds 100 --start-seed 90000 \
  --checkpoints outputs/v3/train_{1,2,3}/{gnn_spike_observed,dqn_spike}.pt \
  --out /tmp/v3-repro
```

Expected: the six families match `변경내역.md` to printed precision.

## Receipt — fill this in

| Item | Expected | Yours | Match |
|---|---|---|---|
| Commit | `9379db7` | | |
| `git status --porcelain` | empty | | |
| Python version | ≥ 3.10 | | |
| role3 pytest | 160 passed / 27 subtests | | |
| role2 pytest | 4 passed / 6 subtests | | |
| `run_ordered_gate_v21.py` readout | `R=0.821 [0.630,0.964]`, kept 15/60 | | |
| `gate.json` sha256 | `5822ee7b…` | | |
| `gate.md` sha256 | `188d23f1…` | | |
| dp `report.md` sha256 | `77a0bba4…` | | |
| p-catch `report.md` sha256 | `91411d2d…` | | |
| `information.json` sha256 | `0fa07d2f…` | | |
| Step 4 (optional) | matches `변경내역.md` | | |

**Second person:** name, date, machine, OS.

**Free-text verdict — required.** One of:

- reproduced (every row matched),
- reproduced with deviations (say which, and whether they are version drift or a real bug),
- could not run (say where it stopped — this is a legitimate and useful outcome).

## If something mismatches

Do not edit a frozen output, a pre-registration, or a published number. Append:

- an issue with the command, the log, your `shasum`, and the expected value above;
- a `CORRECTION.md` next to the affected `outputs/` directory if a reported value is wrong.

The rules that govern this are in `BENCHMARK_SPEC.md` §7 and `AUDIT_POLICY.md`. Reproducing a number
and revising a number are different acts; this file only authorises the first.
