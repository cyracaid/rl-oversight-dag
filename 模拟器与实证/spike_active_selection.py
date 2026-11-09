#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spike：依赖图上"主动选节点审查"能否赢过"按置信度阈值"？

修复了原模拟器的 bug：原版审查一个节点后只把 err[i] 设 False，没有重算下游，
导致"修正上游阻断下游传播"没生效。这里改成：
  - base[i] = 节点自身错误（按类型聚集）
  - 每条边 (p->i) 预采样一个传播硬币 coins[(p,i)]
  - err = compute_err(base)：err[i] = base[i] OR (任一父 p 且 coins 为真)
  - 审查节点 i：若 err[i] 且抓到(p_catch)，令 base[i]=False，然后**重算 err**（下游自动解除）

问题（生死判据）：主动选节点（用图结构）能否赢过"按置信度阈值"？
  - 关键假设：审"扇出大（下游 sink 多）的上游节点"比审"低置信度但无下游的节点"更值。
"""
import random
import collections
import math

CFG = dict(
    N=80, K=5, L=4,
    p_prop=0.6,
    p_catch=0.9,
    budget=16,
    seeds=list(range(1, 21)),
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
    conf = []
    for i, nd in enumerate(nodes):
        signal = -1.5 if base[i] else 1.5
        signal -= 0.4 * (P_TYPE[nd["type"]] - 0.15)
        logit = signal + rng.gauss(0, 1.2)
        conf.append(1.0 / (1.0 + math.exp(-logit)))
    return conf


def apply_reviews(order, base, nodes, topo, coins, sinks, rng):
    base = list(base)
    err = compute_err(base, nodes, topo, coins)
    for i in order:
        if err[i] and rng.random() < CFG["p_catch"]:
            base[i] = False
            err = compute_err(base, nodes, topo, coins)
    return sum(1 for i in sinks if err[i])


def run_seed(rng):
    nodes, topo, coins, sinks, sink_reach = build_graph(rng)
    base = [rng.random() < P_TYPE[nodes[i]["type"]] for i in range(CFG["N"])]
    conf = make_conf(nodes, base, rng)
    R = CFG["budget"]

    # 策略1：按置信度阈值（只看 conf，不看图）
    order_conf = sorted(range(CFG["N"]), key=lambda i: conf[i])[:R]

    # 策略2：结构贪心（likely_err × 下游影响）
    score = [(1.0 - conf[i]) * (1 + sink_reach[i]) for i in range(CFG["N"])]
    order_struct = sorted(range(CFG["N"]), key=lambda i: -score[i])[:R]

    # 参考上限：贪心 oracle（每步选当下能最大减少 sink 错误的节点）
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

    return (no_review,
            apply_reviews(order_conf, base, nodes, topo, coins, sinks, rng),
            apply_reviews(order_struct, base, nodes, topo, coins, sinks, rng),
            oracle_final)


def main():
    print("=" * 70)
    print("Spike：主动选节点（图结构） vs 按置信度阈值")
    print("=" * 70)
    print(f"N={CFG['N']} K={CFG['K']} 层={CFG['L']} p_prop={CFG['p_prop']} "
          f"预算={CFG['budget']} 类型错误率={P_TYPE}")
    print()
    agg = [0.0] * 4
    for seed in CFG["seeds"]:
        r = run_seed(random.Random(seed))
        for k in range(4):
            agg[k] += r[k]
    n = len(CFG["seeds"])
    agg = [a / n for a in agg]
    labels = ["不审", "按置信度阈值", "结构贪心(扇出×likelihood)", "贪心oracle上限"]
    print(f"{'策略':<28}{'平均sink错误数':>14}")
    for lab, v in zip(labels, agg):
        print(f"{lab:<28}{v:>14.2f}")
    print()
    gain = agg[1] - agg[2]
    print(f"结构贪心 vs 阈值：{'少' if gain > 0 else '多'} {abs(gain):.2f} 个 sink 错误")
    print(f"oracle 上限 = {agg[3]:.2f}（结构贪心离它 {'还有空间' if agg[2] > agg[3] + 0.5 else '已接近'}）")
    print()
    print("判读：结构贪心明显 < 阈值 → 图结构有独立价值 → RL 有东西可学 → 值得重构 + 上 DQN/PPO。")
    print("      否则 → 换题。")

if __name__ == "__main__":
    main()
