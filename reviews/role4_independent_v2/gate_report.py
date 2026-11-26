"""Independent gate report, recomputed from the raw rows CSV."""
import csv
import sys

REPO = "/Users/sloblucyra/Documents/강화학습"
FAMILIES = ("spike", "modular", "ba", "er", "real")
POLICIES = ("confidence", "structural", "marginal")


def read(path):
    with open(path, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def main(block):
    mine = {}
    for r in read(f"{block}/rows.csv"):
        if r["draw"] != "0" or not r["actions"]:
            continue
        mine[(r["family"], int(r["graph_seed"]), r["condition"], r["policy"])] = (
            int(r["sink_errors"]), r["actions"])

    bench = {(r["family"], int(r["graph_seed"]), r["policy"]): (int(r["sink_errors"]), r["actions"])
             for r in read(f"{REPO}/role3 improvement/outputs/v3/benchmark_role3.csv")}
    ctl = {(r["family"], int(r["graph_seed"]), r["condition"], r["policy"]):
           (int(r["sink_errors"]), r["actions"])
           for r in read(f"{REPO}/role4_controls/results/controls.csv")}

    lines, failures = [], 0
    for name, ref, cond in (("intact==benchmark_role3", bench, "intact"),
                            ("flatten==controls.csv", ctl, "flatten"),
                            ("rewire_index:0==controls.csv[rewire]", ctl, "rewire_index")):
        compared = 0
        bad = 0
        for fam in FAMILIES:
            for seed in range(90000, 90100):
                for pol in POLICIES:
                    key_ref = (fam, seed, pol) if cond == "intact" else (fam, seed, "rewire" if cond == "rewire_index" else cond, pol)
                    if key_ref not in ref:
                        continue
                    compared += 1
                    if mine[(fam, seed, cond, pol)] != ref[key_ref]:
                        bad += 1
        failures += bad
        lines.append(f"{name}: compared {compared} rows, mismatches {bad}")
    lines.append("GATES " + ("PASS" if failures == 0 else "FAIL"))
    text = "\n".join(lines)
    print(text)
    with open(f"{block}/gate_report.txt", "w") as fh:
        fh.write(text + "\n")
    return failures


if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1]) else 0)
