#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Spike: does active node selection on a dependency graph beat a confidence threshold?

Fixes a bug in the earlier simulator: reviewing a node now recomputes downstream,
so a fixed upstream node stops error propagation. Answers the go/no-go question of
whether graph structure has independent value beyond confidence.
"""
import random
import collections

from belief import ParticleBelief, conf_posterior, sample_conf

CFG = dict(
    N=80, K=5, L=4,
    p_prop=0.6,
    p_catch=0.9,
    budget=16,
    crn=False,   # True: pre-draw one Uniform per node (common random numbers). Changes numbers; rerun all tables.
    seeds=list(range(1, 21)),
    n_particles=1024,      # <512 collapses after a few flags (particle impoverishment)
)
P_TYPE = [0.01, 0.03, 0.08, 0.15, 0.25]


def build_graph(rng):
    N, K, L = CFG["N"], CFG["K"], CFG["L"]
    nodes = []
    per = max(1, N // L)
    for l in range(L):
        for _ in range(per):
            nodes.append({"layer": l, "type": rng.randrange(K), "parents": []})
    nodes = nodes[:N]
    by_layer = collections.defaultdict(list)
    for i, nd in enumerate(nodes):
        by_layer[nd["layer"]].append(i)
    for i, nd in enumerate(nodes):
        if nd["layer"] == 0:
            continue
        cands = by_layer[nd["layer"] - 1]
        np_ = rng.choice([1, 2])
        nd["parents"] = rng.sample(cands, min(np_, len(cands)))
    topo = sorted(range(N), key=lambda i: nodes[i]["layer"])
    # 每条边预采样传播硬币（保证重算一致）
    coins = {}
    for i, nd in enumerate(nodes):
        for p in nd["parents"]:
            coins[(p, i)] = rng.random() < CFG["p_prop"]
    # 下游 sink 可达数（扇出影响）
    sinks = set(i for i, nd in enumerate(nodes) if nd["layer"] == L - 1)
    sink_reach = [0] * N
    # 传递闭包：reach[i] = 从 i 能到的所有节点集合
    reach = [set() for _ in range(N)]
    for i in reversed(topo):
        r = {i}
        # 子节点？反过来：沿 parents 向上累加即可
        for nd in nodes:
            pass
    # 简单：自底向上，reach[i] = {i} ∪ ∪_{child c of i} reach[c]
    children = collections.defaultdict(list)
    for i, nd in enumerate(nodes):
        for p in nd["parents"]:
            children[p].append(i)
    for i in reversed(topo):
        s = {i}
        for c in children[i]:
            s |= reach[c]
        reach[i] = s
    for i in range(N):
        sink_reach[i] = sum(1 for j in reach[i] if j in sinks)
    return nodes, topo, coins, sinks, sink_reach


def compute_err(base, nodes, topo, coins):
    N = len(nodes)
    err = [False] * N
    for i in topo:
        err[i] = base[i]
        if not err[i]:
            for p in nodes[i]["parents"]:
                if err[p] and coins[(p, i)]:
                    err[i] = True
                    break
    return err


def make_conf(nodes, base, rng):
    return [sample_conf(base[i], P_TYPE[nd["type"]], rng) for i, nd in enumerate(nodes)]


def make_belief(nodes, topo, sinks, conf, seed):
    """Deployable belief: structure, edge probabilities, calibrated prior. No truth."""
    parents = [nd["parents"] for nd in nodes]
    edge_prob = {(p, i): CFG["p_prop"] for i, ps in enumerate(parents) for p in ps}
    prior = [conf_posterior(conf[i], P_TYPE[nd["type"]]) for i, nd in enumerate(nodes)]
    return ParticleBelief(parents, topo, sinks, edge_prob, prior, CFG["p_catch"],
                          n_particles=CFG["n_particles"], seed=seed)


def episode_uniforms(rng, n):
    """One Uniform per node, drawn before any review (common random numbers)."""
    return [rng.random() for _ in range(n)]


def review_step(a, base, err, nodes, topo, coins, rng, u=None):
    """Review node a in place. Returns (flagged, err). flagged = reviewer saw an error.

    Semantics: a successful review clears *a's own* (base) error and recomputes
    descendants. Errors inherited from a still-wrong parent are not cleared --
    this is not a do(X_a = 1) intervention. See experiments/SEMANTICS_AUDIT.md.
    """
    draw = u[a] if u is not None else rng.random()
    flagged = err[a] and draw < CFG["p_catch"]
    if flagged:
        base[a] = False
        err = compute_err(base, nodes, topo, coins)
    return flagged, err


def apply_reviews(order, base, nodes, topo, coins, sinks, rng):
    base = list(base)
    err = compute_err(base, nodes, topo, coins)
    u = episode_uniforms(rng, len(nodes)) if CFG["crn"] else None
    for i in order:
        _, err = review_step(i, base, err, nodes, topo, coins, rng, u)
    return sum(1 for i in sinks if err[i])


def run_belief_greedy(belief, base, nodes, topo, coins, sinks, budget, rng):
    """Adaptive greedy on the particle belief; each review outcome updates the belief."""
    base = list(base)
    err = compute_err(base, nodes, topo, coins)
    available = [True] * len(nodes)
    u = episode_uniforms(rng, len(nodes)) if CFG["crn"] else None
    for _ in range(budget):
        a = belief.best_action(available)
        available[a] = False
        flagged, err = review_step(a, base, err, nodes, topo, coins, rng, u)
        belief.observe(a, flagged)
    return sum(1 for i in sinks if err[i])


def run_seed(rng, belief_seed):
    nodes, topo, coins, sinks, sink_reach = build_graph(rng)
    base = [rng.random() < P_TYPE[nodes[i]["type"]] for i in range(CFG["N"])]
    conf = make_conf(nodes, base, rng)
    R = CFG["budget"]

    # 策略1：按置信度阈值（只看 conf，不看图）
    order_conf = sorted(range(CFG["N"]), key=lambda i: conf[i])[:R]

    # 策略2：结构贪心（likely_err × 下游影响）
    score = [(1.0 - conf[i]) * (1 + sink_reach[i]) for i in range(CFG["N"])]
    order_struct = sorted(range(CFG["N"]), key=lambda i: -score[i])[:R]

    # 参考上限：贪心 oracle（读真实错误状态，不可部署；只作天花板）
    base_or = list(base)
    err_or = compute_err(base_or, nodes, topo, coins)
    order_or = []
    b = R
    while b > 0:
        best, bestval = None, None
        for i in range(CFG["N"]):
            if i in order_or:
                continue
            if not err_or[i]:
                continue
            tmp = list(base_or); tmp[i] = False
            e2 = compute_err(tmp, nodes, topo, coins)
            val = sum(1 for j in sinks if e2[j])
            if bestval is None or val < bestval:
                bestval, best = val, i
        if best is None:
            break
        order_or.append(best)
        base_or[best] = False
        err_or = compute_err(base_or, nodes, topo, coins)
        b -= 1

    no_review = sum(1 for j in sinks if compute_err(base, nodes, topo, coins)[j])
    oracle_final = sum(1 for j in sinks if err_or[j])

    res_conf = apply_reviews(order_conf, base, nodes, topo, coins, sinks, rng)
    res_struct = apply_reviews(order_struct, base, nodes, topo, coins, sinks, rng)

    # 策略3：信念贪心（可部署：粒子信念 + 每次审查结果回写信念，不读真实状态）
    belief = make_belief(nodes, topo, sinks, conf, belief_seed)
    res_belief = run_belief_greedy(belief, base, nodes, topo, coins, sinks, R, rng)

    return (no_review, res_conf, res_struct, res_belief, oracle_final)


def main():
    print("=" * 70)
    print("Spike：主动选节点（图结构） vs 按置信度阈值")
    print("=" * 70)
    print(f"N={CFG['N']} K={CFG['K']} 层={CFG['L']} p_prop={CFG['p_prop']} "
          f"预算={CFG['budget']} 类型错误率={P_TYPE}")
    print()
    agg = [0.0] * 5
    for seed in CFG["seeds"]:
        r = run_seed(random.Random(seed), belief_seed=10_000 + seed)
        for k in range(5):
            agg[k] += r[k]
    n = len(CFG["seeds"])
    agg = [a / n for a in agg]
    labels = ["不审", "按置信度阈值", "结构贪心(扇出×likelihood)",
              "信念贪心(自适应,可部署)", "贪心oracle上限(读真值)"]
    print(f"{'策略':<28}{'平均sink错误数':>14}")
    for lab, v in zip(labels, agg):
        print(f"{lab:<28}{v:>14.2f}")
    print()
    gain = agg[1] - agg[2]
    print(f"结构贪心 vs 阈值：{'少' if gain > 0 else '多'} {abs(gain):.2f} 个 sink 错误")
    print(f"信念贪心 vs 结构贪心：{agg[2] - agg[3]:+.2f}（正数 = 信念贪心更少）")
    print(f"oracle 上限 = {agg[4]:.2f}（读真实错误状态，不可部署）")
    print()
    print("判读：结构贪心明显 < 阈值 → 图结构有独立价值 → RL 有东西可学 → 值得重构 + 上 DQN/PPO。")
    print("      否则 → 换题。")

if __name__ == "__main__":
    main()
