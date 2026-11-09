#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upgraded method (proposal Section 3): CMDP + PPO-Lagrangian + GNN.

Upgrades over the MLP scorer:
  1. GNN node scorer: one message-passing layer (child -> parent aggregation).
  2. CMDP: the review budget becomes a soft coverage constraint in [d_l, d_u].
  3. PPO-Lagrangian: policy gradient + dual multipliers lambda_u / lambda_l.
  4. Explicit "stop" action so the policy learns when to stop reviewing.
Naive version: the stop-action credit assignment is too coarse and underperforms.
"""
import torch
import torch.nn.functional as F
import math
import random
import spike_active_selection as SP

K = SP.CFG["K"]
N = SP.CFG["N"]
D = K + 2                      # type one-hot(K) + conf + sink_reach_scaled
HIDDEN = 32
D_U = 16                       # 审查上限（20% coverage）
D_L = 8                        # 审查下限（10% coverage）
N_EPISODES = 20000
SEEDS = SP.CFG["seeds"]


def build_env(rng):
    nodes, topo, coins, sinks, sink_reach = SP.build_graph(rng)
    base = [rng.random() < SP.P_TYPE[nodes[i]["type"]] for i in range(N)]
    conf = SP.make_conf(nodes, base, rng)
    F = torch.zeros(N, D)
    for i in range(N):
        F[i, nodes[i]["type"]] = 1.0
        F[i, K] = conf[i]
        F[i, K + 1] = math.log1p(sink_reach[i]) / math.log1p(N)
    # 子→父 归一化邻接（下游特征聚合到上游）
    children = [[] for _ in range(N)]
    for i, nd in enumerate(nodes):
        for p in nd["parents"]:
            children[p].append(i)
    A = torch.zeros(N, N)
    for i in range(N):
        if children[i]:
            for c in children[i]:
                A[i, c] = 1.0 / len(children[i])
    return nodes, topo, coins, sinks, base, F, A


def compute_err(base, nodes, topo, coins):
    err = [False] * N
    for i in topo:
        err[i] = base[i]
        if not err[i]:
            for p in nodes[i]["parents"]:
                if err[p] and coins[(p, i)]:
                    err[i] = True
                    break
    return err


class GNNPolicy(torch.nn.Module):
    def __init__(self, d=D, h=HIDDEN):
        super().__init__()
        self.W_self = torch.nn.Parameter(torch.randn(d, h) * 0.5)
        self.W_neigh = torch.nn.Parameter(torch.randn(d, h) * 0.5)
        self.w = torch.nn.Parameter(torch.randn(h, 1) * 0.5)
        self.b = torch.nn.Parameter(torch.zeros(1))
        self.stop = torch.nn.Parameter(torch.zeros(1))   # stop 动作的 logit

    def score(self, Fmat, A):
        agg = A @ Fmat                            # (N, D) 下游聚合
        h = torch.tanh(Fmat @ self.W_self + agg @ self.W_neigh)   # (N, H)
        return (h @ self.w + self.b).squeeze(-1)   # (N,)


def rollout(policy, nodes, topo, coins, sinks, base, F, A, rng, greedy=False, temp=1.0):
    base_cur = list(base)
    err = compute_err(base_cur, nodes, topo, coins)
    reviewed = [False] * N
    logps = []
    while True:
        s = policy.score(F, A)
        mask = torch.full((N,), float("-inf"))
        for i in range(N):
            if not reviewed[i]:
                mask[i] = 0.0
        scores = torch.cat([s + mask, policy.stop.reshape(1)])   # (N+1,)
        logprobs = torch.log_softmax(scores / temp, dim=0)
        if greedy:
            a = int(torch.argmax(scores).item())
            logps.append(logprobs[a])
        else:
            a = int(torch.multinomial(torch.exp(logprobs), 1).item())
            logps.append(logprobs[a])
        if a == N:      # stop
            break
        reviewed[a] = True
        if err[a] and rng.random() < SP.CFG["p_catch"]:
            base_cur[a] = False
            err = compute_err(base_cur, nodes, topo, coins)
        if sum(reviewed) >= N:
            break
    c = sum(reviewed)
    r = -sum(1 for j in sinks if err[j])
    return r, c, logps


def train():
    policy = GNNPolicy()
    opt = torch.optim.Adam(policy.parameters(), lr=0.003)
    lam_u, lam_l = 0.1, 0.0
    alpha_lam = 0.0008
    baseline = 0.0
    rng = random.Random(1)
    hist = []
    for ep in range(N_EPISODES):
        temp = max(0.3, 2.0 * (0.9995 ** ep))
        nodes, topo, coins, sinks, base, F, A = build_env(rng)
        r, c, logps = rollout(policy, nodes, topo, coins, sinks, base, F, A, rng, temp=temp)
        cost_u = max(0, c - D_U)
        cost_l = max(0, D_L - c)
        G = r - lam_u * cost_u - lam_l * cost_l
        baseline = 0.95 * baseline + 0.05 * G
        adv = G - baseline
        loss = torch.zeros(1)
        for lp in logps:
            loss = loss - adv * lp
        opt.zero_grad(); loss.backward(); opt.step()
        lam_u = min(2.0, max(0.0, lam_u + alpha_lam * cost_u))
        lam_l = min(2.0, max(0.0, lam_l + alpha_lam * cost_l))
        if ep % 1000 == 0:
            hist.append((ep, G, c, lam_u, lam_l))
            print(f"  ep {ep:>6}  G={G:6.2f}  reviews={c:2d}  "
                  f"lam_u={lam_u:.2f} lam_l={lam_l:.2f}")
    return policy, hist


def evaluate(policy, seeds=SEEDS):
    vals = []
    for seed in seeds:
        rng = random.Random(seed)
        nodes, topo, coins, sinks, base, F, A = build_env(rng)
        r, c, _ = rollout(policy, nodes, topo, coins, sinks, base, F, A, rng, greedy=True)
        vals.append(-r)          # sink 错误数
    return sum(vals) / len(vals)


def main():
    print("=" * 70)
    print("CMDP + PPO-Lagrangian + GNN（升级版方法）")
    print("=" * 70)
    print(f"N={N} 预算软约束 coverage∈[{D_L},{D_U}]  GNN(1层消息传递)")
    policy, hist = train()
    err = evaluate(policy)
    print()
    print(f"{'方法':<26}{'sink错误数':>12}")
    print(f"{'置信度阈值(spike)':<26}{2.30:>12.2f}")
    print(f"{'结构贪心(spike)':<26}{1.80:>12.2f}")
    print(f"{'REINFORCE(旧,MLP)':<26}{1.40:>12.2f}")
    print(f"{'PPO(旧,MLP)':<26}{1.60:>12.2f}")
    print(f"{'CMDP+PPO-Lagrangian+GNN(新)':<26}{err:>12.2f}")
    print()
    if err < 1.40:
        print(f"→ 升级版压过旧 REINFORCE {1.40 - err:.2f} 个错误 ✅")
    elif err < 1.60:
        print(f"→ 升级版压过旧 PPO，略逊 REINFORCE")
    else:
        print(f"→ 升级版尚未超过旧版（可能需调参），诚实报告")

if __name__ == "__main__":
    main()
