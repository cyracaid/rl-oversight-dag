"""Quick gate probe: a handful of graphs, intact + flatten + rewire draw 0."""
import csv
import sys

import core
from core import (MapMismatchEnv, episode_for, flatten_snapshot, rewire_index,
                  run_policy, budget_for, assert_same_episode)

REPO = "/Users/sloblucyra/Documents/강화학습"
FAMILIES = ("spike", "modular", "ba", "er", "real")
POLICIES = ("confidence", "marginal", "structural")


def load_anchor(path, key_condition=None):
    out = {}
    with open(path, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if key_condition is None:
                out[(row["family"], int(row["graph_seed"]), row["policy"])] = (
                    int(row["sink_errors"]), row["actions"])
            else:
                if row["condition"] != key_condition:
                    continue
                out[(row["family"], int(row["graph_seed"]), row["policy"])] = (
                    int(row["sink_errors"]), row["actions"])
    return out


bench = load_anchor(f"{REPO}/role3 improvement/outputs/v3/benchmark_role3.csv")
ctl_intact = load_anchor(f"{REPO}/role4_controls/results/controls.csv", "intact")
ctl_flat = load_anchor(f"{REPO}/role4_controls/results/controls.csv", "flatten")
ctl_rew = load_anchor(f"{REPO}/role4_controls/results/controls.csv", "rewire")

seeds = [int(x) for x in sys.argv[1:]] or [90000, 90001, 90002]
bad = 0
for family in FAMILIES:
    for seed in seeds:
        graph = core.generate_graph(family, seed)
        snap = episode_for(graph, seed)
        budget = budget_for(family)
        view = rewire_index(graph, seed, 0)
        vsnap = episode_for(view, seed)
        assert_same_episode(snap, vsnap)
        assert [len(p) for p in view.parents] == [len(p) for p in graph.parents]
        assert view.types == graph.types and set(view.sinks) == set(graph.sinks)
        for pol in POLICIES:
            e0, a0 = run_policy(graph, snap, graph, snap, pol, budget)
            e1, a1 = run_policy(graph, flatten_snapshot(snap), graph, snap, pol, budget)
            e2, a2 = run_policy(graph, snap, view, vsnap, pol, budget)
            checks = [
                ("intact-bench", (e0, " ".join(map(str, a0))), bench[(family, seed, pol)]),
                ("intact-ctl", (e0, " ".join(map(str, a0))), ctl_intact[(family, seed, pol)]),
                ("flatten", (e1, " ".join(map(str, a1))), ctl_flat[(family, seed, pol)]),
                ("rewire0", (e2, " ".join(map(str, a2))), ctl_rew[(family, seed, pol)]),
            ]
            for tag, mine, ref in checks:
                if mine != ref:
                    bad += 1
                    print("MISMATCH", family, seed, pol, tag,
                          "mine", mine[0], mine[1][:200], "| ref", ref[0], ref[1][:200])
print("bad:", bad)
