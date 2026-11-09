#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RL method comparison: REINFORCE / PPO / DQN with an MLP node scorer,
on the active-node-selection MDP over a dependency graph.
"""
import numpy as np
import math
import random
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import spike_active_selection as SP

K = SP.CFG["K"]
N = SP.CFG["N"]
R = SP.CFG["budget"]
D = K + 2
HIDDEN = 32
SEEDS = SP.CFG["seeds"]

# 基线数字（来自 spike / bandit 脚本，硬编码为参考线）
THRESHOLD = 2.30
STRUCT_GREEDY = 1.80
NO_REVIEW = 5.90
ORACLE = 0.00


def feats(nodes, conf, sink_reach):
    F = np.zeros((N, D), dtype=np.float32)
    for i in range(N):
        F[i, nodes[i]["type"]] = 1.0
        F[i, K] = conf[i]
        F[i, K + 1] = math.log1p(sink_reach[i]) / math.log1p(N)
    return F


def sample_env(rng):
    nodes, topo, coins, sinks, sink_reach = SP.build_graph(rng)
    base = [rng.random() < SP.P_TYPE[nodes[i]["type"]] for i in range(N)]
    conf = SP.make_conf(nodes, base, rng)
    F = feats(nodes, conf, sink_reach)
    return nodes, topo, coins, sinks, sink_reach, base, conf, F


# ============================================================ MLP 打分网络
class MLP:
    def __init__(self, din, seed=0):
        rng = np.random.default_rng(seed)
        self.W1 = rng.normal(0, 0.5, (HIDDEN, din)).astype(np.float32)
        self.b1 = np.zeros(HIDDEN, dtype=np.float32)
        self.W2 = rng.normal(0, 0.5, (1, HIDDEN)).astype(np.float32)
        self.b2 = np.zeros(1, dtype=np.float32)

    def forward(self, X):                       # X:(m,din)->(m,)
        self.z1 = X @ self.W1.T + self.b1
        self.a1 = np.tanh(self.z1)
        return (self.a1 @ self.W2.T + self.b2).reshape(-1)

    def backward(self, X, g):                   # g = dJ/ds (m,) -> 参数梯度
        g = g.astype(np.float32)
        m = X.shape[0]
        da1 = g.reshape(m, 1) @ self.W2
        dz1 = da1 * (1 - self.a1 ** 2)
        gW2 = (g.reshape(1, m) @ self.a1).reshape(1, HIDDEN)
        gb2 = g.sum()
        gW1 = dz1.T @ X
        gb1 = dz1.sum(0)
        return gW1, gb1, gW2, gb2

    def add(self, grads, lr):
        gW1, gb1, gW2, gb2 = grads
        self.W1 += lr * gW1; self.b1 += lr * gb1
        self.W2 += lr * gW2; self.b2 += lr * gb2


# ============================================================ 通用 rollout
def greedy_roll(policy, env, eps=None):
    """greedy（或 eps 探索）rollout，返回 (reward, [steps])，step=(F, p, a)。"""
    nodes, topo, coins, sinks, sink_reach, base, conf, F = env
    base_cur = list(base)
    err = SP.compute_err(base_cur, nodes, topo, coins)
    reviewed = np.zeros(N, dtype=bool)
    steps = []
    for _ in range(R):
        s = policy.forward(F)
        sm = s.copy(); sm[reviewed] = -1e9; sm -= sm.max()
        p = np.exp(sm); p /= p.sum()
        if eps is not None and np.random.random() < eps:
            cand = np.where(~reviewed)[0]
            a = int(np.random.choice(cand))
        else:
            a = int(np.argmax(p))
        steps.append((F, p.copy(), a))
        reviewed[a] = True
        if err[a] and np.random.random() < SP.CFG["p_catch"]:
            base_cur[a] = False
            err = SP.compute_err(base_cur, nodes, topo, coins)
    reward = -sum(1 for j in sinks if err[j])
    return reward, steps


def evaluate(policy, seeds=SEEDS):
    vals = []
    for seed in seeds:
        env = sample_env(random.Random(seed))
        r, _ = greedy_roll(policy, env)
        vals.append(-r)
    return sum(vals) / len(vals)


# ============================================================ REINFORCE
def train_reinforce(n_ep=20000, lr=0.02):
    policy = MLP(D, seed=0)
    baseline = 0.0
    rng = random.Random(1)
    hist = []
    for ep in range(n_ep):
        temp = max(0.3, 2.0 * (0.9993 ** ep))
        env = sample_env(rng)
        nodes, topo, coins, sinks, sink_reach, base, conf, F = env
        base_cur = list(base)
        err = SP.compute_err(base_cur, nodes, topo, coins)
        reviewed = np.zeros(N, dtype=bool)
        steps = []
        for _ in range(R):
            s = policy.forward(F)
            sm = s.copy(); sm[reviewed] = -1e9; sm -= sm.max()
            p = np.exp(sm); p /= p.sum()
            a = int(np.random.choice(N, p=p))
            steps.append((F, p.copy(), a))
            reviewed[a] = True
            if err[a] and rng.random() < SP.CFG["p_catch"]:
                base_cur[a] = False
                err = SP.compute_err(base_cur, nodes, topo, coins)
        reward = -sum(1 for j in sinks if err[j])
        baseline = 0.95 * baseline + 0.05 * reward
        adv = reward - baseline
        gW1 = np.zeros_like(policy.W1); gb1 = np.zeros_like(policy.b1)
        gW2 = np.zeros_like(policy.W2); gb2 = np.zeros_like(policy.b2)
        for F, p, a in steps:
            oh = np.zeros(N); oh[a] = 1.0
            g = adv * (oh - p)
            policy.forward(F)
            d = policy.backward(F, g)
            gW1 += d[0]; gb1 += d[1]; gW2 += d[2]; gb2 += d[3]
        policy.add((gW1, gb1, gW2, gb2), lr)
        if ep % 500 == 0:
            hist.append((ep, baseline))
    return policy, hist


# ============================================================ PPO（clipped）
def train_ppo(n_ep=20000, lr=0.01, clip=0.2, epochs=4):
    policy = MLP(D, seed=0)
    baseline = 0.0
    rng = random.Random(1)
    hist = []
    for ep in range(n_ep):
        temp = max(0.3, 2.0 * (0.9993 ** ep))
        env = sample_env(rng)
        nodes, topo, coins, sinks, sink_reach, base, conf, F = env
        base_cur = list(base)
        err = SP.compute_err(base_cur, nodes, topo, coins)
        reviewed = np.zeros(N, dtype=bool)
        steps = []          # (F, mask, a, logp_old)
        for _ in range(R):
            s = policy.forward(F)
            sm = s.copy(); sm[reviewed] = -1e9; sm -= sm.max()
            p = np.exp(sm); p /= p.sum()
            a = int(np.random.choice(N, p=p))
            steps.append((F, reviewed.copy(), a, math.log(p[a] + 1e-12)))
            reviewed[a] = True
            if err[a] and rng.random() < SP.CFG["p_catch"]:
                base_cur[a] = False
                err = SP.compute_err(base_cur, nodes, topo, coins)
        reward = -sum(1 for j in sinks if err[j])
        baseline = 0.95 * baseline + 0.05 * reward
        A = reward - baseline
        # PPO：多 epoch 带裁剪的更新（重要性采样）
        for _ in range(epochs):
            gW1 = np.zeros_like(policy.W1); gb1 = np.zeros_like(policy.b1)
            gW2 = np.zeros_like(policy.W2); gb2 = np.zeros_like(policy.b2)
            for F, mask, a, logp_old in steps:
                s = policy.forward(F)
                sm = s.copy(); sm[mask] = -1e9; sm -= sm.max()
                p = np.exp(sm); p /= p.sum()
                logp_new = math.log(p[a] + 1e-12)
                ratio = math.exp(min(logp_new - logp_old, 10.0))
                rclip = min(max(ratio, 1 - clip), 1 + clip)
                # J = min(ratio, rclip) * A ；dJ/ds = dJ/dlogp_new * (onehot - p)
                if A >= 0:
                    coef = A if ratio <= rclip else 0.0
                else:
                    coef = A if ratio >= rclip else 0.0
                oh = np.zeros(N); oh[a] = 1.0
                g = coef * (oh - p)
                d = policy.backward(F, g)
                gW1 += d[0]; gb1 += d[1]; gW2 += d[2]; gb2 += d[3]
            policy.add((gW1, gb1, gW2, gb2), lr)
        if ep % 500 == 0:
            hist.append((ep, baseline))
    return policy, hist


# ============================================================ DQN（值函数 + 目标网络 + replay）
def train_dqn(n_ep=20000, lr=0.005, gamma=0.98, buffer_cap=20000, target_every=200):
    qnet = MLP(2 + D, seed=2)
    target = MLP(2 + D, seed=2)
    # 复制参数
    def copy(src, dst):
        dst.W1 = src.W1.copy(); dst.b1 = src.b1.copy()
        dst.W2 = src.W2.copy(); dst.b2 = src.b2.copy()
    copy(qnet, target)
    replay = []
    rng = random.Random(1)
    hist = []
    eps = 1.0
    for ep in range(n_ep):
        env = sample_env(rng)
        nodes, topo, coins, sinks, sink_reach, base, conf, F = env
        base_cur = list(base)
        err = SP.compute_err(base_cur, nodes, topo, coins)
        reviewed = np.zeros(N, dtype=bool)
        budget = R
        traj = []          # (ctx_t, F_a, next_ctx_t, terminal?, reward)
        for _ in range(R):
            ctx = np.array([budget / R, reviewed.sum() / N], dtype=np.float32)
            X = np.concatenate([np.tile(ctx, (N, 1)), F], axis=1).astype(np.float32)
            q = qnet.forward(X)
            qm = q.copy(); qm[reviewed] = -1e9
            if np.random.random() < eps:
                cand = np.where(~reviewed)[0]
                a = int(np.random.choice(cand))
            else:
                a = int(np.argmax(qm))
            traj.append((ctx, F[a].copy(), a))
            reviewed[a] = True
            budget -= 1
            if err[a] and rng.random() < SP.CFG["p_catch"]:
                base_cur[a] = False
                err = SP.compute_err(base_cur, nodes, topo, coins)
        terminal = -sum(1 for j in sinks if err[j])
        # 构造目标：从最后一步回推
        for t in range(R - 1, -1, -1):
            ctx, Fa, a = traj[t]
            if t == R - 1:
                y = terminal
            else:
                next_ctx, next_Fa, next_a = traj[t + 1]
                # 下一状态 max Q（用目标网络在 next ctx 下对所有未审节点）
                # 简化：用当前下一 ctx 计算目标网络 max（这里 next 状态已知 ctx）
                # 存 replay 时只存 (ctx, Fa, y)，由 buffer 随机采样训练
                # 为简化：直接用 terminal 的折扣回传（等价 MC）
                y = gamma ** (R - 1 - t) * terminal
            replay.append((ctx, Fa, y))
        if len(replay) > buffer_cap:
            replay = replay[-buffer_cap:]
        # 训练
        if len(replay) >= 256:
            batch = random.sample(replay, 256)
            gW1 = np.zeros_like(qnet.W1); gb1 = np.zeros_like(qnet.b1)
            gW2 = np.zeros_like(qnet.W2); gb2 = np.zeros_like(qnet.b2)
            for ctx, Fa, y in batch:
                X1 = np.concatenate([ctx[None, :], Fa[None, :]], axis=1).astype(np.float32)
                pred = qnet.forward(X1)[0]
                err_g = (pred - y)   # dMSE/dpred = pred - y
                d = qnet.backward(X1, np.array([err_g], dtype=np.float32))
                gW1 += d[0]; gb1 += d[1]; gW2 += d[2]; gb2 += d[3]
            qnet.add((gW1 / 256, gb1 / 256, gW2 / 256, gb2 / 256), lr)
        if ep % target_every == 0:
            copy(qnet, target)
        eps = max(0.05, eps * 0.999)
        if ep % 500 == 0:
            hist.append((ep, terminal))
    return qnet, hist


def dqn_policy(qnet):
    def f(env):
        nodes, topo, coins, sinks, sink_reach, base, conf, F = env
        base_cur = list(base)
        err = SP.compute_err(base_cur, nodes, topo, coins)
        reviewed = np.zeros(N, dtype=bool)
        budget = R
        for _ in range(R):
            ctx = np.array([budget / R, reviewed.sum() / N], dtype=np.float32)
            X = np.concatenate([np.tile(ctx, (N, 1)), F], axis=1).astype(np.float32)
            q = qnet.forward(X)
            qm = q.copy(); qm[reviewed] = -1e9
            a = int(np.argmax(qm))
            reviewed[a] = True; budget -= 1
            if err[a] and np.random.random() < SP.CFG["p_catch"]:
                base_cur[a] = False
                err = SP.compute_err(base_cur, nodes, topo, coins)
        return sum(1 for j in sinks if err[j])   # 返回 sink 错误数（非负）
    return f


def evaluate_dqn(f, seeds=SEEDS):
    vals = [f(sample_env(random.Random(seed))) for seed in seeds]
    return sum(vals) / len(vals)


def plot(curves, results, outdir):
    # 学习曲线
    plt.figure(figsize=(7, 4.5))
    for name, hist in curves.items():
        xs = [x for x, _ in hist]
        ys = [y for _, y in hist]
        plt.plot(xs, ys, label=name, linewidth=1.5)
    plt.xlabel("episode"); plt.ylabel("baseline reward (higher=better)")
    plt.title("Learning curves (active node selection on dependency graph)")
    plt.legend(); plt.grid(alpha=0.3); plt.tight_layout()
    plt.savefig(f"{outdir}/learning_curves.png", dpi=130)
    plt.close()

    # 结果柱状图
    names = list(results.keys())
    vals = list(results.values())
    plt.figure(figsize=(8, 4.5))
    colors = ["#888888" if n in ("No review", "Conf threshold", "Structural greedy", "Oracle")
              else "#2a7de1" for n in names]
    bars = plt.bar(names, vals, color=colors)
    for b, v in zip(bars, vals):
        plt.text(b.get_x() + b.get_width() / 2, v + 0.08, f"{v:.2f}",
                 ha="center", va="bottom", fontsize=8)
    plt.ylabel("avg sink errors (lower=better)"); plt.title("Review scheduling: method comparison")
    plt.xticks(rotation=15, ha="right"); plt.tight_layout()
    plt.savefig(f"{outdir}/results_bar.png", dpi=130)
    plt.close()


def main():
    import os
    outdir = os.path.dirname(os.path.abspath(__file__))

    print("训练 REINFORCE ...")
    pr, hr = train_reinforce()
    print("训练 PPO ...")
    pp, hp = train_ppo()
    print("训练 DQN ...")
    q, hq = train_dqn()

    ev_pr = evaluate(pr)
    ev_pp = evaluate(pp)
    ev_dq = evaluate_dqn(dqn_policy(q))

    results = {
        "No review": NO_REVIEW,
        "Conf threshold": THRESHOLD,
        "Structural greedy": STRUCT_GREEDY,
        "REINFORCE": ev_pr,
        "PPO": ev_pp,
        "DQN": ev_dq,
        "Oracle": ORACLE,
    }
    print("\n" + "=" * 60)
    print("方法对比（平均 sink 错误数，越低越好）")
    print("=" * 60)
    for k, v in results.items():
        print(f"  {k:<20}{v:.2f}")

    plot({"REINFORCE": hr, "PPO": hp, "DQN": hq}, results, outdir)
    print("\n已导出：learning_curves.png, results_bar.png")
    print("（DQN 目标为折扣 MC 回传，非标准 TD 目标网络——见代码注释）")


if __name__ == "__main__":
    main()
