#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Real-data check: do errors cluster by type?

Uses the internal sleep-research error-correction records. Skips automatically
when the local data file is missing (Core Principle 3).
"""
import csv
import collections
import math
import os
import random

BASE = os.path.expanduser("~/Documents/splsleep")

def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def dist_of(rows, key):
    c = collections.Counter()
    for r in rows:
        v = (r.get(key) or "").strip()
        if v:
            c[v] += 1
    return c

def chi2_from_counts(counts):
    if hasattr(counts, "values"):
        vals = list(counts.values())
    else:
        vals = list(counts)
    n = sum(vals)
    if n == 0 or len(vals) == 0:
        return 0.0
    mean = n / len(vals)
    return sum((v - mean) ** 2 / mean for v in vals)

def monte_carlo_p(counts, nsim=30000, seed=7):
    """H0: n items uniformly distributed over k categories. Returns p."""
    vals = list(counts.values())
    n = sum(vals)
    k = len(vals)
    if n == 0 or k == 0:
        return 1.0
    obs = chi2_from_counts(counts)
    rng = random.Random(seed)
    cnt = 0
    for _ in range(nsim):
        sim = [0] * k
        for _ in range(n):
            sim[rng.randrange(k)] += 1
        if chi2_from_counts(sim) >= obs:
            cnt += 1
    return (cnt + 1) / (nsim + 1)

def concentration(counts):
    n = sum(counts.values())
    if n == 0:
        return {}
    ranked = counts.most_common()
    top1 = ranked[0][1] / n
    top2 = sum(v for _, v in ranked[:2]) / n
    ent = -sum((v / n) * math.log(v / n) for v in counts.values())
    return {
        "n": n,
        "n_categories": len(counts),
        "top1_share": round(top1, 3),
        "top2_share": round(top2, 3),
        "entropy": round(ent, 3),
        "top3": [(k, v) for k, v in ranked[:3]],
    }

def contingency_chi2_and_pc(table, nsim=30000, seed=7):
    """table: list of (row_cat, col_cat). Test independence."""
    rows = collections.Counter(r for r, _ in table)
    cols = collections.Counter(c for _, c in table)
    n = len(table)
    cells = collections.Counter(table)
    obs = 0.0
    for (r, c), o in cells.items():
        e = rows[r] * cols[c] / n
        if e > 0:
            obs += (o - e) ** 2 / e
    # permutation: shuffle col labels
    rng = random.Random(seed)
    row_list = [r for r, _ in table]
    col_list = [c for _, c in table]
    cnt = 0
    for _ in range(nsim):
        rng.shuffle(col_list)
        t2 = list(zip(row_list, col_list))
        r2 = collections.Counter(r for r, _ in t2)
        c2 = collections.Counter(c for _, c in t2)
        cells2 = collections.Counter(t2)
        s = 0.0
        for (r, c), o in cells2.items():
            e = r2[r] * c2[c] / n
            if e > 0:
                s += (o - e) ** 2 / e
        if s >= obs:
            cnt += 1
    return obs, (cnt + 1) / (nsim + 1)

def main():
    print("=" * 70)
    print("真实数据聚集验证 —— splsleep 睡眠问卷人工纠错")
    print("=" * 70)

    # ---- 1. 错误类型聚集 ----
    f1 = os.path.join(BASE, "manual_error_correction_updated.csv")
    if os.path.exists(f1):
        rows = load_csv(f1)
        print(f"\n[1] manual_error_correction_updated.csv  (n={len(rows)})")
        for key, label in [("error_type", "error_type"), ("correction_type", "correction_type")]:
            d = dist_of(rows, key)
            c = concentration(d)
            p = monte_carlo_p(d)
            print(f"\n  {label}:")
            print(f"    类别数={c['n_categories']}  top1占比={c['top1_share']}  "
                  f"top2占比={c['top2_share']}  熵={c['entropy']}")
            print(f"    蒙特卡洛 p(H0=均匀分布) = {p:.4f}")
            print(f"    前3类: {c['top3']}")
    else:
        print(f"[1] 缺文件: {f1}")

    # ---- 2. 字段 × disposition 独立性 ----
    f2 = os.path.join(BASE, "audit_dispositions.csv")
    if os.path.exists(f2):
        rows = load_csv(f2)
        print(f"\n[2] audit_dispositions.csv  (n={len(rows)})")
        table = [(r.get("field", "").strip(), r.get("disposition", "").strip())
                 for r in rows if r.get("field") and r.get("disposition")]
        obs, p = contingency_chi2_and_pc(table)
        print(f"  field × disposition 列联表:")
        cross = collections.Counter(table)
        fields = sorted({f for f, _ in table})
        disps = sorted({d for _, d in table})
        print("      " + " ".join(f"{d:>8}" for d in disps))
        for f in fields:
            print(f"    {f:<6}" + " ".join(f"{cross[(f,d)]:>8}" for d in disps))
        print(f"  卡方统计量 = {obs:.2f}  蒙特卡洛 p(独立) = {p:.4f}")
        if p < 0.05:
            print("  → disposition 随字段显著变化：错误率按字段/类型聚集的证据成立")
        else:
            print("  → 未达显著（样本太小），方向性证据弱")
    else:
        print(f"[2] 缺文件: {f2}")

    print("\n" + "=" * 70)
    print("说明：样本 <100 行，仅方向性证据。要强结论需全量数据集 + 每行 type×error 标注。")
    print("=" * 70)

if __name__ == "__main__":
    main()
