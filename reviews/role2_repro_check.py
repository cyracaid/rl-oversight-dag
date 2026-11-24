"""Re-run role2_규리 experiments locally and compare them with the committed results.

Reviewer: 한광희 (role 1, code review). Run from the repository root:

    python -X utf8 reviews/role2_repro_check.py            # full (200 graphs each)
    python -X utf8 reviews/role2_repro_check.py --quick    # first 40 graphs each

Writes reviews/role2_repro_result.md. New run folders go to role2_규리/runs/ (git-ignored).
Only the standard library is used here; the experiment scripts need
`role3 improvement/requirements.txt`.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import platform
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLE2 = ROOT / "role2_규리"
RESULTS = ROLE2 / "results"
OUT_MD = ROOT / "reviews" / "role2_repro_result.md"

# name, script, extra args, committed folder, key columns, start seed
EXPERIMENTS = [
    ("partial", "evaluate_partial.py", ["--workers", "4"], "partial-v1",
     ("graph_seed", "shuffled_type_count", "approach"), 95000),
    ("confirm", "evaluate_conditions.py", ["--confirm"], "confirm-v1",
     ("graph_seed", "condition", "policy"), 2000),
    ("conditions", "evaluate_conditions.py", [], "confidence-v1",
     ("graph_seed", "condition", "policy"), 91000),
    ("feedback", "evaluate_feedback.py", [], "feedback-v1",
     ("graph_seed", "condition", "policy", "approach"), 92000),
]
# columns averaged in the summary table (GNN seeds pooled as "gnn")
GROUP = {"partial": ("shuffled_type_count", "approach"), "confirm": ("condition", "policy"),
         "conditions": ("condition", "policy"), "feedback": ("condition", "policy", "approach")}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path, keys):
    with path.open(encoding="utf-8", newline="") as stream:
        return {tuple(row[k] for k in keys): row for row in csv.DictReader(stream)}


def run(cmd, log, cwd=ROOT):
    print(">", " ".join(map(str, cmd)), flush=True)
    started = dt.datetime.now()
    proc = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    seconds = (dt.datetime.now() - started).total_seconds()
    log.append((" ".join(map(str, cmd)), proc.returncode, seconds, (proc.stdout + proc.stderr)[-1500:]))
    print(f"  exit {proc.returncode}, {seconds:.0f}s", flush=True)
    return proc.returncode == 0


def compare(name, new_csv, old_dir, keys):
    new = load(new_csv, keys)
    old = load(old_dir / "episodes.csv", keys)
    seeds = {k[0] for k in new}
    old = {k: v for k, v in old.items() if k[0] in seeds}   # same graphs only
    shared = sorted(set(new) & set(old))
    same = sum(new[k]["sink_errors"] == old[k]["sink_errors"] for k in shared)
    groups = defaultdict(lambda: [[], []])
    for k in shared:
        g = tuple("gnn" if (c == "policy" and new[k][c].startswith("gnn")) else new[k][c]
                  for c in GROUP[name])
        groups[g][0].append(int(old[k]["sink_errors"]))
        groups[g][1].append(int(new[k]["sink_errors"]))
    table = [(g, sum(o) / len(o), sum(n) / len(n)) for g, (o, n) in sorted(groups.items())]
    return {"rows_new": len(new), "rows_old": len(old), "shared": len(shared), "same": same,
            "graphs": len(seeds), "table": table}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true", help="first 40 graphs of each experiment")
    ap.add_argument("--only", nargs="+", choices=[e[0] for e in EXPERIMENTS])
    args = ap.parse_args()
    graphs = 40 if args.quick else 200
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    log, reports = [], {}

    tests_ok = run([sys.executable, "-X", "utf8", "-m", "unittest", "-v",
                    "test_planning", "test_sleep"], log, cwd=ROLE2) if not args.only else None

    for name, script, extra, folder, keys, start in EXPERIMENTS:
        if args.only and name not in args.only:
            continue
        out = ROLE2 / "runs" / f"review-{name}-{stamp}"
        cmd = [sys.executable, "-X", "utf8", ROLE2 / script, "--out", out, "--graphs", graphs, *extra]
        if name != "confirm":
            cmd += ["--start", start]
        if not run(cmd, log):
            reports[name] = {"error": True}
            continue
        report = compare(name, out / "episodes.csv", RESULTS / folder, keys)
        if not args.quick:
            manifest = json.loads((RESULTS / folder / "manifest.json").read_text(encoding="utf-8"))
            report["sha_match"] = sha256(out / "episodes.csv") == manifest.get("episodes_sha256")
        reports[name] = report

    try:
        import numpy, torch  # noqa: E401
        versions = f"numpy {numpy.__version__}, torch {torch.__version__}"
    except Exception as exc:  # pragma: no cover
        versions = f"(version check failed: {exc})"
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip() or "?"

    lines = ["# role2_규리 로컬 재실행 결과", "",
             f"- 실행: {dt.datetime.now():%Y-%m-%d %H:%M}, 커밋 `{commit}`, "
             f"{'빠른 점검(그래프 40개)' if args.quick else '전체(그래프 200개)'}",
             f"- 환경: {platform.system()} {platform.release()}, Python {platform.python_version()}, {versions}",
             "- 비교 기준: 같은 그래프·같은 정책끼리 `sink_errors`(남은 결론 오류)를 한 줄씩 대조", ""]
    if tests_ok is not None:
        lines += [f"단위 테스트(test_planning, test_sleep): **{'통과' if tests_ok else '실패'}**", ""]
    lines += ["| 실험 | 비교한 줄 | 완전히 같은 줄 | 결과 파일 해시 |", "|---|---:|---:|---|"]
    for name, r in reports.items():
        if r.get("error"):
            lines.append(f"| {name} | 실행 실패 | – | – |")
            continue
        sha = "–" if "sha_match" not in r else ("일치" if r["sha_match"] else "다름")
        lines.append(f"| {name} | {r['shared']} | {r['same']} ({100 * r['same'] / max(1, r['shared']):.1f}%) | {sha} |")
    for name, r in reports.items():
        if r.get("error"):
            continue
        lines += ["", f"## {name} (그래프 {r['graphs']}개, 평균 남은 결론 오류)", "",
                  "| 셀 | 저장된 결과 | 재실행 | 차이 |", "|---|---:|---:|---:|"]
        for g, old, new in r["table"]:
            lines.append(f"| {' / '.join(g)} | {old:.3f} | {new:.3f} | {new - old:+.3f} |")
    lines += ["", "## 실행 기록", ""]
    for cmd, code, sec, tail in log:
        lines += [f"- `{cmd}` → exit {code}, {sec:.0f}초"]
        if code:
            lines += ["", "```", tail, "```"]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote {OUT_MD}")


if __name__ == "__main__":
    main()
