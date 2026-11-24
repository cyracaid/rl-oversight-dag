"""Render the pre-registered robustness boundary from episodes.csv.

    python3 report_scope_robust.py results/scope-robust-v1

The verdict uses PREREGISTER_SCOPE_ROBUST.md's frozen arithmetic and nothing
else. Every comparison goes through `holds`, the whole grid is printed whether
or not the predictions hold, and the two boundary predictions (E4, E5) are
printed with their measured values instead of being restated.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from _env import EXPERIMENTS, ensure_experiments

ensure_experiments()
from rl_boundary import paired_bootstrap

POLICIES = ("oracle", "trust", "shrink", "scope")
DELTA_STEP = 0.5

# (name, value key, relation, bar, description)
RULES = (
    ("r1_offgrid_map", "off_grid_map", "<=", 0.50,
     "격자 밖 δ에서 최빈 셀이 이웃을 고른다 (평균 |δ_err|)"),
    ("r1_offgrid_q", "off_grid_q", ">=", 0.95,
     "격자 밖 100 % 셀에서 최빈 비율이 1이다 (평균 map_q)"),
    ("r2_offgrid_gain", "off_grid_gain", "<=", -0.50,
     "격자 밖 큰 음의 이동에서도 이득이 남는다 (평균 scope − trust)"),
    ("r2b_offgrid_harmless", "off_grid_harmless", "<=", 0.20,
     "격자 밖 큰 양의 이동에서 손해가 없다 (평균 scope − trust)"),
    ("r3_clean_cost", "clean_cost", "<=", 0.05,
     "깨끗한 그래프 비용 (scope − trust)"),
    ("e4_two_delta_loss", "two_delta_loss", ">", 0.0,
     "두 δ에서 shrink보다 나쁘다 (평균 scope − shrink)"),
    ("e5_two_delta_q", "two_delta_q", "<=", 0.50,
     "두 δ에서 전체 이동을 주장하지 않는다 (평균 map_q)"),
)
# (cell, fraction, shift_a, shift_b, label)
HEADLINES = (
    ("off_grid", 1.0, -2.37, 0.0, "격자 밖 −2.37 (100 %)"),
    ("off_grid", 1.0, 2.37, 0.0, "격자 밖 +2.37 (100 %)"),
    ("off_grid", 1.0, -3.6, 0.0, "격자 밖 −3.6 (100 %)"),
    ("off_grid", 1.0, 3.6, 0.0, "격자 밖 +3.6 (100 %)"),
    ("off_grid", 0.5, 2.37, 0.0, "격자 밖 +2.37 (50 %)"),
    ("two_delta", 1.0, -3.0, 3.0, "두 δ: source −3 / sink +3 (100 %)"),
    ("two_delta", 1.0, 3.0, -3.0, "두 δ: source +3 / sink −3 (100 %)"),
    ("two_delta", 1.0, -4.0, 2.0, "두 δ: source −4 / sink +2 (100 %)"),
)


def holds(value, relation, bar):
    if relation == "<=":
        return bool(value <= bar)
    if relation == ">=":
        return bool(value >= bar)
    if relation == ">":
        return bool(value > bar)
    raise ValueError(f"unknown relation {relation!r}")


def load(run):
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8-sig"))
    episodes = run / "episodes.csv"
    if hashlib.sha256(episodes.read_bytes()).hexdigest() != manifest["episodes_sha256"]:
        raise ValueError("episodes.csv SHA-256 does not match the run manifest")
    graphs = manifest["graph_seeds"]
    final, initial, diag = {}, {}, {}
    with episodes.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            graph = int(row["graph_seed"])
            key = (row["cell"], float(row["fraction"]), float(row["shift_a"]),
                   float(row["shift_b"]), row["policy"])
            if int(row["reviews"]) != manifest["budget"]:
                raise ValueError(f"review budget violated: {key}")
            final.setdefault(key, {})[graph] = int(row["sink_errors"])
            initial.setdefault(graph, int(row["initial_sink_errors"]))
            if row["policy"] == "scope":
                diag.setdefault(key, {})[graph] = (
                    float(row["map_q"]), float(row["map_delta"]))
    cells = {}
    for key, values in final.items():
        if set(values) != set(graphs):
            raise ValueError(f"incomplete cell {key}")
        cells[key] = np.array([values[graph] for graph in graphs])
    if len(initial) != len(graphs):
        raise ValueError("incomplete initial-error map")
    if not np.array_equal(cells[("clean", 0.0, 0.0, 0.0, "trust")],
                          cells[("clean", 0.0, 0.0, 0.0, "oracle")]):
        raise ValueError("clean trust must reproduce oracle exactly")
    return manifest, cells, diag, graphs


def gap(cells, key, policy, reference):
    result = paired_bootstrap(cells[key + (policy,)][None, :], cells[key + (reference,)],
                              draws=10000, seed=20261124)
    return f"{result['mean']:+.3f} [{result['low']:+.3f}, {result['high']:+.3f}]"


def grid_cells(manifest):
    off = [(fraction, shift, 0.0) for fraction in manifest["cells"]["off_grid"]["fractions"]
           for shift in manifest["cells"]["off_grid"]["shifts"]]
    two = [(fraction, pair[0], pair[1])
           for fraction in manifest["cells"]["two_delta"]["fractions"]
           for pair in manifest["cells"]["two_delta"]["shift_pairs"]]
    return off, two


def build(manifest, cells, diag, graphs):
    off, two = grid_cells(manifest)
    table = {}
    for cell, entries in (("off_grid", off), ("two_delta", two)):
        for fraction, shift_a, shift_b in entries:
            key = (cell, fraction, shift_a, shift_b)
            means = {policy: float(cells[key + (policy,)].mean())
                     for policy in ("trust", "shrink", "scope")}
            map_q = np.array([diag[key + ("scope",)][graph][0] for graph in graphs])
            map_delta = np.array([diag[key + ("scope",)][graph][1] for graph in graphs])
            table[key] = {
                "means": means,
                "scope_trust": means["scope"] - means["trust"],
                "scope_shrink": means["scope"] - means["shrink"],
                "shrink_trust": means["shrink"] - means["trust"],
                "map_q": float(map_q.mean()),
                "map_delta": float(map_delta.mean()),
                "delta_err": float(np.abs(map_delta - shift_a).mean()),
            }
    clean_trust = float(cells[("clean", 0.0, 0.0, 0.0, "trust")].mean())

    full_off = [(f, a, b) for (f, a, b) in off if f == 1.0]
    values = {
        "off_grid_map": float(np.mean([table[("off_grid", f, a, b)]["delta_err"]
                                       for f, a, b in full_off])),
        "off_grid_q": float(np.mean([table[("off_grid", f, a, b)]["map_q"]
                                     for f, a, b in full_off])),
        "off_grid_gain": float(np.mean([table[("off_grid", f, a, b)]["scope_trust"]
                                        for f, a, b in full_off if a <= -2.37])),
        "off_grid_harmless": float(np.mean([table[("off_grid", f, a, b)]["scope_trust"]
                                            for f, a, b in full_off if a >= 2.37])),
        "clean_cost": float(cells[("clean", 0.0, 0.0, 0.0, "scope")].mean()) - clean_trust,
        "two_delta_loss": float(np.mean([table[("two_delta", f, a, b)]["scope_shrink"]
                                         for f, a, b in two])),
        "two_delta_q": float(np.mean([table[("two_delta", f, a, b)]["map_q"]
                                      for f, a, b in two])),
    }
    checks, rule_rows = {}, {}
    for name, key, relation, bar, description in RULES:
        checks[name] = holds(values[key], relation, bar)
        rule_rows[name] = {"value": values[key], "relation": relation, "bar": bar,
                           "description": description, "holds": checks[name]}
    general = all(checks[name] for name in ("r1_offgrid_map", "r1_offgrid_q",
                                            "r2_offgrid_gain", "r2b_offgrid_harmless",
                                            "r3_clean_cost"))
    boundary = all(checks[name] for name in ("e4_two_delta_loss", "e5_two_delta_q"))
    if general and boundary:
        verdict = "성공"
    elif general:
        verdict = "부분 성공"
    else:
        verdict = "실패"
    return {"table": table, "rules": rule_rows, "verdict": verdict,
            "general_holds": general, "boundary_holds": boundary,
            "clean": {"oracle_trust": clean_trust,
                      "shrink": float(cells[("clean", 0.0, 0.0, 0.0, "shrink")].mean()),
                      "scope": float(cells[("clean", 0.0, 0.0, 0.0, "scope")].mean())},
            "bootstrap": {"unit": "paired graph", "draws": 10000, "seed": 20261124},
            "frozen": {"rules": [list(r) for r in RULES], "delta_step": DELTA_STEP}}


def render(manifest, cells, result, graphs):
    off, two = grid_cells(manifest)
    table = result["table"]
    count = len(graphs)
    lines = [
        "# 범위 모형의 경계: 격자 밖 δ와 두 개의 δ", "",
        f"사전 등록(`PREREGISTER_SCOPE_ROBUST.md`) 후 새 그래프 {count}개(seed {graphs[0]}–{graphs[-1]})에서 "
        f"격자 밖 이동 12셀과 두 층 동시 이동 8셀을 쟀다. 예산 {manifest['budget']}회, "
        f"`p0 = {manifest['scope']['p0']:.2f}`, `π = {manifest['scope']['shrink_reference_pi']:.2f}`는 "
        "이전 실험의 적합값을 그대로 쓴다. 재적합 없음.", "",
        "이 실험은 새 모형을 제안하지 않는다. 이미 확정된 모형의 **가정 두 개**를 하나씩 깬다. "
        "δ가 격자 위에 있다는 가정, δ가 하나라는 가정. 둘 다 생성기의 성질이지 실제 파이프라인의 "
        "성질이 아니다.", "",
        "## 기준선", "",
        "| 정책 | 깨끗한 그래프 평균 잔여 오류 |", "|---|---:|",
        f"| oracle = trust | {result['clean']['oracle_trust']:.3f} |",
        f"| shrink | {result['clean']['shrink']:.3f} |",
        f"| scope | {result['clean']['scope']:.3f} |",
        "", "## 격자 밖 δ", "",
        "`δ_err`는 그래프별 `|map_delta − δ_true|`의 평균이다. 100 % 셀에서만 최빈 셀이 "
        "참 δ를 따라가는지 본다(50 %는 q가 부분값인 것이 정상).", "",
        "| 비율 | δ_true | trust | shrink | scope | scope − trust | map_q | δ_err |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for fraction, shift, _ in off:
        row = table[("off_grid", fraction, shift, 0.0)]
        means = row["means"]
        lines.append(f"| {fraction:.0%} | {shift:+.2f} | {means['trust']:.2f} | "
                     f"{means['shrink']:.2f} | {means['scope']:.2f} | "
                     f"{row['scope_trust']:+.2f} | {row['map_q']:.2f} | {row['delta_err']:.2f} |")

    lines.extend(["", "## 두 개의 δ (source / sink)", "",
                  "`scope − shrink`가 양수면 shrink보다 나쁘다. shrink는 노드마다 δ를 고를 수 있으므로 "
                  "두 δ를 표현할 수 있고, scope는 하나만 가질 수 있다.", "",
                  "| 비율 | δ_source | δ_sink | trust | shrink | scope | scope − shrink | map_q |",
                  "|---:|---:|---:|---:|---:|---:|---:|---:|"])
    for fraction, shift_a, shift_b in two:
        row = table[("two_delta", fraction, shift_a, shift_b)]
        means = row["means"]
        lines.append(f"| {fraction:.0%} | {shift_a:+.1f} | {shift_b:+.1f} | {means['trust']:.2f} | "
                     f"{means['shrink']:.2f} | {means['scope']:.2f} | "
                     f"{row['scope_shrink']:+.2f} | {row['map_q']:.2f} |")

    lines.extend(["", "## 핵심 셀 (짝지은 부트스트랩 95 % 구간)", "",
                  "| 셀 | scope − trust | scope − shrink |", "|---|---:|---:|"])
    for cell, fraction, shift_a, shift_b, label in HEADLINES:
        key = (cell, fraction, shift_a, shift_b)
        lines.append(f"| {label} | {gap(cells, key, 'scope', 'trust')} "
                     f"| {gap(cells, key, 'scope', 'shrink')} |")

    lines.extend(["", "## 예측 대조와 판정", ""])
    for name, _, _, _, description in RULES:
        row = result["rules"][name]
        lines.append(f"- {description}: **{'성립' if row['holds'] else '불성립'}** "
                     f"({row['value']:+.3f}, 기준 {row['relation']} {row['bar']:+.2f}).")
    lines.extend(["", f"사전 등록 판정: **{result['verdict']}**.", ""])

    if result["verdict"] == "성공":
        lines.extend([
            "격자 밖에서도 최빈 셀은 참 δ의 이웃을 고르고, 큰 이동의 이득은 남았으며, 깨끗한 비용은 "
            "상한 안이다. 두 δ에서는 예상대로 shrink보다 나쁘고, 모형은 전체 이동을 주장하지 않는다. "
            "즉 **경계 지도가 사전 예측과 일치**한다.", "",
            "일반성 주장은 이 범위까지다: δ는 연속이어도 이웃 셀로 흡수되지만, δ가 둘이면 모형은 "
            "하나를 포기한다. 그 조건의 기준선은 shrink다.", "",
        ])
    elif result["verdict"] == "부분 성공":
        lines.extend([
            "격자 밖 강건성은 확인됐지만 두 δ 경계 예측 하나가 빗나갔다. 어느 쪽이 빗나갔는지가 "
            "모형이 생각보다 넓거나 좁다는 뜻이므로, 그 방향으로만 해석한다.", "",
        ])
    else:
        lines.extend([
            "일반성 예측이 깨졌다. 격자 밖 δ에서 이득이 사라졌거나, 최빈 셀이 참 δ를 따라가지 "
            "못했거나, 깨끗한 비용이 상한을 넘었다. 이 경우 scope의 우위는 격자 위 δ에 한정되며, "
            "실제 드리프트가 연속값인 환경으로 일반화할 수 없다.", "",
        ])

    lines.extend([
        "## 한계", "",
        "- δ 격자는 여전히 0.5 간격이고, 격자 밖 값은 이웃 셀로 흡수된다. 잔차 자체를 줄이는 "
        "방법(연속 최적화)은 이 실험에 없다.",
        "- 두 δ는 서로소인 두 층에 하나씩만 놓았다. 한 층 안에서 δ가 섞이거나 세 층이 동시에 "
        "움직이는 조건은 없다.",
        "- 100장, 단일 family, 단일 예산. 판정은 위 산술로만 계산했고 사후 조정은 없다.",
        "- `oracle`은 정답 점수를 쓰므로 비배포 상한이다. 표의 oracle 열은 깨끗한 점수의 성능이다.",
        "", "[그래프별 결과](episodes.csv) · [실행 설정](manifest.json) · "
        "[수치 요약](scope_robust.json) · [사전 등록](../PREREGISTER_SCOPE_ROBUST.md)", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    run = parser.parse_args().run
    manifest, cells, diag, graphs = load(run)
    result = build(manifest, cells, diag, graphs)
    result["source_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (run / "manifest.json", run / "episodes.csv", Path(__file__),
                     Path(__file__).with_name("PREREGISTER_SCOPE_ROBUST.md"),
                     EXPERIMENTS / "rl_boundary.py")
    }
    (run / "scope_robust.md").write_text(render(manifest, cells, result, graphs),
                                         encoding="utf-8")
    serializable = dict(result)
    serializable["table"] = {"|".join((key[0], f"{key[1]:.2f}", f"{key[2]:+.2f}",
                                       f"{key[3]:+.2f}")): row
                             for key, row in result["table"].items()}
    (run / "scope_robust.json").write_text(
        json.dumps(serializable, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(run / "scope_robust.md")


if __name__ == "__main__":
    main()
