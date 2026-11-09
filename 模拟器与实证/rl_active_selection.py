#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RL：依赖图上主动选节点审查 —— policy gradient (REINFORCE, 纯 NumPy)

状态（图知识状态）：每节点 [type one-hot, 置信度, 下游 sink 影响数] + 剩余预算
动作：softmax 策略选下一个"待审节点"
奖励：稀疏终端奖励 = −(结论 sink 错误数)
目标：学出节点打分函数，贪心按分选节点，使终端错误最少。

对比（spike 结果）：按置信度阈值 = 2.30；结构贪心(扇出×likelihood) = 1.80。
本脚本看 REINFORCE 学出的打分能否压过 1.80。

RL 知识点：策略梯度、softmax 策略、稀疏延迟奖励、baseline 减方差、MLP 函数近似、温度退火。
"""
import numpy as np
import math
import random
import spike_active_selection as SP

K = SP.CFG["K"]
N = SP.CFG["N"]
R = SP.CFG["budget"]
D = K + 2                       # type one-hot(K) + conf + sink_reach_scaled

HIDDEN = 32
LR = 0.02
N_EPISODES = 20000
SEEDS = SP.CFG["seeds"]


def feats(nodes, conf, sink_reach):
    F = np.zeros((N, D), dtype=np.float32)
    for i in range(N):
        F[i, nodes[i]["type"]] = 1.0
        F[i, K] = conf[i]
        F[i, K + 1] = math.log1p(sink_reach[i]) / math.log1p(N)
    return F


class MLPPolicy:
    def __init__(self):
        rng = np.random.default_rng(0)
        self.W1 = rng.normal(0, 0.5, (HIDDEN, D)).astype(np.float32)
        self.b1 = np.zeros(HIDDEN, dtype=np.float32)
        self.W2 = rng.normal(0, 0.5, (1, HIDDEN)).astype(np.float32)
        self.b2 = np.zeros(1, dtype=np.float32)

    def forward(self, F):                      # F:(N,D) -> s:(N,)
        self.z1 = F @ self.W1.T + self.b1
        self.a1 = np.tanh(self.z1)
        return (self.a1 @ self.W2.T + self.b2).reshape(-1)

    def backward(self, F, g):                  # g = dJ/ds (N,) -> 返回各参数梯度
        g = g.astype(np.float32)
        da1 = g.reshape(N, 1) @ self.W2        # (N,h)
        dz1 = da1 * (1 - self.a1 ** 2)
        gW2 = (g.reshape(1, N) @ self.a1).reshape(1, HIDDEN)
        gb2 = g.sum()
        gW1 = dz1.T @ F
        gb1 = dz1.sum(0)
        return gW1, gb1, gW2, gb2

    def apply_grads(self, grads):
        gW1, gb1, gW2, gb2 = grads
        self.W1 += LR * gW1
        self.b1 += LR * gb1
        self.W2 += LR * gW2
        self.b2 += LR * gb2


def roll_episode(policy, rng, temp, greedy=False):
    nodes, topo, coins, sinks, sink_reach = SP.build_graph(rng)
    base = [rng.random() < SP.P_TYPE[nodes[i]["type"]] for i in range(N)]
    conf = SP.make_conf(nodes, base, rng)
    F = feats(nodes, conf, sink_reach)
    base_cur = list(base)
    err = SP.compute_err(base_cur, nodes, topo, coins)
    reviewed = np.zeros(N, dtype=bool)

    steps = []       # (F, p, a)
    for _ in range(R):
        s = policy.forward(F)
        sm = s.copy()
        sm[reviewed] = -1e9
        sm -= sm.max()
        p = np.exp(sm); p /= p.sum()
        if greedy:
            a = int(np.argmax(p))
        else:
            a = int(np.random.choice(N, p=p))
        steps.append((F, p.copy(), a))
        reviewed[a] = True
        if err[a] and rng.random() < SP.CFG["p_catch"]:
            base_cur[a] = False
            err = SP.compute_err(base_cur, nodes, topo, coins)
    reward = -sum(1 for j in sinks if err[j])
    return reward, steps


def train():
    policy = MLPPolicy()
    baseline = 0.0
    rng = random.Random(1)
    hist = []
    for ep in range(N_EPISODES):
        temp = max(0.3, 2.0 * (0.9993 ** ep))
        reward, steps = roll_episode(policy, rng, temp)
        baseline = 0.95 * baseline + 0.05 * reward
        adv = reward - baseline
        # 累积梯度
        gW1 = np.zeros_like(policy.W1); gb1 = np.zeros_like(policy.b1)
        gW2 = np.zeros_like(policy.W2); gb2 = np.zeros_like(policy.b2)
        for F, p, a in steps:
            oh = np.zeros(N); oh[a] = 1.0
            g = adv * (oh - p)               # dJ/ds，J = adv * log p_a
            policy.forward(F)                # 重算激活用于链式
            dW1, db1, dW2, db2 = policy.backward(F, g)
            gW1 += dW1; gb1 += db1; gW2 += dW2; gb2 += db2
        policy.apply_grads((gW1, gb1, gW2, gb2))
        if ep % 2000 == 0:
            hist.append((ep, reward, baseline))
            print(f"  ep {ep:>6}  reward={reward:6.2f}  baseline={baseline:6.2f}")
    return policy, hist


def evaluate(policy, seeds=SEEDS):
    vals = []
    for seed in seeds:
        rng = random.Random(seed)
        reward, _ = roll_episode(policy, rng, 1.0, greedy=True)
        vals.append(-reward)                 # sink 错误数
    return sum(vals) / len(vals)


def main():
    print("=" * 70)
    print("REINFORCE 主动选节点审查 —— 能否压过结构贪心(1.80)?")
    print("=" * 70)
    policy, hist = train()
    err = evaluate(policy)
    print()
    print(f"{'策略':<28}{'平均sink错误数':>14}")
    print(f"{'按置信度阈值(spike)':<28}{2.30:>14.2f}")
    print(f"{'结构贪心(spike)':<28}{1.80:>14.2f}")
    print(f"{'REINFORCE(本脚本)':<28}{err:>14.2f}")
    print()
    if err < 1.80:
        print(f"→ RL 学出的策略压过结构贪心 {1.80 - err:.2f} 个错误，重构方向成立。")
    else:
        print(f"→ RL 未超过结构贪心（差 {err - 1.80:.2f}），需调参或换算法（PPO/DDQN）。")

if __name__ == "__main__":
    main()
