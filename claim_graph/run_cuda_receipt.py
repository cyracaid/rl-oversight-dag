"""Write the coverage receipt for a case repository's claim tables."""
import argparse
import json
from pathlib import Path

from claim_graph import case, plan


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache", type=Path, default=Path("claim_graph/.cache"))
    ap.add_argument("--out", type=Path, default=Path("claim_graph/outputs/cuda-case"))
    ap.add_argument("--budgets", nargs="+", type=int, default=list(plan.BUDGETS))
    args = ap.parse_args()
    claims, provenance = case.load(str(args.cache))
    data = plan.receipt(claims, provenance, budgets=tuple(args.budgets))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "receipt.json").write_text(json.dumps(data, indent=2))
    (args.out / "receipt.md").write_text(plan.render(data))
    inv = data["inventory"]
    print(f"claims {inv['claims']}  presented {inv['presented']}  "
          f"weak {inv['weak']}  weak_presented {inv['weak_presented']}")
    for row in data["coverage"]:
        if row["budget"] == max(data["budgets"]):
            print(f"  {row['ranking']:14s} B={row['budget']:4d} "
                  f"covers {row['share_of_weak_presented']:.1%} of weak mass")


if __name__ == "__main__":
    main()
