#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖图传播审查调度模拟器 —— 把"结尾惩罚"弱代理换成真结构。

模型（对应文档 §2 两个事实）：
  事实一 错误按类型聚集：每种 type 有独立基础出错率 p_type[t]（少数类型高错误率）。
  事实二 错误沿依赖图往下游传播：条目间是 DAG 依赖，上游错误以概率 p_prop 传到
         下游；未审查的错误"在结论（sink）处才暴露"。
  目标：在固定审查预算下，让到达 sink 的错误最少。

策略（对应文档 §3 的对比 + 批评要求的"按类型校准阈值"基线）：
  ReviewNone        完全不审查
  Random            随机审 R 个
  ThresholdPerType  按类型分别校准置信度阈值（BestReject 式，只用 type+conf，看不到图）
  LearnedQ          tabular Q-learning，状态含 (type, conf, budget, 下游后代数)，
                    学到"审上游高后代节点"以吃到延迟终端奖励
  (上限) 无预算全审  审查所有条目（p_catch<1 仍有残余），天花板参考

防"模拟器自证"的两个对照：
  - shuffle_errors（打乱错误，破坏类型聚集）→ 学习策略优势应消失
  - flatten（摊平依赖图，破坏传播）        → 学习策略相对阈值的优势应消失
"""
import math
import random
import collections

# ---------------------------------------------------------------- 配置
CFG = dict(
    N=80, K=5, L=4,                  # 条目数 / 类型数 / 层数
    p_prop=0.6,                       # 上游错误向下游传播的概率
    p_catch=0.9,                      # 审查者发现并修正错误的概率
    review_cost=0.05,                 # 每次审查的小额成本
    budget=16,                        # 审查预算（20%）
    n_episodes=12000,                 # Q-learning 训练 episode 数
    conf_bins=8,                      # 置信度分箱数（敏感性：粗分箱会削弱学习策略）
    seeds=list(range(1, 17)),
)

# 类型级出错率：强聚集（猫狗混淆式），整体偏低让传播主导 sink 错误
P_TYPE = [0.01, 0.03, 0.08, 0.15, 0.25]


# ---------------------------------------------------------------- 数据生成
def build_graph(rng, flatten=False):
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
    descendants = [0] * N
    for i in reversed(topo):
        for p in nodes[i]["parents"]:
            descendants[p] += 1 + descendants[i]
    if flatten:
        for nd in nodes:
            nd["parents"] = []
        descendants = [0] * N
    return nodes, topo, descendants


def sample_errors(nodes, topo, rng, shuffle_errors=False):
    N = len(nodes)
    base = [rng.random() < P_TYPE[nodes[i]["type"]] for i in range(N)]
    if shuffle_errors:
        rng.shuffle(base)  # 破坏类型聚集（错误数不变，但不再与 type 相关）
    err = [False] * N
    for i in topo:
        err[i] = base[i]
        if not err[i]:
            for p in nodes[i]["parents"]:
                if err[p] and rng.random() < CFG["p_prop"]:
                    err[i] = True
                    break
    return err


def make_conf(nodes, err, rng):
    conf = []
    for i, nd in enumerate(nodes):
        signal = -1.5 if err[i] else 1.5
        signal -= 0.4 * (P_TYPE[nd["type"]] - 0.15)
        logit = signal + rng.gauss(0, 1.2)
        conf.append(1.0 / (1.0 + math.exp(-logit)))
    return conf


# ---------------------------------------------------------------- 审查过程
def sink_error(nodes, err):
    sinks = set(i for i, nd in enumerate(nodes) if nd["layer"] == CFG["L"] - 1)
    return sum(1 for i in sinks if err[i])


def run_policy(nodes, topo, err, conf, decide, rng):
    err = list(err)
    budget = CFG["budget"]
    for i in topo:
        if budget > 0 and decide(i):
            budget -= 1
            if err[i] and rng.random() < CFG["p_catch"]:
                err[i] = False
    return sink_error(nodes, err)


def review_all_upper(nodes, topo, err, rng):
    err = list(err)
    for i in topo:
        if err[i] and rng.random() < CFG["p_catch"]:
            err[i] = False
    return sink_error(nodes, err)


# ---------------------------------------------------------------- 策略
def policy_review_none(i): return False


def make_random_policy(rng):
    review_set = set(rng.sample(range(CFG["N"]), CFG["budget"]))
    return lambda i: i in review_set


def calibrate_thresholds(nodes, err, conf, rng):
    """BestReject 式：per-type 置信度阈值，验证集校准到预算，只用 (type, conf)。"""
    N = len(nodes)
    val = set(rng.sample(range(N), int(N * 0.4)))
    thr = {}
    for t in range(CFG["K"]):
        errs = sorted([conf[i] for i in val if nodes[i]["type"] == t and err[i]])
        thr[t] = errs[len(errs) // 2] if errs else 0.0
    lo, hi = 0.0, 2.0
    for _ in range(50):
        mid = (lo + hi) / 2
        c = sum(1 for i in val if conf[i] < thr[nodes[i]["type"]] * mid)
        if c > CFG["budget"] * 0.4:
            hi = mid
        else:
            lo = mid
    scale = (lo + hi) / 2
    thr = {t: v * scale for t, v in thr.items()}
    return lambda i: conf[i] < thr[nodes[i]["type"]]


# ---- Q-learning ----
def _conf_bin(c): return min(CFG["conf_bins"] - 1, int(c * CFG["conf_bins"]))
def _budget_bin(b): return min(4, b // 3)
def _desc_bin(d): return 0 if d == 0 else (1 if d <= 3 else 2)


def train_q(rng):
    Q = collections.defaultdict(float)
    alpha, gamma = 0.15, 0.97
    eps = 1.0
    for _ in range(CFG["n_episodes"]):
        nodes, topo, desc = build_graph(rng)
        err = sample_errors(nodes, topo, rng)
        conf = make_conf(nodes, err, rng)
        err_c = list(err)
        budget = CFG["budget"]
        traj = []
        for i in topo:
            s = (nodes[i]["type"], _conf_bin(conf[i]), _budget_bin(budget), _desc_bin(desc[i]))
            acts = [0, 1] if budget > 0 else [0]
            if rng.random() < eps:
                a = rng.choice(acts)
            else:
                a = 1 if (1 in acts and Q[(s, 1)] > Q[(s, 0)]) else 0
            traj.append((s, a))
            if a == 1:
                budget -= 1
                if err_c[i] and rng.random() < CFG["p_catch"]:
                    err_c[i] = False
        terminal = -sink_error(nodes, err_c)
        for t in range(len(traj) - 1, -1, -1):
            s, a = traj[t]
            r = -CFG["review_cost"] if a == 1 else 0.0
            nxt = traj[t + 1][0] if t + 1 < len(traj) else None
            nxt_max = max(Q[(nxt, 0)], Q[(nxt, 1)]) if nxt is not None else terminal
            Q[(s, a)] += alpha * (r + gamma * nxt_max - Q[(s, a)])
        eps = max(0.05, eps * 0.998)
    return Q


def make_q_policy(Q, nodes, conf, desc):
    budget_left = [CFG["budget"]]
    def f(i):
        b = budget_left[0]
        if b <= 0:
            return False
        s = (nodes[i]["type"], _conf_bin(conf[i]), _budget_bin(b), _desc_bin(desc[i]))
        a = 1 if Q[(s, 1)] > Q[(s, 0)] else 0
        if a == 1:
            budget_left[0] -= 1
        return a == 1
    return f


# ---------------------------------------------------------------- 主实验
def evaluate(decide_maker, seeds, shuffle_errors=False, flatten=False):
    totals = []
    for seed in seeds:
        rng = random.Random(seed)
        nodes, topo, desc = build_graph(rng, flatten=flatten)
        err = sample_errors(nodes, topo, rng, shuffle_errors=shuffle_errors)
        conf = make_conf(nodes, err, rng)
        decide = decide_maker(nodes, err, conf, desc, rng)
        totals.append(run_policy(nodes, topo, err, conf, decide, rng))
    return sum(totals) / len(totals)


def upper_bound(seeds):
    vals = []
    for seed in seeds:
        rng = random.Random(seed)
        nodes, topo, _ = build_graph(rng)
        err = sample_errors(nodes, topo, rng)
        vals.append(review_all_upper(nodes, topo, err, rng))
    return sum(vals) / len(vals)


def main():
    print("=" * 74)
    print("依赖图传播审查调度 —— 学习策略 vs 按类型校准阈值")
    print("=" * 74)
    print(f"配置: N={CFG['N']} K={CFG['K']} 层={CFG['L']} p_prop={CFG['p_prop']} "
          f"预算={CFG['budget']} 类型错误率={P_TYPE}")
    print()

    seeds = CFG["seeds"]
    Q = train_q(random.Random(0))

    makers = {
        "ReviewNone": lambda n, e, c, d, r: policy_review_none,
        "Random": lambda n, e, c, d, r: make_random_policy(r),
        "ThresholdPerType": lambda n, e, c, d, r: calibrate_thresholds(n, e, c, r),
        "LearnedQ": lambda n, e, c, d, r: make_q_policy(Q, n, c, d),
    }

    print("[主实验] 正常结构（聚集 + 传播都开）")
    print(f"{'策略':<18}{'平均sink错误数':>16}")
    results = {}
    for name, mk in makers.items():
        v = evaluate(mk, seeds)
        results[name] = v
        print(f"{name:<18}{v:>16.2f}")
    print(f"{'(上限)无预算全审':<18}{upper_bound(seeds):>16.2f}")
    print()
    gap0 = results["ThresholdPerType"] - results["LearnedQ"]
    print(f"  → 学习策略比阈值策略{'少' if gap0 > 0 else '多'} {abs(gap0):.2f} 个 sink 错误")

    print("\n[对照1] 打乱错误（破坏类型聚集）")
    r1 = {}
    for name in ["ThresholdPerType", "LearnedQ"]:
        r1[name] = evaluate(makers[name], seeds, shuffle_errors=True)
        print(f"  {name:<18}{r1[name]:>16.2f}")
    gap1 = r1["ThresholdPerType"] - r1["LearnedQ"]
    print(f"  → 学习策略优势 = {gap1:.2f}（正常结构 = {gap0:.2f}）")

    print("\n[对照2] 摊平依赖图（破坏传播）")
    r2 = {}
    for name in ["ThresholdPerType", "LearnedQ"]:
        r2[name] = evaluate(makers[name], seeds, flatten=True)
        print(f"  {name:<18}{r2[name]:>16.2f}")
    gap2 = r2["ThresholdPerType"] - r2["LearnedQ"]
    print(f"  → 学习策略优势 = {gap2:.2f}（正常结构 = {gap0:.2f}）")

    print("\n[敏感性] 学习策略对置信度分箱粒度的依赖（阈值基线固定不变）")
    thr_main = results["ThresholdPerType"]
    for cb in [4, 8, 16]:
        CFG["conf_bins"] = cb
        Q2 = train_q(random.Random(0))
        def _mk(n, e, c, d, r, _Q=Q2):
            return make_q_policy(_Q, n, c, d)
        v = evaluate(_mk, seeds)
        print(f"  conf_bins={cb:<3} LearnedQ={v:.2f}  (阈值={thr_main:.2f}, 学习优势={thr_main-v:+.2f})")
    CFG["conf_bins"] = 8

    print("\n" + "=" * 74)
    print("判读：")
    print("  若学习策略在正常结构下优于阈值，且对照1/对照2 下优势明显缩小，")
    print("  说明优势来自聚集+传播结构本身，而非模拟器里硬写的'学习必胜'。")
    print("  若任何条件下学习都不优于阈值 —— 这本身也是诚实结论（批评原文要求的）。")
    print("=" * 74)


if __name__ == "__main__":
    main()
