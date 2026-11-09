#!/usr/bin/env python3
"""Generate PLAN.html (trilingual: EN / KO / 中文) from one data structure.

The page is static; this script only exists so the three language blocks stay in
sync. Run:

    python3 tools/build_plan.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

L = {}

L["en"] = {
    "nav": "Plan",
    "title": "Five people, one critical path",
    "lead": "Not five independent tasks: <b>two surveys that can truly run in parallel</b>, "
            "<b>one critical path</b>, <b>one choke point</b>. All parallelism is bought by four "
            "interfaces that must be frozen by day 2.",
    "stats": [("2", "truly independent surveys (WP3 reading / WP5 datasets)"),
              ("1", "choke point: freezing the environment (change it once, every number dies)"),
              ("4", "interfaces frozen by day 2"),
              ("G0", "day-5 decision: Option 1 or Option 2")],
    "banner": "<b>Status discipline.</b> The belief-conditioned GNN + REINFORCE result is <b>a single run</b>, "
              "marked <span class=\"tag\">unverified</span>. Until WP1 reproduces it, no document, slide or "
              "group-chat message may present it as a finding.",
    "h_graph": "1. Dependency graph",
    "legend": ["critical path (cannot be compressed)", "parallel / independent",
               "dashed = interface dependency, not time"],
    "h_gantt": "2. Eight-day schedule (who moves when)",
    "gantt_head": ["Person", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"],
    "gantt": [
        ("P1 lead", ["WP0", "WP0 frozen", "review", "review", "review", "paper", "paper", "paper"], "c1"),
        ("P2 policy", ["read code", "belief feats", "WP1", "WP1", "G0", "O1: seeds", "O1: seeds", "WP4"], "c2"),
        ("P3 env", ["WP2 freeze", "schema", "adapter", "adapter", "G1 data", "G1", "G1", "G1 table"], "c3"),
        ("P4 baselines", ["WP3 survey", "WP3 survey", "WP3 impl", "WP3 impl", "WP3 impl", "WP4", "WP4", "WP4 table"], "c5"),
        ("P5 you", ["WP5 survey", "schema", "licences", "licences", "WP5 hand-off", "G1 data", "writing", "writing"], "c2"),
    ],
    "h_people": "3. Five people, five deliverables",
    "cards": [
        ("WP0", "P1 · lead / protocol", "One job: make everyone's numbers comparable",
         ["<code>eval.py</code>: the single recall / CI implementation",
          "table template, seed protocol, pairing rule",
          "reject any table without a CI or a script path"],
         "Acceptance: others import your eval instead of copying it. Frozen by D2."),
        ("WP1", "P2 · policy gradient", "One question: does RL lose on representation or on credit assignment?",
         ["belief / static / observed / belief-greedy, four arms",
          "5 seeds × 200 held-out graphs × paired bootstrap",
          "publish every seed, not the best one"],
         "Acceptance: one command produces one table; a negative result is still a delivery.<br>Blocked by: WP2 freeze."),
        ("WP2", "P3 · environment", "The choke point: move the environment and every number dies",
         ["tag and freeze the synthetic generator",
          "define the item schema for transfer datasets",
          "write the KAIST adapter"],
         "Acceptance: <code>--dataset kaist</code> runs end to end; after the freeze, changing the env means a new version and a full rerun."),
        ("WP3 · WP4", "P4 · baselines / controls", "Survey first, implement two; diagnostics only under Option 2",
         ["five candidates: VOI, MCTS, BC, offline RL, transformer",
          "implement the two cheapest on the same harness",
          "diagnostics: credit correlation, return variance, four interventions"],
         "Acceptance: a one-page fit/effort/risk table plus two working baselines."),
        ("WP5", "P5 · you / data", "The only truly independent job, and it decides whether this generalizes",
         ["KAIST → GO → Manchester, verifying licence and fields",
          "open the real files, not the abstract",
          "no data in the repo, only aggregate numbers"],
         "Acceptance: every row has a verifiable licence and a load command that runs."),
    ],
    "h_interfaces": "4. Four interfaces that must be frozen by day 2",
    "if_head": ["Interface", "owner", "consumers", "cost of not freezing it"],
    "interfaces": [
        ("<code>eval.py</code>", "P1", "P2/P3/P4/P5", "two denominators; the numbers disagree in the last week"),
        ("item schema (unit/type/label/edge/cost)", "P2+P5", "adapter, G1, G2", "a dataset needs a field the simulator cannot express, and the env changes after the freeze"),
        ("env tag + seed protocol", "P3", "all experiments", "the env is edited after verification and every table dies"),
        ("table template (columns / CI rule / script path)", "P1", "every report", "five tables nobody can merge"),
    ],
    "h_gates": "5. Three gates",
    "gates": [
        ("red", "G0 · D5 · decides how the whole deliverable is written.",
         "After the belief features go into RL: catching up → <b>Option 1</b> (RL is the method); "
         "still behind → <b>Option 2</b> (credit assignment is the cause; the analysis is the result)."),
        ("green", "G1 · D6–8 · a second sleep cohort.",
         "Same table, same script. Only a repeated ordering (type ≫ within-type) counts as transfer."),
        ("green", "G2 · after the course · a different biological unit (GO).",
         "The real test of whether the method only works on timestamps."),
    ],
    "footer": "Plan · 2026-11-09 · numbers follow <a href=\"GENERALIZATION_PLAN.md\">GENERALIZATION_PLAN.md</a> · "
              "RL detail in <a href=\"RL_PLAN.md\">RL_PLAN.md</a> · "
              "<span class=\"tag\">unverified</span> follows the repo's §12 discipline",
    "svg": {
        "wp0": "WP0 protocol + harness", "wp2": "WP2 freeze env", "wp1": "WP1 verify",
        "g0": "G0 decision", "g0s": "day 5", "paper": "Paper / slides",
        "wp5": "WP5 dataset survey", "wp5s": "P5 · day 1–5 · indep.",
        "adapter": "Adapter", "adapters": "P5+P3 · schema",
        "g1": "G1 sleep B", "g1s": "day 6–8", "g2": "G2 GO", "g2s": "later",
        "wp3": "WP3 model survey", "wp3s": "P4 · day 1–2 · indep.",
        "wp3i": "WP3 implement 2", "wp3is": "P4 · day 3–8",
        "wp4": "WP4 diagnostics", "wp4s": "P4+P2 · Option 2 only",
        "schema": "item schema",
    },
}

L["ko"] = {
    "nav": "계획",
    "title": "다섯 명, 하나의 임계 경로",
    "lead": "독립된 다섯 과제가 아니다. <b>진짜 병렬로 돌릴 수 있는 조사 두 개</b>, "
            "<b>하나의 임계 경로</b>, <b>하나의 병목</b>. 병렬성은 2일 차까지 고정하는 네 개의 인터페이스로 산다.",
    "stats": [("2", "진짜 독립 조사 (WP3 문헌 / WP5 데이터셋)"),
              ("1", "병목: 환경 동결 (한 번 바뀌면 모든 숫자가 죽는다)"),
              ("4", "2일 차까지 고정하는 인터페이스"),
              ("G0", "5일 차 결정: Option 1 또는 Option 2")],
    "banner": "<b>상태 규율.</b> belief 조건화 GNN + REINFORCE 결과는 <b>단 한 번의 실행</b>이며 "
              "<span class=\"tag\">unverified</span>로 표시한다. WP1이 재현하기 전까지 어떤 문서·슬라이드·단체 대화도 "
              "이를 결론으로 쓰지 않는다.",
    "h_graph": "1. 의존 그래프",
    "legend": ["임계 경로 (압축 불가)", "병렬 / 독립", "점선 = 인터페이스 의존, 시간 의존 아님"],
    "h_gantt": "2. 8일 일정 (누가 언제 움직이나)",
    "gantt_head": ["사람", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"],
    "gantt": [
        ("P1 팀장", ["WP0", "WP0 확정", "검수", "검수", "검수", "논문", "논문", "논문"], "c1"),
        ("P2 정책", ["코드 읽기", "belief 특징", "WP1", "WP1", "G0", "O1: 시드", "O1: 시드", "WP4"], "c2"),
        ("P3 환경", ["WP2 동결", "스키마", "어댑터", "어댑터", "G1 데이터", "G1", "G1", "G1 표"], "c3"),
        ("P4 베이스라인", ["WP3 조사", "WP3 조사", "WP3 구현", "WP3 구현", "WP3 구현", "WP4", "WP4", "WP4 표"], "c5"),
        ("P5 당신", ["WP5 조사", "스키마", "라이선스", "라이선스", "WP5 인계", "G1 데이터", "집필", "집필"], "c2"),
    ],
    "h_people": "3. 다섯 명, 다섯 개의 산출물",
    "cards": [
        ("WP0", "P1 · 팀장 / 프로토콜", "한 가지 일: 모두의 숫자를 비교 가능하게 만든다",
         ["<code>eval.py</code>: 유일한 recall / CI 구현",
          "표 템플릿, 시드 프로토콜, 페어링 규칙",
          "CI나 스크립트 경로가 없는 표는 반려"],
         "검수: 다른 사람이 당신의 eval을 import 한다(복사하지 않는다). D2까지 확정."),
        ("WP1", "P2 · 정책 경사", "한 가지 질문: RL은 표현에서 지는가, 크레딧 할당에서 지는가",
         ["belief / static / observed / belief-greedy 네 갈래",
          "5 시드 × 200 held-out 그래프 × 짝지은 부트스트랩",
          "가장 좋은 시드가 아니라 모든 시드를 공개"],
         "검수: 한 명령으로 표 하나; 부정적 결과도 납품이다.<br>차단: WP2 동결."),
        ("WP2", "P3 · 환경", "병목 본인: 환경이 움직이면 모든 숫자가 죽는다",
         ["합성 생성기를 태그로 동결",
          "전이 데이터셋의 item 스키마 정의",
          "KAIST 어댑터 작성"],
         "검수: <code>--dataset kaist</code> 한 명령으로 끝까지; 동결 후 환경 변경 = 새 버전 + 전면 재실행."),
        ("WP3 · WP4", "P4 · 베이스라인 / 대조", "먼저 조사, 두 개 구현; 진단은 Option 2일 때만",
         ["다섯 후보: VOI, MCTS, BC, 오프라인 RL, 트랜스포머",
          "가장 싼 두 개를 같은 harness에 구현",
          "진단: 크레딧 상관, 리턴 분산, 네 가지 개입"],
         "검수: fit/effort/risk 한 페이지 표 + 작동하는 베이스라인 두 개."),
        ("WP5", "P5 · 당신 / 데이터", "유일하게 진짜 독립인 일, 그리고 일반화 가능성을 좌우한다",
         ["KAIST → GO → Manchester, 라이선스와 필드 확인",
          "초록이 아니라 실제 파일을 연다",
          "데이터는 저장소에 넣지 않고 집계만"],
         "검수: 모든 행에 검증 가능한 라이선스와 실행되는 로드 명령."),
    ],
    "h_interfaces": "4. 2일 차까지 고정해야 하는 네 개의 인터페이스",
    "if_head": ["인터페이스", "owner", "사용자", "고정하지 않으면"],
    "interfaces": [
        ("<code>eval.py</code>", "P1", "P2/P3/P4/P5", "분모가 두 개가 되어 마지막 주에 숫자가 어긋난다"),
        ("item 스키마 (unit/type/label/edge/cost)", "P2+P5", "어댑터, G1, G2", "데이터셋이 요구하는 필드를 시뮬레이터가 표현하지 못해 동결 후 환경을 고친다"),
        ("환경 태그 + 시드 프로토콜", "P3", "모든 실험", "검증 후 환경이 바뀌어 모든 표가 무효"),
        ("표 템플릿 (열 / CI 규칙 / 스크립트 경로)", "P1", "모든 보고", "합칠 수 없는 다섯 개의 표"),
    ],
    "h_gates": "5. 세 개의 관문",
    "gates": [
        ("red", "G0 · D5 · 과제 전체의 서술 방식을 결정한다.",
         "belief 특징을 RL에 넣은 뒤: 따라잡으면 <b>Option 1</b>(RL이 방법), 여전히 뒤지면 "
         "<b>Option 2</b>(크레딧 할당이 원인, 분석이 결과)."),
        ("green", "G1 · D6–8 · 두 번째 수면 코호트.",
         "같은 표, 같은 스크립트. 순서가 반복(type ≫ within-type)되어야 전이로 인정."),
        ("green", "G2 · 과정 이후 · 다른 생물학적 단위 (GO).",
         "이 방법이 시간값에만 통하는지에 대한 진짜 시험."),
    ],
    "footer": "Plan · 2026-11-09 · 숫자 기준은 <a href=\"GENERALIZATION_PLAN.md\">GENERALIZATION_PLAN.md</a> · "
              "RL 세부는 <a href=\"RL_PLAN.md\">RL_PLAN.md</a> · "
              "<span class=\"tag\">unverified</span> 표기는 저장소 §12 규율을 따른다",
    "svg": {
        "wp0": "WP0 프로토콜 + harness", "wp2": "WP2 환경 동결", "wp1": "WP1 재현 검증",
        "g0": "G0 결정", "g0s": "5일 차", "paper": "논문 / 슬라이드",
        "wp5": "WP5 데이터셋 조사", "wp5s": "P5 · 1–5일 · 독립",
        "adapter": "어댑터", "adapters": "P5+P3 · 스키마",
        "g1": "G1 수면 B", "g1s": "6–8일", "g2": "G2 GO", "g2s": "이후",
        "wp3": "WP3 모델 조사", "wp3s": "P4 · 1–2일 · 독립",
        "wp3i": "WP3 2개 구현", "wp3is": "P4 · 3–8일",
        "wp4": "WP4 진단", "wp4s": "P4+P2 · Option 2만",
        "schema": "item 스키마",
    },
}

L["zh"] = {
    "nav": "计划",
    "title": "五个人，一条关键路径",
    "lead": "不是五个独立任务：<b>两个可以真并行的调研</b>、<b>一条关键路径</b>、<b>一个卡点</b>。"
            "所有并行靠第 2 天前定死的四个接口买来。",
    "stats": [("2", "真正独立的调研（WP3 文献 / WP5 数据集）"),
              ("1", "卡点：环境冻结（动一次，全部数字作废）"),
              ("4", "第 2 天前必须定死的接口"),
              ("G0", "第 5 天决策：Option 1 还是 Option 2")],
    "banner": "<b>状态纪律。</b>belief 条件化的 GNN + REINFORCE 目前是<b>一次运行</b>，标记 "
              "<span class=\"tag\">unverified</span>；在 WP1 复现之前，任何文档、幻灯片、群消息都不得把它写成结论。",
    "h_graph": "1. 依赖图",
    "legend": ["关键路径（不可压缩）", "可并行 / 独立", "虚线＝接口依赖，不是时间依赖"],
    "h_gantt": "2. 八天时间表（谁在第几天动）",
    "gantt_head": ["人", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"],
    "gantt": [
        ("P1 组长", ["WP0", "WP0 定死", "验收", "验收", "验收", "论文", "论文", "论文"], "c1"),
        ("P2 策略", ["读码", "belief 特征", "WP1", "WP1", "G0", "O1: 种子", "O1: 种子", "WP4"], "c2"),
        ("P3 环境", ["WP2 冻结", "schema", "适配器", "适配器", "G1 数据", "G1", "G1", "G1 表"], "c3"),
        ("P4 基线", ["WP3 调研", "WP3 调研", "WP3 实现", "WP3 实现", "WP3 实现", "WP4", "WP4", "WP4 表"], "c5"),
        ("P5 你", ["WP5 调研", "schema", "许可核实", "许可核实", "WP5 交付", "G1 数据", "写作", "写作"], "c2"),
    ],
    "h_people": "3. 五个人，各自交什么",
    "cards": [
        ("WP0", "P1 · 组长 / 协议", "唯一职责：让所有人的数字可比",
         ["<code>eval.py</code>：唯一的 recall / CI 实现",
          "表头模板 + 种子协议 + 配对规则",
          "退回没有 CI 或没有脚本路径的表"],
         "验收：别人 import 你的 eval，不复制你的代码。D2 前定死。"),
        ("WP1", "P2 · 策略梯度", "回答一个问题：RL 输在表示，还是输在信用分配",
         ["belief / static / observed / belief greedy 四路",
          "5 种子 × 200 held-out × 配对 bootstrap",
          "每种子数字全部公开，不报最好的那个"],
         "验收：一条命令出一张表；成立或不成立都算交付。<br>阻塞于：WP2 冻结。"),
        ("WP2", "P3 · 环境", "卡点本人：环境一动，全部数字作废",
         ["合成生成器打 tag 冻结",
          "定义迁移数据集的 item schema",
          "写 KAIST 适配器"],
         "验收：<code>--dataset kaist</code> 一条命令跑通；冻结后改环境 = 新版本 + 重跑全部表。"),
        ("WP3 · WP4", "P4 · 基线 / 对照", "先调研，再实现两个；Option 2 时做诊断",
         ["5 个候选：VOI、MCTS、BC、离线 RL、Transformer",
          "实现最便宜的两个，接同一 harness",
          "诊断：信用分配相关性、回报方差、四个干预"],
         "验收：一页对比表（fit/effort/risk）+ 两个能跑的基线。"),
        ("WP5", "P5 · 你 / 数据", "唯一真正独立的活，但决定能不能 generalize",
         ["KAIST → GO → Manchester，逐个核实许可与字段",
          "打开真实文件，不看摘要",
          "数据不进 repo，只进聚合"],
         "验收：每行都有可验证的 license + 能跑的加载命令。"),
    ],
    "h_interfaces": "4. 第 2 天前必须定死的四个接口",
    "if_head": ["接口", "owner", "用的人", "定不死的后果"],
    "interfaces": [
        ("<code>eval.py</code>", "P1", "P2/P3/P4/P5", "两套分母，最后一周数字对不上"),
        ("item schema（unit/type/label/edge/cost）", "P2+P5", "适配器、G1、G2", "数据集要的字段模拟器表达不了，冻结后被迫改环境"),
        ("环境 tag + 种子协议", "P3", "所有实验", "验证通过后环境被改，全部表作废"),
        ("表格模板（列 / CI 规则 / 脚本路径）", "P1", "所有报告", "每人一张表，无法合并"),
    ],
    "h_gates": "5. 三道闸门",
    "gates": [
        ("red", "G0 · D5 · 决定整份作业的写法。",
         "belief 特征喂进 RL 后：追平 → <b>Option 1</b>（RL 是方法）；仍落后 → <b>Option 2</b>（信用分配是原因，分析即结果）。"),
        ("green", "G1 · D6–8 · 换一个睡眠队列。",
         "同一张表、同一个脚本。排序重复（type ≫ within-type）才算迁移。"),
        ("green", "G2 · 课后 · 换生物单元（GO）。",
         "真正检验「方法是否只对时间戳有效」。"),
    ],
    "footer": "Plan · 2026-11-09 · 数字口径见 <a href=\"GENERALIZATION_PLAN.md\">GENERALIZATION_PLAN.md</a> · "
              "RL 细节见 <a href=\"RL_PLAN.md\">RL_PLAN.md</a> · "
              "<span class=\"tag\">unverified</span> 标记沿用仓库第 12 节纪律",
    "svg": {
        "wp0": "WP0 协议 + harness", "wp2": "WP2 冻结环境", "wp1": "WP1 复现验证",
        "g0": "G0 决策", "g0s": "day 5", "paper": "论文 / 幻灯片",
        "wp5": "WP5 数据集调研", "wp5s": "P5 · day 1–5 · 独立",
        "adapter": "适配器", "adapters": "P5+P3 · schema",
        "g1": "G1 睡眠 B", "g1s": "day 6–8", "g2": "G2 GO", "g2s": "之后",
        "wp3": "WP3 模型调研", "wp3s": "P4 · day 1–2 · 独立",
        "wp3i": "WP3 实现 2 个", "wp3is": "P4 · day 3–8",
        "wp4": "WP4 诊断", "wp4s": "P4+P2 · 仅 Option 2",
        "schema": "item schema",
    },
}


def svg(lg: dict) -> str:
    s = lg["svg"]
    return f'''<svg viewBox="0 0 900 330" role="img" aria-label="dependency graph">
  <defs>
    <marker id="aRed" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#c0392b"/></marker>
    <marker id="aGray" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#8b949e"/></marker>
    <marker id="aGreen" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#1a9850"/></marker>
  </defs>
  <rect x="14" y="24" width="150" height="56" rx="8" fill="#fdecea" stroke="#c0392b" stroke-width="2"/>
  <text x="89" y="46" text-anchor="middle" font-size="12" font-weight="700">{s['wp0']}</text>
  <text x="89" y="63" text-anchor="middle" font-size="11" fill="#57606a">P1 · day 1–2</text>
  <rect x="204" y="24" width="150" height="56" rx="8" fill="#fdecea" stroke="#c0392b" stroke-width="2"/>
  <text x="279" y="46" text-anchor="middle" font-size="12" font-weight="700">{s['wp2']}</text>
  <text x="279" y="63" text-anchor="middle" font-size="11" fill="#57606a">P3 · day 1–2</text>
  <rect x="394" y="24" width="150" height="56" rx="8" fill="#fdecea" stroke="#c0392b" stroke-width="2"/>
  <text x="469" y="46" text-anchor="middle" font-size="12" font-weight="700">{s['wp1']}</text>
  <text x="469" y="63" text-anchor="middle" font-size="11" fill="#57606a">P2 · day 3–5</text>
  <rect x="584" y="24" width="120" height="56" rx="8" fill="#c0392b"/>
  <text x="644" y="46" text-anchor="middle" font-size="12" font-weight="700" fill="#fff">{s['g0']}</text>
  <text x="644" y="63" text-anchor="middle" font-size="10.5" fill="#fdecea">{s['g0s']}</text>
  <rect x="744" y="24" width="140" height="56" rx="8" fill="#fdecea" stroke="#c0392b" stroke-width="2"/>
  <text x="814" y="46" text-anchor="middle" font-size="12" font-weight="700">{s['paper']}</text>
  <text x="814" y="63" text-anchor="middle" font-size="11" fill="#57606a">P1 · day 6+</text>
  <line x1="164" y1="52" x2="200" y2="52" stroke="#c0392b" stroke-width="2.5" marker-end="url(#aRed)"/>
  <line x1="354" y1="52" x2="390" y2="52" stroke="#c0392b" stroke-width="2.5" marker-end="url(#aRed)"/>
  <line x1="544" y1="52" x2="580" y2="52" stroke="#c0392b" stroke-width="2.5" marker-end="url(#aRed)"/>
  <line x1="704" y1="52" x2="740" y2="52" stroke="#c0392b" stroke-width="2.5" marker-end="url(#aRed)"/>
  <rect x="14" y="140" width="150" height="56" rx="8" fill="#e8f5e9" stroke="#1a9850" stroke-width="2"/>
  <text x="89" y="162" text-anchor="middle" font-size="12" font-weight="700">{s['wp5']}</text>
  <text x="89" y="179" text-anchor="middle" font-size="11" fill="#57606a">{s['wp5s']}</text>
  <rect x="204" y="140" width="150" height="56" rx="8" fill="#fff" stroke="#8b949e" stroke-dasharray="4 3"/>
  <text x="279" y="162" text-anchor="middle" font-size="12" font-weight="700">{s['adapter']}</text>
  <text x="279" y="179" text-anchor="middle" font-size="11" fill="#57606a">{s['adapters']}</text>
  <rect x="394" y="140" width="120" height="56" rx="8" fill="#fff" stroke="#1a9850"/>
  <text x="454" y="162" text-anchor="middle" font-size="12" font-weight="700">{s['g1']}</text>
  <text x="454" y="179" text-anchor="middle" font-size="11" fill="#57606a">{s['g1s']}</text>
  <rect x="554" y="140" width="120" height="56" rx="8" fill="#fff" stroke="#1a9850"/>
  <text x="614" y="162" text-anchor="middle" font-size="12" font-weight="700">{s['g2']}</text>
  <text x="614" y="179" text-anchor="middle" font-size="11" fill="#57606a">{s['g2s']}</text>
  <line x1="164" y1="168" x2="200" y2="168" stroke="#1a9850" stroke-width="2" marker-end="url(#aGreen)"/>
  <line x1="354" y1="168" x2="390" y2="168" stroke="#1a9850" stroke-width="2" marker-end="url(#aGreen)"/>
  <line x1="514" y1="168" x2="550" y2="168" stroke="#1a9850" stroke-width="2" marker-end="url(#aGreen)"/>
  <line x1="279" y1="80" x2="279" y2="136" stroke="#8b949e" stroke-width="1.5" stroke-dasharray="4 3" marker-end="url(#aGray)"/>
  <text x="270" y="112" text-anchor="end" font-size="10" fill="#8b949e">{s['schema']}</text>
  <path d="M 700 80 L 700 278 L 740 278" fill="none" stroke="#8b949e" stroke-width="1.5" stroke-dasharray="4 3" marker-end="url(#aGray)"/>
  <rect x="14" y="250" width="150" height="56" rx="8" fill="#e8f5e9" stroke="#1a9850" stroke-width="2"/>
  <text x="89" y="272" text-anchor="middle" font-size="12" font-weight="700">{s['wp3']}</text>
  <text x="89" y="289" text-anchor="middle" font-size="11" fill="#57606a">{s['wp3s']}</text>
  <rect x="204" y="250" width="150" height="56" rx="8" fill="#fff" stroke="#8b949e" stroke-dasharray="4 3"/>
  <text x="279" y="272" text-anchor="middle" font-size="12" font-weight="700">{s['wp3i']}</text>
  <text x="279" y="289" text-anchor="middle" font-size="11" fill="#57606a">{s['wp3is']}</text>
  <line x1="164" y1="278" x2="200" y2="278" stroke="#1a9850" stroke-width="2" marker-end="url(#aGreen)"/>
  <rect x="744" y="250" width="140" height="56" rx="8" fill="#fff" stroke="#8b949e" stroke-dasharray="4 3"/>
  <text x="814" y="272" text-anchor="middle" font-size="12" font-weight="700">{s['wp4']}</text>
  <text x="814" y="289" text-anchor="middle" font-size="11" fill="#57606a">{s['wp4s']}</text>
</svg>'''


def block(lang: str, lg: dict, default: bool) -> str:
    stats = "".join(f'<div class="stat"><div class="n">{n}</div><div class="l">{t}</div></div>'
                    for n, t in lg["stats"])
    legend = "".join(
        f'<span><i style="background:{c}"></i>{t}</span>'
        for c, t in zip(("#c0392b", "#1a9850", "#8b949e"), lg["legend"]))
    head = "".join(f"<th>{h}</th>" for h in lg["gantt_head"])
    rows = ""
    for name, cells, cls in lg["gantt"]:
        tds = "".join(f'<td class="{cls}">{c}</td>' for c in cells)
        rows += f'<tr><td class="name">{name}</td>{tds}</tr>'
    cards = ""
    for wp, title, role, bullets, acc in lg["cards"]:
        lis = "".join(f"<li>{b}</li>" for b in bullets)
        cards += (f'<div class="pcard"><span class="wp">{wp}</span><h3>{title}</h3>'
                  f'<div class="role">{role}</div><ul>{lis}</ul>'
                  f'<div class="acc">{acc}</div></div>')
    ifh = "".join(f"<th>{h}</th>" for h in lg["if_head"])
    ifr = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>"
                  for a, b, c, d in lg["interfaces"])
    gates = "".join(f'<div class="box {k}"><b>{t}</b> {b}</div>' for k, t, b in lg["gates"])
    show = " show" if default else ""
    return f'''<div class="lang-block{show}" id="lang-{lang}">
<h1>{lg["title"]}</h1>
<p class="lead">{lg["lead"]}</p>
<div class="stats">{stats}</div>
<div class="box amber">{lg["banner"]}</div>

<h2>{lg["h_graph"]}</h2>
<div class="graph">{svg(lg)}</div>
<div class="legend">{legend}</div>

<h2>{lg["h_gantt"]}</h2>
<table class="gantt"><tr>{head}</tr>{rows}</table>

<h2>{lg["h_people"]}</h2>
<div class="cards">{cards}</div>

<h2>{lg["h_interfaces"]}</h2>
<table><tr>{ifh}</tr>{ifr}</table>

<h2>{lg["h_gates"]}</h2>
{gates}

<footer>{lg["footer"]}</footer>
</div>'''


CSS = """
  * { box-sizing: border-box; margin: 0; }
  body { font-family: -apple-system, "Segoe UI", "Noto Sans", "PingFang SC", "Noto Sans KR", sans-serif;
         background: #f6f8fa; color: #1f2328; line-height: 1.65; }
  .nav { position: sticky; top: 0; z-index: 10; display: flex; align-items: center;
         justify-content: space-between; background: #0d1117; color: #fff; padding: 10px 20px; }
  .nav .title { font-weight: 700; font-size: 0.95em; }
  .nav a { color: #c9d1d9; text-decoration: none; }
  .nav .langs a { padding: 4px 10px; border-radius: 16px; font-size: 0.85em;
                  border: 1px solid #30363d; margin-left: 6px; }
  .lang-tabs { display: flex; gap: 8px; max-width: 980px; margin: 14px auto 0; padding: 0 16px; }
  .lang-tabs button { border: 1px solid #d0d7de; background: #fff; color: #1f2328; padding: 6px 16px;
                      border-radius: 16px; cursor: pointer; font-size: 0.9em; }
  .lang-tabs button.active { background: #1a9850; color: #fff; border-color: #1a9850; }
  .lang-block { display: none; max-width: 980px; margin: 0 auto; padding: 18px 16px 40px; }
  .lang-block.show { display: block; }
  h1 { font-size: 1.6em; margin: 6px 0 6px; }
  h2 { font-size: 1.18em; margin: 30px 0 12px; padding-bottom: 6px; border-bottom: 1px solid #eaeef2; }
  p { margin: 10px 0; }
  .lead { font-size: 1.03em; color: #57606a; }
  .box { background: #fff; border-radius: 10px; padding: 14px 18px; margin: 14px 0; border: 1px solid #eaeef2; }
  .box.green { background: #e8f5e9; border-left: 4px solid #1a9850; }
  .box.red { background: #fdecea; border-left: 4px solid #c0392b; }
  .box.amber { background: #fff8ec; border-left: 4px solid #fdae61; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 16px 0 4px; }
  .stat { background: #fff; border: 1px solid #eaeef2; border-radius: 10px; padding: 14px 16px; }
  .stat .n { font-size: 1.7em; font-weight: 700; line-height: 1.1; }
  .stat .l { font-size: 0.85em; color: #57606a; }
  .graph { background: #fff; border: 1px solid #eaeef2; border-radius: 10px; padding: 8px; overflow-x: auto; }
  svg { display: block; width: 100%; height: auto; }
  .legend { display: flex; gap: 18px; flex-wrap: wrap; font-size: 0.85em; color: #57606a; margin-top: 8px; }
  .legend i { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }
  table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 0.92em; background: #fff; }
  th, td { padding: 8px 10px; border-bottom: 1px solid #eaeef2; text-align: left; vertical-align: top; }
  th { background: #f6f8fa; font-weight: 600; }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 14px; margin-top: 12px; }
  .pcard { background: #fff; border: 1px solid #eaeef2; border-radius: 10px; padding: 16px; }
  .pcard h3 { font-size: 1em; margin: 0 0 2px; }
  .pcard .role { font-size: 0.84em; color: #57606a; margin-bottom: 10px; }
  .pcard .wp { display: inline-block; background: #0d1117; color: #fff; border-radius: 6px; padding: 2px 8px; font-size: 0.78em; margin-bottom: 8px; }
  .pcard ul { padding-left: 18px; margin: 6px 0; font-size: 0.9em; }
  .pcard .acc { font-size: 0.84em; color: #1a5e20; background: #e8f5e9; border-radius: 6px; padding: 8px 10px; margin-top: 8px; }
  .gantt td, .gantt th { text-align: center; padding: 6px 4px; font-size: 0.82em; }
  .gantt td.name { text-align: left; font-weight: 600; white-space: nowrap; }
  .c1 { background: #e3f2fd; } .c2 { background: #e8f5e9; } .c3 { background: #fff3e0; }
  .c4 { background: #f3e5f5; } .c5 { background: #fce4ec; }
  .gate { background: #c0392b; color: #fff; font-weight: 700; }
  .tag { display: inline-block; background: #eef2f6; color: #30363d; border-radius: 12px; padding: 2px 10px; font-size: 0.8em; margin: 2px 4px 2px 0; }
  footer { text-align: center; color: #57606a; font-size: 0.85em; padding: 24px 0 40px; }
  code { background: #eef2f6; padding: 1px 6px; border-radius: 4px; font-size: 0.88em; }
  a { color: #2a7de1; }
"""

HTML = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Plan — 5 people, one critical path / 다섯 명, 하나의 임계 경로 / 五个人，一条关键路径</title>
<link rel="icon" type="image/x-icon" href="favicon.ico">
<style>{CSS}</style>
</head>
<body>

<nav class="nav">
  <div class="title"><a href="index.html">📊 Plan</a></div>
  <div class="langs">
    <a href="index.html">Home</a>
    <a href="GENERALIZATION_PLAN.md">Markdown</a>
    <a href="RL_PLAN.md">RL plan</a>
    <a href="TEAM_CLAIMS.html">Claims</a>
  </div>
</nav>

<div class="lang-tabs">
  <button class="active" onclick="setLang('en', this)">English</button>
  <button onclick="setLang('ko', this)">한국어</button>
  <button onclick="setLang('zh', this)">中文</button>
</div>

{block("en", L["en"], True)}
{block("ko", L["ko"], False)}
{block("zh", L["zh"], False)}

<script>
function setLang(lang, btn) {{
  document.querySelectorAll('.lang-block').forEach(el => el.classList.remove('show'));
  document.getElementById('lang-' + lang).classList.add('show');
  document.querySelectorAll('.lang-tabs button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.documentElement.lang = lang;
}}
</script>
</body>
</html>
'''

(ROOT / "PLAN.html").write_text(HTML)
print("wrote PLAN.html", len(HTML), "bytes")
