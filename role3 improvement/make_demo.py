"""Render the one-page receipt demo from committed results.

Presentation only. Every number in the page comes from
``outputs/supervisor-v1/summary.json``; the page has no literals of its own and
no live simulation. That is deliberate: a demo that recomputes can drift from
the report, and a demo that hand-types numbers is a second, unchecked source.

    python3 make_demo.py            # writes ../demo/receipt_demo.html

The interaction is one checkbox: remove the receipt. Everything else is static.
"""
import json
from pathlib import Path

from dag_role3.audit_policy import frozen_policy_v1

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "demo" / "receipt_demo.html"
SUMMARY = HERE / "outputs/supervisor-v1/summary.json"
MANIFEST = HERE / "outputs/supervisor-v1/manifest.json"
FAMILIES = ("spike", "modular", "real", "ticket")
THRESHOLD = 0.90


def load():
    payload = json.loads(SUMMARY.read_text())
    manifest = json.loads(MANIFEST.read_text())
    p1 = payload["p1_holds"]
    rows = {r["family"]: r for r in payload["rows"] if r["policy"] == "marginal"}
    missing = [f for f in FAMILIES if f not in rows]
    if missing:
        raise SystemExit(f"summary.json is missing families: {missing}")
    for family, row in rows.items():
        # The demo tells a story about three statements over one measurement, so
        # the two facts it leans on are checked rather than assumed.
        if not row["overclaim_false_equals_wrong"]:
            raise SystemExit(f"{family}: overclaim no longer equals surviving errors")
        if row["fidelity_min"] != 1.0:
            raise SystemExit(f"{family}: honest fidelity is not 1.0")
        if row["wrong_sinks"] != row["declared_gap"] + row["false_inspection"]:
            raise SystemExit(f"{family}: uncovered + false-inspected != surviving errors")
    return payload, manifest, p1, rows


def card_data(row):
    wrong = row["wrong_sinks"]
    honest_share = row["declared_share"]
    return {
        "wrong": wrong,
        "honest": {
            "uncovered": row["declared_gap"],
            "false_inspected": row["false_inspection"],
            "share": honest_share,
            "status": ("load-bearing" if honest_share is not None and honest_share >= THRESHOLD
                       else "weak"),
        },
        "overclaim": {
            "uncovered": 0,
            "false_inspected": row["overclaim_false_inspection"],
            "share": 0.0,
        },
        "silent": {},
        "counts": row["status_counts"],
        "graphs": row["graphs"],
    }


HTML = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>What a delivery can say about its own coverage</title>
<style>
  :root {
    --bg: #0d1117; --panel: #161b22; --line: #283040; --ink: #e6edf3;
    --dim: #8b949e; --good: #3fb950; --bad: #f85149; --warn: #d29922;
    --accent: #58a6ff;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 40px 24px 64px; background: var(--bg); color: var(--ink);
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  }
  .wrap { max-width: 1080px; margin: 0 auto; }
  h1 { font-size: 26px; margin: 0 0 6px; letter-spacing: -0.02em; }
  .sub { color: var(--dim); margin: 0 0 24px; font-size: 14px; }
  .bar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 20px; }
  button.fam {
    background: var(--panel); color: var(--ink); border: 1px solid var(--line);
    border-radius: 999px; padding: 6px 14px; cursor: pointer; font-size: 13px;
  }
  button.fam[aria-pressed="true"] { border-color: var(--accent); color: var(--accent); }
  .toggle {
    margin-left: auto; display: flex; gap: 8px; align-items: center;
    background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
    padding: 7px 12px; font-size: 13px; cursor: pointer; user-select: none;
  }
  .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
  .card { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 16px; }
  .card h2 { font-size: 14px; margin: 0 0 2px; letter-spacing: 0.02em; }
  .card .tag { color: var(--dim); font-size: 12px; min-height: 34px; }
  .row { display: flex; justify-content: space-between; gap: 12px; padding: 7px 0;
         border-top: 1px solid var(--line); font-size: 13px; }
  .row span:first-child { color: var(--dim); }
  .row b { font-variant-numeric: tabular-nums; }
  .badge { display: inline-block; margin-top: 12px; padding: 3px 9px; border-radius: 999px;
           font-size: 12px; border: 1px solid; }
  .g { color: var(--good); border-color: color-mix(in srgb, var(--good) 45%, transparent); }
  .b { color: var(--bad); border-color: color-mix(in srgb, var(--bad) 45%, transparent); }
  .w { color: var(--warn); border-color: color-mix(in srgb, var(--warn) 45%, transparent); }
  .n { color: var(--dim); border-color: var(--line); }
  .absent { color: #4d5566; font-style: italic; }
  .banner { margin: 18px 0 0; padding: 12px 14px; border-radius: 8px; font-size: 13px;
            border: 1px solid #5a3d00; background: #2a1f05; color: #e3b341; display: none; }
  .banner.on { display: block; }
  .truth { margin: 18px 0 0; padding: 12px 16px; border: 1px solid var(--line);
           border-radius: 8px; background: #11161d; font-size: 13px; color: var(--dim); }
  .truth b { color: var(--ink); font-variant-numeric: tabular-nums; }
  footer { margin-top: 26px; color: var(--dim); font-size: 12px; line-height: 1.7; }
  code { background: #11161d; padding: 1px 5px; border-radius: 4px; }
  @media (max-width: 820px) { .grid { grid-template-columns: 1fr; } }
</style>

<div class="wrap">
  <h1>What a delivery can say about its own coverage</h1>
  <p class="sub">Same review log, same policy, same episodes. Three ways of describing the result.
     One of them makes a question answerable.</p>

  <div class="bar" id="bar"></div>

  <div class="grid">
    <div class="card" id="c-silent">
      <h2>silent</h2>
      <div class="tag">Reports the review log and stops. No field says what was missed.</div>
      <div class="rows"></div>
      <div class="badge n">no claim</div>
    </div>
    <div class="card" id="c-overclaim">
      <h2>overclaim</h2>
      <div class="tag">Every reviewed sink is reported clean, so nothing is reported missed.</div>
      <div class="rows"></div>
      <div class="badge b">wrong</div>
    </div>
    <div class="card" id="c-honest">
      <h2>honest receipt</h2>
      <div class="tag">Says <code>inspected</code>, <code>partial</code> or <code>untouched</code>
        per sink, and counts the errors outside full coverage.</div>
      <div class="rows"></div>
      <div class="badge g">accurate scope</div>
    </div>
  </div>

  <div class="banner" id="banner"></div>
  <div class="truth" id="truth"></div>

  <footer id="foot"></footer>
</div>

<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
const data = JSON.parse(document.getElementById("payload").textContent);
const fams = data.families;
const state = { family: fams[0], removed: false };

const fmtPct = x => (x === null || x === undefined) ? "—" : (100 * x).toFixed(1) + "%";
const row = (label, value, absent) =>
  `<div class="row"><span>${label}</span>` +
  (absent ? `<b class="absent">no field</b>` : `<b>${value}</b>`) + `</div>`;

function paint() {
  const d = data.cells[state.family];

  const bar = document.getElementById("bar");
  bar.innerHTML = fams.map(f =>
    `<button class="fam" data-f="${f}" aria-pressed="${f === state.family}">${f}</button>`
  ).join("") + `<label class="toggle"><input type="checkbox" id="kill" ${state.removed ? "checked" : ""}>
    remove the receipt</label>`;

  const silent = document.querySelector("#c-silent .rows");
  silent.innerHTML =
    row("surviving sink errors", d.wrong) +
    row("reported uncovered", "", true) +
    row("reported inspected but wrong", "", true) +
    row("declared share", "", true);

  const over = document.querySelector("#c-overclaim .rows");
  over.innerHTML =
    row("surviving sink errors", d.wrong) +
    row("reported uncovered", d.overclaim.uncovered) +
    row("reported inspected but wrong", d.overclaim.false_inspected) +
    row("declared share", fmtPct(d.overclaim.share));

  const honest = document.querySelector("#c-honest .rows");
  honest.innerHTML = state.removed
    ? row("surviving sink errors", d.wrong) +
      row("reported uncovered", "", true) +
      row("reported inspected but wrong", "", true) +
      row("declared share", "", true)
    : row("surviving sink errors", d.wrong) +
      row("reported uncovered", d.honest.uncovered) +
      row("reported inspected but wrong", d.honest.false_inspected) +
      row("declared share", fmtPct(d.honest.share));

  const badge = document.querySelector("#c-honest .badge");
  badge.className = "badge " + (state.removed ? "n" : "g");
  badge.textContent = state.removed ? "question not askable" : "accurate scope";

  const banner = document.getElementById("banner");
  banner.classList.toggle("on", state.removed);
  banner.textContent = state.removed
    ? "Receipt removed. The counts still exist in the log; the statement about what they cover does not. "
      + "\\u201cHow many of the surviving errors did we not cover?\\u201d now has no answer \\u2014 not a worse one."
    : "";

  document.getElementById("truth").innerHTML =
    `<b>${d.graphs}</b> episodes, <code>${state.family}</code>. ` +
    `Measured surviving errors: <b>${d.wrong}</b>. ` +
    `Of those, <b>${d.honest.uncovered}</b> sit outside full coverage and ` +
    `<b>${d.honest.false_inspected}</b> sit inside sinks whose every upstream source was reviewed ` +
    `(that is <code>p_catch = ${data.p_catch}</code>, not a reporting bug).`;

  document.getElementById("foot").innerHTML = data.footer;

  bar.querySelectorAll("button.fam").forEach(b =>
    b.onclick = () => { state.family = b.dataset.f; paint(); });
  document.getElementById("kill").onchange = e => { state.removed = e.target.checked; paint(); };
}

paint();
</script>
</html>
"""


def build():
    """Return (html, payload) without touching disk, so tests can inspect it."""
    payload, manifest, p1, rows = load()
    cells = {f: card_data(rows[f]) for f in FAMILIES}
    digest = manifest["sha256"]
    footer = (
        "Block {b0}–{b1}, p_catch {pc}, policy register <code>{fp}</code>. "
        "Rendered by <code>make_demo.py</code> from <code>outputs/supervisor-v1/summary.json</code>; "
        "the page contains no numbers of its own. "
        "Illustrative: the three columns are three statements about the same episodes, not three runs. "
        "P1 (receipt changes no action) {p1}. Hashes: <code>{h_env}</code> environment, "
        "<code>{h_sup}</code> supervisor, <code>{h_run}</code> runner. "
        "Result file: <code>outputs/supervisor-v1/receipt_vs_silent.md</code>."
    ).format(
        b0=manifest["block"][0], b1=manifest["block"][1], pc=manifest["p_catch"],
        fp=frozen_policy_v1().fingerprint(), p1="holds" if p1 else "fails",
        h_env=digest["dag_role3/environment.py"][:16] + "…",
        h_sup=digest["dag_role3/supervisor.py"][:16] + "…",
        h_run=digest["run_supervisor_check.py"][:16] + "…",
    )
    data = {"families": list(FAMILIES), "cells": cells, "p_catch": manifest["p_catch"],
            "footer": footer}
    return HTML.replace("__PAYLOAD__", json.dumps(data)), data


def main():
    html, _ = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
