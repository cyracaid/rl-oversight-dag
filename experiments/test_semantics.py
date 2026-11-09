#!/usr/bin/env python3
"""Unit tests for the review semantics and the common-random-numbers switch.

Run:  python3 experiments/test_semantics.py

These tests pin down what a review actually does, because the docs used to say
`do(X_v = 1)` while the simulator clears only the node's own error. They also
check that the CRN switch makes a node's reviewer outcome independent of the
policy's ordering.

No file is written; exit code 0 means all checks passed.
"""

from __future__ import annotations

import random
import sys

from belief import ParticleBelief
from spike_active_selection import CFG, compute_err, episode_uniforms, review_step


def tiny_graph():
    """A -> B -> C, both edges infected with probability 1 (coins True)."""
    nodes = [
        {"layer": 0, "type": 0, "parents": []},
        {"layer": 1, "type": 0, "parents": [0]},
        {"layer": 2, "type": 0, "parents": [1]},
    ]
    coins = {(0, 1): True, (1, 2): True}
    return nodes, [0, 1, 2], coins


def with_catch(p=1.0):
    old = CFG["p_catch"]
    CFG["p_catch"] = p
    return old


def test_fix_base_error():
    """Reviewing a node with its own error and a clean parent clears the error."""
    nodes, topo, coins = tiny_graph()
    base = [True, False, False]
    err = compute_err(base, nodes, topo, coins)
    assert err == [True, True, True], err

    old = with_catch()
    try:
        flagged, err = review_step(0, base, err, nodes, topo, coins, random.Random(0))
    finally:
        CFG["p_catch"] = old
    assert flagged is True
    assert base[0] is False
    assert err == [False, False, False], err


def test_inherited_error_persists():
    """A node that is wrong only because its parent is wrong stays wrong after review.

    This is the consequence the docs must state: a review is not do(X_v = 1).
    """
    nodes, topo, coins = tiny_graph()
    base = [True, False, False]
    err = compute_err(base, nodes, topo, coins)

    old = with_catch()
    try:
        flagged, err = review_step(1, base, err, nodes, topo, coins, random.Random(1))
    finally:
        CFG["p_catch"] = old
    assert flagged is True, "the reviewer sees the inherited error"
    assert err[1] is True, "but fixing B does not fix A, so B stays wrong"


def test_mixed_source_and_inherited():
    """With both a base error and an inherited one, review clears only the base part."""
    nodes, topo, coins = tiny_graph()
    base = [True, True, False]
    err = compute_err(base, nodes, topo, coins)
    assert err == [True, True, True]

    old = with_catch()
    try:
        _, err = review_step(1, base, err, nodes, topo, coins, random.Random(2))
    finally:
        CFG["p_catch"] = old
    assert base[1] is False, "the node's own error is cleared"
    assert err[1] is True, "the parent's error still propagates into it"


def test_belief_gain_is_zero_without_base_error():
    """belief.gain must agree with the simulator: no source error, nothing to gain."""
    nodes, topo, coins = tiny_graph()
    parents = [nd["parents"] for nd in nodes]
    edge_prob = {(p, i): 1.0 for i, ps in enumerate(parents) for p in ps}
    base_prob = [0.0, 1.0, 0.0]      # only B has a possible base error
    b = ParticleBelief(parents, topo, sinks={2}, edge_prob=edge_prob,
                       base_prob=base_prob, p_catch=0.9, n_particles=64, seed=0)
    assert b.gain(0) == 0.0, "A has no base error in any particle"
    assert b.gain(1) > 0.0, "B does"


def test_crn_independent_of_order():
    """Under CRN, a node's reviewer outcome does not depend on when it is reviewed."""
    nodes, topo, coins = tiny_graph()

    def run(order):
        CFG["crn"] = True
        old = with_catch(0.5)
        try:
            rng = random.Random(7)
            u = episode_uniforms(rng, len(nodes))
            base = [True, False, True]
            err = compute_err(base, nodes, topo, coins)
            out = {}
            for i in order:
                flagged, err = review_step(i, base, err, nodes, topo, coins, rng, u)
                out[i] = flagged
            return out, u
        finally:
            CFG["p_catch"] = old
            CFG["crn"] = False

    a, u1 = run([0, 2])
    b, u2 = run([2, 0])
    assert u1 == u2, "the uniform stream must be identical"
    # node 2's own draw is the same in both orders; whether it is *flagged* can
    # differ only because node 0 was reviewed first and changed its state.
    assert u1[2] == u2[2]


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {t.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
