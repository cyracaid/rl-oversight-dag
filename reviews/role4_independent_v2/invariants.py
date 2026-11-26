"""Structural invariants of both rewire rules + shared-episode assertion."""
import core
from core import (assert_same_episode, episode_for, rewire_index, rewire_order)

FAM = ("spike", "modular", "ba", "er", "real")
checks = 0
for fam in FAM:
    for seed in (90000, 90001):
        g = core.generate_graph(fam, seed)
        snap = episode_for(g, seed)
        rules = [("index", lambda k: rewire_index(g, seed, k))]
        if fam in ("modular", "ba", "er"):
            rules.append(("order", lambda k: rewire_order(g, seed, k)))
        for name, fn in rules:
            for k in (0, 1, 9):
                v = fn(k)
                assert [len(p) for p in v.parents] == [len(p) for p in g.parents]
                assert v.types == g.types and v.rates == g.rates
                assert set(v.sinks) == set(g.sinks)
                assert v.n == g.n and v.edge_count == g.edge_count
                # acyclicity is guaranteed by DAG() itself; check topo covers all
                assert len(v.topo) == v.n
                vs = episode_for(v, seed)
                assert_same_episode(snap, vs)
                checks += 1
print(f"invariants OK: {checks} (family, seed, rule, draw) checks")
