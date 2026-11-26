"""Compare clean-room summaries with the two target summaries (read only now)."""
import csv
import sys

REPO = "/Users/sloblucyra/Documents/강화학습"
KEY = ("family", "rule", "policy")
IGNORE = {"direction"}


def load(path):
    with open(path, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    return {tuple(r[k] for k in KEY): r for r in rows}, rows[0].keys()


def same(a, b):
    if a == b:
        return True
    try:
        return round(float(a), 4) == round(float(b), 4)
    except (TypeError, ValueError):
        return False


def compare(mine, target, label):
    mrows, mcols = load(mine)
    trows, tcols = load(target)
    cols = [c for c in tcols if c not in IGNORE]
    missing_cols = [c for c in cols if c not in mcols]
    extra_cols = [c for c in mcols if c not in tcols]
    if missing_cols:
        print(f"{label}: target columns I lack: {missing_cols}")
    if extra_cols:
        print(f"{label}: columns I have that target lacks: {extra_cols}")
    print(f"{label}: my rows {len(mrows)}, target rows {len(trows)}")
    only_mine = sorted(set(mrows) - set(trows))
    only_tgt = sorted(set(trows) - set(mrows))
    if only_mine:
        print(f"{label}: keys only in mine: {only_mine}")
    if only_tgt:
        print(f"{label}: keys only in target: {only_tgt}")
    mismatch = []
    total = 0
    for key in sorted(set(mrows) & set(trows)):
        for c in cols:
            total += 1
            if not same(mrows[key].get(c), trows[key][c]):
                mismatch.append((key, c, mrows[key].get(c), trows[key][c]))
    print(f"{label}: {len(mismatch)} mismatched cells out of {total} compared")
    by_col = {}
    for key, c, a, b in mismatch:
        by_col.setdefault(c, []).append((key, a, b))
    for c, items in by_col.items():
        print(f"  column {c}: {len(items)}")
        for key, a, b in items[:6]:
            print(f"    {key}: mine={a} target={b}")
        if len(items) > 6:
            print(f"    ... {len(items)-6} more")
    labels = sum(1 for key in set(mrows) & set(trows)
                 if mrows[key]["verdict"] == trows[key]["verdict"])
    print(f"{label}: verdict label agreement {labels}/{len(set(mrows) & set(trows))}")
    for key, c, a, b in mismatch:
        if c == "verdict":
            print(f"    label diff {key}: mine={a} target={b}")
    prim = [k for k in set(mrows) & set(trows)
            if k[0] in ("spike", "modular", "ba", "er") and k[2] == "marginal"
            and k[1] in ("flatten", "rewire_index", "rewire_order")]
    agree = sum(1 for k in prim if mrows[k]["verdict"] == trows[k]["verdict"])
    print(f"{label}: primary labels (marginal x sp/mod/ba/er x 3 controls) {agree}/{len(prim)}")
    return mismatch


if __name__ == "__main__":
    compare("out90000/summary.csv",
            f"{REPO}/role4_controls/results/v2/controls_v2_summary.csv", "90000")
    print()
    compare("out7100/summary.csv",
            f"{REPO}/role4_controls/results/v2_confirm/controls_v2_summary.csv", "7100")
