"""Check that README "Exact `rewire_order` procedure" is complete.

`from_readme()` follows the README section step by step and does not call or copy
run_controls_v2.rewire_order. For every graph of both v2 blocks (90000-90099, 7100-7199), every family that
has `rewire_order` (modular, BA, ER) and every draw k = 0..9, it must produce exactly the same parent tuples
as the committed code. Two plausible misreadings must NOT match, which is why the README names them.

    python3 check_rewire_order_spec.py      # ~5 min, one core; exit 0 = README reproduces the code exactly
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_controls_v2 as v2  # noqa: E402  (only for the reference graphs and constants)
from dag_role3 import generate_graph  # noqa: E402

BLOCKS = (90000, 7100)
FAMILIES = ("modular", "ba", "er")


def from_readme(graph, graph_seed, k, phase_b_sorted_pool=False, phase_b_index_order=False):
    """README steps 1-4; returns the parent tuples. The two flags are the misreadings."""
    rng = random.Random(5_050_000 + 100_000 * k + graph_seed)            # step 1
    need = [len(p) for p in graph.parents]                              # step 2
    placed, unplaced = [], set(range(graph.n))
    while unplaced:                                                     # step 3, phase A
        pool = sorted(v for v in unplaced if need[v] <= len(placed))
        v = rng.choice(pool)
        placed.append(v)
        unplaced.remove(v)
    where = {v: i for i, v in enumerate(placed)}
    walk = sorted(placed) if phase_b_index_order else placed
    parents = [()] * graph.n
    for v in walk:                                                      # step 4, phase B
        if need[v] == 0:
            continue
        population = placed[:where[v]]
        if phase_b_sorted_pool:
            population = sorted(population)
        parents[v] = tuple(sorted(rng.sample(population, need[v])))
    return tuple(parents)


def main():
    checked = mismatched = 0
    misread = {"phase_b_sorted_pool": 0, "phase_b_index_order": 0}
    for block in BLOCKS:
        for family in FAMILIES:
            for seed in range(block, block + 100):
                graph = generate_graph(family, seed)
                for k in range(v2.K_DRAWS):
                    ref = v2.rewire_order(graph, seed, k)
                    assert ref.sinks == graph.sinks and ref.types == graph.types
                    checked += 1
                    if from_readme(graph, seed, k) != ref.parents:
                        mismatched += 1
                    for flag in misread:
                        if from_readme(graph, seed, k, **{flag: True}) != ref.parents:
                            misread[flag] += 1
        print(f"block {block}: done", flush=True)
    print(f"README procedure vs committed rewire_order: {checked - mismatched}/{checked} graphs identical")
    for flag, n in misread.items():
        print(f"  misreading {flag}: differs on {n}/{checked} graphs")
    ok = mismatched == 0 and all(n > 0 for n in misread.values())
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
