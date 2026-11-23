"""Render a Korean comparison sheet from the three completed follow-up reports."""

import json
from pathlib import Path

from matplotlib import font_manager, rc_context
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle


RUNS = Path(__file__).resolve().parent / "results"
INK, MUTED, HIGHLIGHT, PALE = "#162E40", "#455E6C", "#006C66", "#EAF4F2"


def read(path):
    return json.loads((RUNS / path).read_text(encoding="utf-8"))


def render():
    partial = read("partial-v1/partial.json")
    credit = read("credit-v1/summary.json")
    sleep = read("sleep-v1/kaist_replay.json")
    pc = partial["conditions"]["2"]["mean_final_errors"]
    cc = credit["conditions"]["shuffled"]
    sc = sleep["conditions"]["evaluation/consecutive"]
    sleep_data = sleep["historical_baseline_check"]["header"]
    sleep_values = [sc["means"][name]["wrong_conclusions_C1_C3"] for name in ("before_review", "qc", "contiguous")]

    fonts = ["Malgun Gothic", "Noto Sans CJK KR", "Noto Sans KR", "Apple SD Gothic Neo"]
    installed = set(font_manager.get_font_names())
    family = next((font for font in fonts if font in installed), None)
    if not family:
        raise RuntimeError("Install a Korean font: " + ", ".join(fonts))
    with rc_context({"font.family": family}):
        fig = Figure(figsize=(10.5, 10.0), facecolor="#FFFFFF")

        def text(x, y, value, size, color=INK, bold=False):
            fig.text(x, y, value, color=color, va="center", fontsize=size, weight="bold" if bold else "normal")

        def row(top, title, context, unit, labels, values, conclusion, precision=3):
            text(.052, top, title, 16.4, bold=True)
            text(.052, top - .036, context, 10.7, MUTED)
            fig.add_artist(Rectangle((.05, top - .166), .9, .101, transform=fig.transFigure,
                                     linewidth=0, facecolor=PALE, zorder=0))
            for i, (label, value) in enumerate(zip(labels, values)):
                x = .067 + .30 * i
                text(x, top - .093, label, 10.8, MUTED)
                text(x, top - .135, f"{value:.{precision}f}개", 17.3, HIGHLIGHT, bold=True)
            text(.052, top - .19, unit, 10.6, MUTED)
            text(.052, top - .22, conclusion, 12.0, bold=True)

        text(.05, .948, "검토가 끝난 뒤, 틀린 결론은 몇 개 남았나?", 25.8, bold=True)
        text(.052, .897, "Role 2 후속 실험   ·   각 표에서 작을수록 검토 후 남은 평균 오류가 적다.", 13.0, MUTED)
        for y in (.86, .589, .318):
            fig.add_artist(Line2D([.05, .95], [y, y], transform=fig.transFigure, linewidth=1.0, color="#A9BFBE"))

        row(.827, "일부 점수가 뒤섞였을 때, 얼마나 믿어야 할까?",
            f"5개 항목 유형 중 2개에서 점수를 섞었다. 합성 작업 흐름 {partial['graphs']}개에서 각각 80개 항목 중 16개를 검토했다.",
            "단위  ·  작업 흐름 하나의 최종 결론 20개 중 틀린 개수",
            ("점수를 계속 신뢰", "점수를 계속 무시", "검토 결과에 따라 신뢰·무시 선택"),
            (pc["trust"], pc["ignore"], pc["feedback"]),
            "검토하면서 판단하면 점수를 계속 무시할 때보다 오류가 줄었다. 계속 신뢰할 때와의 차이는 불확실했다.")

        first, last = credit["graph_range_inclusive"]
        row(.556, "어떤 검토가 도움이 됐는지 구분해 보상을 주면?",
            f"모든 유형에서 점수를 섞었다. 모델을 초기값 {len(credit['train_seeds'])}가지로 학습하고 새 흐름 "
            f"{last - first + 1}개에서 각각 16번 검토했다.",
            "단위  ·  작업 흐름 하나의 최종 결론 20개 중 틀린 개수",
            ("학습 모델 · 모든 선택에 같은 보상", "학습 모델 · 각 선택 이후 개선만 반영", "규칙 · 여러 결론에 영향 주는 항목 우선"),
            (cc["means"]["terminal"], cc["means"]["future"], cc["rule"]),
            "보상을 바꾸자 학습 모델의 오류가 줄었다. 기존 검토 규칙이 남긴 평균 오류는 그보다 조금 적었다.")

        dev = sleep["conditions"]["development/consecutive"]["participants"]
        row(.285, "수면 기록에 연속 이틀 오류를 넣으면, 어느 밤을 열어야 할까?",
            f"KAIST {sleep_data['participants_total']}명·{sleep_data['records_used']:,}박(개발 {dev}명, 평가 {sc['participants']}명). "
            f"평가에서는 오류를 넣은 {sc['scenarios']:,}가지 상황마다 참가자당 2박을 검토했다.",
            "단위  ·  수면시간·효율·불규칙성 판단 3개 중 오류 주입 전과 달라진 개수의 참가자별 평균",
            ("검토하기 전", "품질 규칙이 고른 두 밤 검토", "오류 의심 점수가 높은 연속 이틀 검토"),
            sleep_values, "두 방식 모두 오류를 줄였다. 두 밤을 연속으로 골라 추가로 얻는 이득은 확인되지 않았다.",
            precision=5)
        fig.savefig(RUNS / "후속실험요약.png", dpi=175)


if __name__ == "__main__":
    render()
