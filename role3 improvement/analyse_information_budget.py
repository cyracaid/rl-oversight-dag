"""Information-theoretic readings of the *existing* environment. Zero seed blocks.

Nothing here samples an episode, runs a policy, or touches the frozen ledger. Every
number is a closed-form function of (graph, prior rate table, edge probability), plus
an optional replay of the shipped particle filter at its default belief seed.

Three quantities per node, all conditional on the simulator's assumed generative model:

    p_j    exact marginal P(node j effectively wrong)   (forward OR recursion)
    H_j    H(E_j) in bits
    I_j    I(E_j ; O_j), the review channel. The channel is a Z-channel: a clean node
           is never flagged, a wrong node is flagged with p_catch. So "not flagged" is
           the only outcome that carries information, and it is ambiguous.
    VoI_j  p_catch * p_j * delta_j, delta_j = exact drop in E[#wrong conclusions]
           when node j's *local* source error is cleared. This is one-step value of
           information under the residual-error loss.

Run: /usr/local/bin/python3.14 analyse_information_budget.py
"""
from __future__ import annotations

import json
import math

import numpy as np

from dag_role3.graphs import gen_real, gen_ticket
from dag_role3.policies import marginal_scores

P_CATCH = 0.9


def forward_marginals(graph, base, w):
    """Exact marginal P(v effectively wrong). Exact for marginals, not for the joint."""
    p = np.zeros(graph.n)
    for v in graph.topo:
        clean = 1.0
        for u in graph.parents[v]:
            clean *= 1.0 - p[u] * w[u, v]
        p[v] = 1.0 - (1.0 - base[v]) * clean
    return p


def binary_entropy(p):
    p = min(max(float(p), 1e-12), 1 - 1e-12)
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


def z_channel_information(p, p_catch=P_CATCH):
    """I(E;O) for P(O=1|E=1)=p_catch, P(O=1|E=0)=0."""
    h_e = binary_entropy(p)
    p_o0 = 1.0 - p_catch * p                # nothing flagged
    miss = p * (1.0 - p_catch)
    p_e_given_o0 = miss / p_o0 if p_o0 > 0 else 0.0
    h_cond = p_o0 * binary_entropy(p_e_given_o0)
    return max(0.0, h_e - h_cond)


def asymmetric_channel_information(prior, p_pos_given_1, p_pos_given_0):
    """I(X;O) for a binary X and a binary observation with the given hit rates."""
    h_x = binary_entropy(prior)
    p1 = prior * p_pos_given_1 + (1 - prior) * p_pos_given_0
    h_cond = 0.0
    for p_o, lik1, lik0 in ((p1, p_pos_given_1, p_pos_given_0), (1 - p1, 1 - p_pos_given_1, 1 - p_pos_given_0)):
        if p_o <= 0:
            continue
        post = prior * lik1 / p_o
        h_cond += p_o * binary_entropy(post)
    return max(0.0, h_x - h_cond)


def analyse(graph, lam_weight=1.0, label=""):
    n = graph.n
    base = np.array([graph.rates[graph.types[i]] for i in range(n)])
    w = np.full((n, n), 1.0 - math.exp(-graph.lam * lam_weight))
    p = forward_marginals(graph, base, w)
    sinks = np.asarray(graph.sinks, dtype=int)
    total = float(p[sinks].sum())

    # Split the effective-error probability into the part a review can repair and the
    # part it cannot: e_j = b_j OR (inherited from a parent). Only b_j is fixable.
    inherit = np.zeros(n)
    for v in range(n):
        clean = 1.0
        for u in graph.parents[v]:
            clean *= 1.0 - p[u] * w[u, v]
        inherit[v] = 1.0 - clean
    # A flag reports e_j, not b_j: P(flag|b_j=1)=p_catch, P(flag|b_j=0)=p_catch*inherit_j.
    info_b = np.array([
        asymmetric_channel_information(base[j], P_CATCH, P_CATCH * inherit[j]) for j in range(n)
    ])

    delta = np.zeros(n)
    for j in range(n):
        b2 = base.copy()
        b2[j] = 0.0
        delta[j] = total - float(forward_marginals(graph, b2, w)[sinks].sum())

    # A review repairs b_j only when the node is *flagged AND its own value is the
    # culprit*: P(flag and b_j=1) = p_catch * base_j (b_j=1 implies e_j=1). Using p_j
    # here would over-credit every node whose error is mostly inherited.
    voi = P_CATCH * base * delta
    H = np.array([binary_entropy(x) for x in p])
    I = np.array([z_channel_information(x) for x in p])

    # The shipped baseline: reverse-derivative approximation of the same delta.
    k = len(graph.rates)
    f = np.zeros((n, k + 7), dtype=np.float64)
    f[np.arange(n), list(graph.types)] = 1.0
    f[:, k + 2] = base
    obs = {
        "features": f,
        "edge_index": graph.edge_index(),
        "edge_probability": np.array([w[u, v] for u, v in graph.edge_index().T]),
        "topological_order": np.array(graph.topo),
        "sink_ids": sinks,
    }
    mar = marginal_scores(obs)

    def rank(x):
        return [int(i) for i in np.argsort(-np.asarray(x), kind="stable")]

    def spearman(a, b):
        from scipy.stats import spearmanr
        return float(spearmanr(a, b).statistic)

    out = {
        "family": graph.family,
        "label": label,
        "n": n,
        "sinks": list(map(int, sinks)),
        "expected_wrong_conclusions": total,
        "total_entropy_bits": float(sum(binary_entropy(x) for x in p)),
        "max_entropy_bits": float(n),
        "expected_information_first_review_bits": float(I.max()),
        "mean_information_first_review_bits": float(I.mean()),
        "top1": {
            "by_probability": int(np.argmax(p)),
            "by_entropy": int(np.argmax(H)),
            "by_information": int(np.argmax(I)),
            "by_voi": int(np.argmax(voi)),
            "by_marginal_baseline": int(np.argmax(mar)),
        },
        "top5": {
            "by_probability": rank(p)[:5],
            "by_entropy": rank(H)[:5],
            "by_voi": rank(voi)[:5],
            "by_marginal_baseline": rank(mar)[:5],
        },
        "spearman": {
            "entropy_vs_voi": spearman(H, voi),
            "entropy_vs_probability": spearman(H, p),
            "information_vs_voi": spearman(I, voi),
            "repairable_information_vs_voi": spearman(info_b, voi),
            "repairable_information_vs_information": spearman(info_b, I),
            "voi_vs_marginal_baseline": spearman(voi, mar),
            "voi_vs_sink_reach": spearman(voi, np.asarray(graph.sink_reach, dtype=float)),
        },
        "max_abs_error_baseline_vs_exact_voi": float(np.max(np.abs(mar - voi))),
        "voi_range": [float(voi.min()), float(voi.max())],
        "total_repairable_entropy_bits": float(sum(binary_entropy(x) for x in base)),
        "max_repairable_information_bits": float(info_b.max()),
        "median_repairable_fraction": float(np.median(info_b / np.maximum(I, 1e-12))),
        "top1_repairable": {
            "node": int(np.argmax(info_b)),
            "information_bits": float(info_b.max()),
            "voi": float(voi[int(np.argmax(info_b))]),
        },
        "nodes": [
            {
                "node": int(i),
                "p": float(p[i]),
                "entropy_bits": float(H[i]),
                "information_bits": float(I[i]),
                "repairable_information_bits": float(info_b[i]),
                "inherited_share": float(inherit[i]),
                "voi": float(voi[i]),
                "delta": float(delta[i]),
                "marginal_baseline": float(mar[i]),
                "sink_reach": int(graph.sink_reach[i]),
            }
            for i in range(n)
        ],
    }
    return out


def main():
    results = []
    for graph in (gen_real(), gen_ticket()):
        for lam_weight, label in ((1.0, "nominal"), (0.6, "weak_edges"), (1.4, "strong_edges")):
            results.append(analyse(graph, lam_weight, label))

    payload = {
        "note": "Closed-form analysis of the shipped generative model. No sampling, no seed blocks.",
        "p_catch": P_CATCH,
        "lam_weight": {"nominal": 1.0, "weak_edges": 0.6, "strong_edges": 1.4},
        "results": results,
    }
    with open("outputs/information-v1/information.json", "w") as fh:
        json.dump(payload, fh, indent=2)

    for r in results:
        print(f"== {r['family']} / {r['label']}: n={r['n']} sinks={r['sinks']}")
        print(f"   E[wrong conclusions] = {r['expected_wrong_conclusions']:.3f} / {len(r['sinks'])}")
        print(f"   sum H(E_j) = {r['total_entropy_bits']:.2f} bits (ceiling {r['max_entropy_bits']:.0f})")
        print(f"   first review: max I = {r['expected_information_first_review_bits']:.4f} bits, "
              f"mean I = {r['mean_information_first_review_bits']:.4f}")
        print(f"   argmax p={r['top1']['by_probability']} H={r['top1']['by_entropy']} "
              f"I={r['top1']['by_information']} VoI={r['top1']['by_voi']} "
              f"baseline={r['top1']['by_marginal_baseline']}")
        s = r["spearman"]
        print(f"   argmax repairable-information: node {r['top1_repairable']['node']} "
              f"({r['top1_repairable']['information_bits']:.3f} bits, VoI {r['top1_repairable']['voi']:.4f})")
        print(f"   spearman H~VoI {s['entropy_vs_voi']:+.3f}  I(E)~VoI {s['information_vs_voi']:+.3f}  "
              f"I(B)~VoI {s['repairable_information_vs_voi']:+.3f}  "
              f"I(B)~I(E) {s['repairable_information_vs_information']:+.3f}")
        print(f"   VoI~baseline {s['voi_vs_marginal_baseline']:+.3f}  VoI~reach {s['voi_vs_sink_reach']:+.3f}")
        print(f"   sum H(B) repairable = {r['total_repairable_entropy_bits']:.2f} bits; "
              f"max I(B) = {r['max_repairable_information_bits']:.3f} bits; "
              f"median I(B)/I(E) = {r['median_repairable_fraction']:.3f}")
        print(f"   baseline vs exact one-step VoI: max abs err "
              f"{r['max_abs_error_baseline_vs_exact_voi']:.4f} (VoI max {r['voi_range'][1]:.4f})")
        print()


if __name__ == "__main__":
    main()
