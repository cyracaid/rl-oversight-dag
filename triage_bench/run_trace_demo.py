#!/usr/bin/env python3
"""Traceability demo on the real N=21 sleep pipeline.

The acceptance question from the evidence-chain review:

    change one upstream node -> what is affected, what is stale, and can a second
    researcher follow the list to the right places?

Run:
    python3 triage_bench/run_trace_demo.py --change time_awake
    python3 triage_bench/run_trace_demo.py --change time_awake --json

Guarantees this demo is built to show:

  * it never marks a downstream node "wrong" -- only "affected";
  * a review receipt goes "stale", it is never deleted;
  * the report names the exact path from the change to each conclusion.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.real_pipeline_graph import LAYER, NAME, NODES, PARENTS, SINKS  # noqa: E402

from triage_bench.audit.receipts import Receipt  # noqa: E402

KIND = {0: "raw input", 1: "derived", 2: "metric", 3: "conclusion"}
SINK_NAMES = {NAME[i] for i in SINKS}


def children() -> dict[str, list[str]]:
    kids: dict[str, list[str]] = {name: [] for name in NAME}
    for node, parents in PARENTS.items():
        for p in parents:
            kids[p].append(node)
    return kids


def affected(start: str) -> dict[str, tuple[int, list[str]]]:
    """node -> (distance, one shortest path from the changed node)."""
    kids = children()
    out: dict[str, tuple[int, list[str]]] = {}
    q = deque([(start, 0, [start])])
    seen = {start}
    while q:
        node, dist, path = q.popleft()
        out[node] = (dist, path)
        for c in kids[node]:
            if c not in seen:
                seen.add(c)
                q.append((c, dist + 1, path + [c]))
    return out


def demo_receipts(version: str = "v1") -> list[Receipt]:
    """One accepted receipt per node, bound to the version that was reviewed."""
    out = []
    for name in NAME:
        out.append(Receipt(
            artifact_version=f"{name}@{version}",
            field_path=None,
            verdict="accepted",
            actor="sha256:curator",
            reason_code=KIND[LAYER[NAME.index(name)]],
        ))
    return out


def trace(change: str, old_version: str = "v1", new_version: str = "v2") -> dict:
    reach = affected(change)
    receipts = demo_receipts(old_version)

    rows = []
    for name, (dist, path) in sorted(reach.items(), key=lambda kv: (kv[1][0], kv[0])):
        rows.append({
            "node": name,
            "kind": KIND[LAYER[NAME.index(name)]],
            "distance": dist,
            "path": " → ".join(path),
            "is_conclusion": name in SINK_NAMES,
        })

    stale = [r for r in receipts if r.artifact_version.split("@")[0] in reach]
    kept = [r for r in receipts if r not in stale]

    return {
        "change": change,
        "from_version": old_version,
        "to_version": new_version,
        "affected_count": len(reach),
        "conclusions_affected": [r["node"] for r in rows if r["is_conclusion"]],
        "rows": rows,
        "stale_receipts": len(stale),
        "valid_receipts": len(kept),
        "stale_nodes": sorted(r.artifact_version.split("@")[0] for r in stale),
    }


def render(out: dict) -> str:
    lines = [
        f"# Traceability demo — change at `{out['change']}` "
        f"({out['from_version']} → {out['to_version']})",
        "",
        f"Affected nodes: **{out['affected_count']} / {len(NAME)}**  |  "
        f"conclusions affected: **{len(out['conclusions_affected'])} / {len(SINK_NAMES)}**  |  "
        f"stale receipts: **{out['stale_receipts']}**, still valid: **{out['valid_receipts']}**",
        "",
        "> No node is marked wrong. The system asserts only *affected* and *stale*; "
        "whether a conclusion still holds is a human verdict.",
        "",
        "| node | kind | distance | path from the change |",
        "|---|---|---:|---|",
    ]
    for r in out["rows"]:
        mark = " **(conclusion)**" if r["is_conclusion"] else ""
        lines.append(f"| `{r['node']}`{mark} | {r['kind']} | {r['distance']} | {r['path']} |")

    lines += [
        "",
        "## Receipts invalidated by the change",
        "",
        f"`{out['stale_receipts']}` of {out['stale_receipts'] + out['valid_receipts']} "
        "review receipts are bound to an earlier version of an affected node. They are "
        "**marked stale, not deleted**: the record of the review still exists, it just no "
        "longer covers the current version.",
        "",
        "## The test a second researcher has to pass",
        "",
        "1. pick a conclusion in the table above;",
        "2. follow its path back to the changed input;",
        "3. say which assumption the change touches;",
        "4. say whether the existing receipt still covers it.",
        "",
        "If they can do that without asking the author, the trace is doing its job.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--change", default="time_awake", choices=NAME)
    ap.add_argument("--from-version", default="v1")
    ap.add_argument("--to-version", default="v2")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--all", action="store_true", help="summary for every raw input")
    args = ap.parse_args()

    if args.all:
        rows = [trace(n, args.from_version, args.to_version) for n in NAME if LAYER[NAME.index(n)] == 0]
        rows.sort(key=lambda r: (-len(r["conclusions_affected"]), -r["affected_count"]))
        print("| changed input | affected nodes | conclusions hit | stale receipts |")
        print("|---|---:|---|---:|")
        for r in rows:
            hit = ", ".join(r["conclusions_affected"]) or "—"
            print(f"| `{r['change']}` | {r['affected_count']} | {hit} | {r['stale_receipts']} |")
        return

    out = trace(args.change, args.from_version, args.to_version)
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    text = render(out)
    from triage_bench.bench import config  # local import keeps --json path light
    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    (config.OUT_DIR / f"trace_{args.change}.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
