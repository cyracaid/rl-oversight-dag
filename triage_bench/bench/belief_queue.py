"""Belief greedy on the real queue, inside the M4-only block.

The synthetic result says a deployable belief policy beats a learned one. The
real queue has no graph, but it does have a hierarchy: rows sit inside
participants. So the belief here is a Beta posterior over each participant's
error rate, and reviewing a row is an observation that updates it.

Protocol (simulated deployment, not offline policy evaluation):
    - a review reveals the row's verdict, exactly as a curator would learn it;
    - the policy never sees the verdict of an unreviewed row;
    - the prior comes from the participant's M1 density, estimated without that
      participant (leave-one-participant-out), so no label leaks forward.

If this cannot beat the 1.24% base rate inside M4-only, then the block is
information-dead for *any* adaptive policy, not just for the feature model.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import SEED
from .mine_m4 import build_features


def lopo_prior(queue: pd.DataFrame, feats: pd.DataFrame, n_bins: int = 5,
               kappa: float = 10.0) -> pd.Series:
    """Smoothed error-rate prior per participant, from M1 density, excluding itself."""
    block = queue.loc[queue["m4"] & ~queue["m1"]]
    density = feats["m1_density"].reindex(block["pid"].unique())
    bins = pd.qcut(density, n_bins, duplicates="drop", labels=False)

    per_pid = block.groupby("pid")["y_broad"].agg(["size", "sum"])
    per_pid["bin"] = bins.reindex(per_pid.index)

    prior = pd.Series(index=per_pid.index, dtype=float)
    global_rate = per_pid["sum"].sum() / per_pid["size"].sum()
    for pid, row in per_pid.iterrows():
        same = per_pid.loc[(per_pid["bin"] == row["bin"]) & (per_pid.index != pid)]
        n = same["size"].sum() - 0
        e = same["sum"].sum()
        prior[pid] = (e + kappa * global_rate) / (n + kappa)
    return prior


def simulate(block: pd.DataFrame, prior: pd.Series, kappa: float,
             budget: int, adaptive: bool = True) -> list[int]:
    """Review order (positional indices into block).

    adaptive=False ranks by the fixed prior; True updates a Beta posterior after
    each revealed verdict. Ties break toward the earliest queue position.
    """
    alpha = (prior * kappa).to_dict()
    beta = ((1 - prior) * kappa).to_dict()
    qpos = block["queue_pos"].to_numpy()
    y = block["y_broad"].to_numpy(int)

    positions = block.groupby("pid").indices  # pid -> positional array
    pointer = {pid: 0 for pid in positions}
    order: list[int] = []

    for _ in range(budget):
        best_key, best_pid = None, None
        for pid, idx in positions.items():
            if pointer[pid] >= len(idx):
                continue
            p = alpha[pid] / (alpha[pid] + beta[pid])
            key = (p, -qpos[idx[pointer[pid]]])
            if best_key is None or key > best_key:
                best_key, best_pid = key, pid
        if best_pid is None:
            break
        idx = positions[best_pid][pointer[best_pid]]
        pointer[best_pid] += 1
        order.append(int(idx))
        if adaptive:
            if y[idx]:
                alpha[best_pid] += 1
            else:
                beta[best_pid] += 1
    return order


def precision_curve(block: pd.DataFrame, order: list[int], ks=(10, 25, 50, 100, 200)) -> dict:
    y = block["y_broad"].to_numpy(int)
    out = {}
    for k in ks:
        take = order[:k]
        out[f"p@{k}"] = float(y[take].mean()) if take else float("nan")
        out[f"hits@{k}"] = int(y[take].sum())
    return out


def run(queue: pd.DataFrame, feats: pd.DataFrame, kappas=(2.0, 10.0),
        budget: int = 200) -> dict:
    block = queue.loc[queue["m4"] & ~queue["m1"]].reset_index(drop=True)
    base = float(block["y_broad"].mean())
    prior = lopo_prior(queue, feats)

    results = {"n": int(len(block)), "positives": int(block["y_broad"].sum()),
               "base_precision": round(base, 6), "budget": budget, "variants": {}}

    for kappa in kappas:
        for mode, adaptive in (("belief_adaptive", True), ("prior_static", False)):
            order = simulate(block, prior, kappa, budget, adaptive=adaptive)
            key = f"{mode}_k{kappa:g}"
            results["variants"][key] = precision_curve(block, order)

    # reference: the queue's own order inside the block
    own = list(range(budget))
    results["variants"]["queue_order"] = precision_curve(block, own)
    return results
