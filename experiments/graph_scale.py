#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scaled + mathematical environment: 500-node dependency DAGs.

Graph families
  - modular : 10 clusters × 50 nodes; intra-cluster propagation high,
              inter-cluster only via interface nodes
  - BA      : Barabási–Albert scale-free, oriented low→high index (DAG)
  - ER      : Erdős–Rényi sparse, oriented low→high index (DAG)

Error model (causal intervention form)
  Base error of node v: X_v ~ Bernoulli(p_type[t_v]), p_type ~ Zipf(s)
  Propagation along edge (u,v):
      P(X_v = 0 | X_u = 0) = 1 - exp(-λ * w_uv)
  A review is a causal intervention: force X_v = 1, cutting outgoing infection.

Baselines (no RL): no-review, random, conf-threshold, hub (degree),
  belief greedy (deployable: adaptive greedy on a particle belief that sees only
  structure, edge probabilities, calibrated confidence and its own review outcomes),
  oracle greedy (reads the true error state; a ceiling, not a policy).

Mathematical notes are in the module docstring of each generator and in
the proposal Section 5 / new Section "scaled experiments".
"""
import numpy as np
import networkx as nx
import math
import random
import time

from belief import ParticleBelief, conf_posterior, sample_conf

# ---------------------------------------------------------------- config
N = 500
K = 10                    # error types
LAMBDA = 0.8              # infection coefficient
ZIPF_S = 1.2
P_CATCH = 0.9
BUDGET = 50               # 10% of N
N_SEEDS = 5
N_EP_TRIALS = 20          # Monte Carlo repetitions per seed for propagation noise
N_PARTICLES = 1024        # belief particles; fewer collapse after a few flags


def zipf_type_rates(k=K, s=ZIPF_S):
    """Heavy-tailed type rates: a few deadly types cause most crashes."""
    w = np.array([1.0 / (t + 1) ** s for t in range(k)])
    w = w / w.sum()
    # map to error rates in a deadly-to-mild range
    rates = 0.02 + 0.38 * w          # deadly type ~0.40, mild ~0.02
    return rates


P_TYPE = zipf_type_rates()


def make_dag_from_undirected(G, rng):
    """Orient an undirected graph into a DAG by node index (u<v)."""
    nodes = list(G.nodes())
    dag = {i: [] for i in nodes}          # parents
    for u, v in G.edges():
        if u > v:
            u, v = v, u
        dag[v].append(u)
    return dag


def gen_modular(seed):
    """10 clusters × 50 nodes. Intra propagation high; inter only via interfaces."""
    rng = np.random.default_rng(seed)
    parents = [[] for _ in range(N)]
    C = 10
    per = N // C
    # intra-cluster edges: each node gets 1-2 parents from same cluster (earlier index)
    for c in range(C):
        start = c * per
        for i in range(start + 1, start + per):
            k = rng.integers(1, 3)
            cand = list(range(start, i))
            if not cand:
                continue
            ps = rng.choice(cand, size=min(k, len(cand)), replace=False)
            parents[i].extend(ps.tolist())
    # inter-cluster: only interface nodes (last 5 of each cluster) connect to next cluster
    for c in range(C - 1):
        iface_src = [c * per + per - 1 - j for j in range(3)]   # last 3 of cluster c
        start_next = (c + 1) * per
        for i in range(start_next, min(start_next + 5, N)):
            if rng.random() < 0.5 and iface_src:
                parents[i].append(int(rng.choice(iface_src)))
    # dedupe, remove self
    for i in range(N):
        parents[i] = sorted(set(p for p in parents[i] if p != i))
    return parents


def gen_ba(seed, m=3):
    """Barabási–Albert scale-free, oriented by index → DAG. Hubs = low-index nodes."""
    G = nx.barabasi_albert_graph(N, m, seed=seed)
    parents = [[] for _ in range(N)]
    for u, v in G.edges():
        if u > v:
            u, v = v, u
        parents[v].append(int(u))
    return parents


def gen_er(seed, p=0.015):
    """Erdős–Rényi sparse, oriented by index → DAG."""
    G = nx.erdos_renyi_graph(N, p, seed=seed)
    parents = [[] for _ in range(N)]
    for u, v in G.edges():
        if u > v:
            u, v = v, u
        parents[v].append(int(u))
    return parents


def topo_order(parents):
    indeg = [0] * N
    for i, ps in enumerate(parents):
        indeg[i] = len(ps)
    # Kahn
    children = [[] for _ in range(N)]
    for i, ps in enumerate(parents):
        for p in ps:
            children[p].append(i)
    from collections import deque
    q = deque(i for i in range(N) if indeg[i] == 0)
    order = []
    while q:
        i = q.popleft()
        order.append(i)
        for c in children[i]:
            indeg[c] -= 1
            if indeg[c] == 0:
                q.append(c)
    if len(order) != N:
        raise RuntimeError("not a DAG")
    return order, children


def sample_base(rng_np, types):
    return [bool(rng_np.random() < P_TYPE[types[i]]) for i in range(N)]


def propagate(base, parents, topo, coins, rng_py):
    """Causal propagation: P(X_v=0 | X_u=0) = 1 - exp(-λ w), w ~ U(0.5, 1.5) baked into coins."""
    err = [False] * N
    for i in topo:
        err[i] = base[i]
        if not err[i]:
            for p in parents[i]:
                if err[p] and coins[(p, i)]:
                    err[i] = True
                    break
    return err


def make_coins(parents, rng):
    """w_uv ~ U(0.5, 1.5); P = 1 - exp(-λ w). Returns (coins, probs); probs are public."""
    coins, probs = {}, {}
    for i, ps in enumerate(parents):
        for p in ps:
            w = rng.uniform(0.5, 1.5)
            probs[(p, i)] = 1.0 - math.exp(-LAMBDA * w)
            coins[(p, i)] = rng.random() < probs[(p, i)]
    return coins, probs


def make_conf(base, types, rng):
    """Noisy confidence, same model as the 80-node version (belief.sample_conf)."""
    return [sample_conf(base[i], P_TYPE[types[i]], rng) for i in range(N)]


def sink_error(err, sinks):
    return sum(1 for i in sinks if err[i])


def review_step(a, base, err, parents, topo, coins, rng):
    """Review node a in place. Returns (flagged, err)."""
    flagged = err[a] and rng.random() < P_CATCH
    if flagged:
        base[a] = False
        err = propagate(base, parents, topo, coins, rng)
    return flagged, err


def review_and_count(order, base, parents, topo, coins, sinks, rng):
    base = list(base)
    err = propagate(base, parents, topo, coins, rng)
    for i in order:
        _, err = review_step(i, base, err, parents, topo, coins, rng)
    return sink_error(err, sinks)


def belief_greedy_and_count(belief, base, parents, topo, coins, sinks, rng):
    """Adaptive greedy on the particle belief; each outcome is fed back to the belief."""
    base = list(base)
    err = propagate(base, parents, topo, coins, rng)
    available = [True] * N
    for _ in range(BUDGET):
        a = belief.best_action(available)
        available[a] = False
        flagged, err = review_step(a, base, err, parents, topo, coins, rng)
        belief.observe(a, flagged)
    return sink_error(err, sinks)


# ---------------------------------------------------------------- experiments
def run_family(family, seed):
    rng = random.Random(seed)
    rng_np = np.random.default_rng(seed)
    if family == "modular":
        parents = gen_modular(seed)
    elif family == "ba":
        parents = gen_ba(seed)
    elif family == "er":
        parents = gen_er(seed)
    else:
        raise ValueError(family)
    topo, children = topo_order(parents)
    coins, edge_prob = make_coins(parents, rng)
    types = [rng.randrange(K) for _ in range(N)]
    base = sample_base(rng_np, types)
    conf = make_conf(base, types, rng)
    sinks = set(i for i in range(N) if not children[i])   # no children = sink/conclusion
    if not sinks:
        sinks = set(range(N - 20, N))

    # policies
    idx = list(range(N))
    rng.shuffle(idx)
    pol_random = idx[:BUDGET]
    pol_thresh = sorted(idx, key=lambda i: conf[i])[:BUDGET]
    pol_hub = sorted(idx, key=lambda i: -len(children[i]))[:BUDGET]
    # oracle greedy: reads the TRUE error state (skips nodes that are not wrong).
    # Not deployable; reported only as a ceiling.
    base_g = list(base)
    err = propagate(base_g, parents, topo, coins, rng)
    chosen = []
    remaining = set(idx)
    for _ in range(BUDGET):
        best, bestval = None, None
        for i in remaining:
            if not err[i]:
                continue
            tmp = list(base_g)
            tmp[i] = False
            e2 = propagate(tmp, parents, topo, coins, rng)
            val = sink_error(e2, sinks)
            if bestval is None or val < bestval:
                bestval, best = val, i
        if best is None:
            break
        chosen.append(best)
        remaining.discard(best)
        base_g[best] = False
        err = propagate(base_g, parents, topo, coins, rng)
    pol_oracle_greedy = chosen

    def catch_rng():
        # every policy replays the same catch-randomness stream -> paired comparison
        return random.Random(1_000_000 + seed)

    no_rev = sink_error(propagate(base, parents, topo, coins, rng), sinks)
    args = (base, parents, topo, coins, sinks)
    out = {
        "no_review": no_rev,
        "random": review_and_count(pol_random, *args, catch_rng()),
        "threshold": review_and_count(pol_thresh, *args, catch_rng()),
        "hub": review_and_count(pol_hub, *args, catch_rng()),
        "oracle_greedy": review_and_count(pol_oracle_greedy, *args, catch_rng()),
        "n_err_base": sum(base),
        "n_sinks": len(sinks),
        "n_edges": sum(len(p) for p in parents),
        "max_deg": max(len(children[i]) for i in range(N)),
    }
    prior = [conf_posterior(conf[i], P_TYPE[types[i]]) for i in range(N)]
    belief = ParticleBelief(parents, topo, sinks, edge_prob, prior, P_CATCH,
                            n_particles=N_PARTICLES, seed=10_000 + seed)
    out["belief_greedy"] = belief_greedy_and_count(belief, *args, catch_rng())
    return out


def main():
    print("=" * 72)
    print(f"Scaled experiments: N={N}, budget={BUDGET} (10%), λ={LAMBDA}, Zipf s={ZIPF_S}")
    print(f"P_type (deadly→mild): {[round(p,3) for p in P_TYPE]}")
    print(f"Seeds: {list(range(1, N_SEEDS+1))}, MC trials folded into coins/propagation")
    print("=" * 72)

    families = ["modular", "ba", "er"]
    keys = ["no_review", "random", "threshold", "hub", "belief_greedy", "oracle_greedy"]
    agg = {f: {k: [] for k in keys} for f in families}
    meta = {}

    t0 = time.time()
    for fam in families:
        for seed in range(1, N_SEEDS + 1):
            r = run_family(fam, seed)
            for k in keys:
                agg[fam][k].append(r[k])
            meta[fam] = {kk: r[kk] for kk in ("n_err_base", "n_sinks", "n_edges", "max_deg")}
            print(f"  {fam:<8} seed {seed}  no={r['no_review']:3d}  rand={r['random']:3d}  "
                  f"thr={r['threshold']:3d}  hub={r['hub']:3d}  "
                  f"belief={r['belief_greedy']:3d}  oracle={r['oracle_greedy']:3d}  "
                  f"edges={r['n_edges']}  max_deg={r['max_deg']}", flush=True)

    print("\n" + "=" * 72)
    print(f"{'family':<10}" + "".join(f"{k:>12}" for k in keys))
    for fam in families:
        row = "".join(f"{sum(v)/len(v):>12.2f}" for k, v in agg[fam].items())
        print(f"{fam:<10}{row}")
    print(f"\nmeta (last seed): {meta}")
    print(f"elapsed {time.time()-t0:.1f}s")

    # markdown table
    lines = [
        f"N={N}, budget={BUDGET} (10%), λ={LAMBDA}, Zipf s={ZIPF_S}, {N_SEEDS} seeds",
        "",
        "| family | no review | random | conf threshold | hub | belief greedy (deployable) "
        "| oracle greedy (reads truth) |",
        "|---|---|---|---|---|---|---|",
    ]
    for fam in families:
        row = " | ".join(f"{sum(v)/len(v):.2f}" for k, v in agg[fam].items())
        lines.append(f"| {fam} | {row} |")
    with open("scale500_table.md", "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\nwrote scale500_table.md")


if __name__ == "__main__":
    main()
