#!/usr/bin/env python3
"""Generate the trilingual GENERALIZATION_PLAN.html and RL_PLAN.html.

Both pages share the tab pattern used by talk.html and PLAN.html. Content is kept
condensed here; the .md files remain the full source of record.

    python3 tools/build_docs.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CSS = open(ROOT / "tools" / "_page_style.css", encoding="utf-8").read()

SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<link rel="icon" type="image/x-icon" href="favicon.ico">
<style>__CSS__</style>
</head>
<body>
<nav class="nav">
  <div class="title"><a href="index.html">__NAV__</a></div>
  <div class="langs">
    <a href="index.html">Home</a>
    <a href="PLAN.html">Plan</a>
    <a href="GENERALIZATION_PLAN.html">Generalization</a>
    <a href="RL_PLAN.html">RL</a>
    <a href="__MD__">Markdown</a>
  </div>
</nav>
<div class="lang-tabs">
  <button class="active" onclick="setLang('en', this)">English</button>
  <button onclick="setLang('ko', this)">한국어</button>
  <button onclick="setLang('zh', this)">中文</button>
</div>
__BLOCKS__
<script>
function setLang(lang, btn) {
  document.querySelectorAll('.lang-block').forEach(el => el.classList.remove('show'));
  document.getElementById('lang-' + lang).classList.add('show');
  document.querySelectorAll('.lang-tabs button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.documentElement.lang = lang;
}
</script>
</body>
</html>
"""


def block(lang, html, default=False):
    cls = "lang-block show" if default else "lang-block"
    return f'<div class="{cls}" id="lang-{lang}">{html}</div>'


def table(head, rows, cls=""):
    th = "".join(f"<th>{h}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="{cls}"><tr>{th}</tr>{tr}</table>'


def cards(items):
    out = ""
    for wp, title, role, bullets, acc in items:
        lis = "".join(f"<li>{b}</li>" for b in bullets)
        out += (f'<div class="pcard"><span class="wp">{wp}</span><h3>{title}</h3>'
                f'<div class="role">{role}</div><ul>{lis}</ul>'
                f'<div class="acc">{acc}</div></div>')
    return f'<div class="cards">{out}</div>'


# ---------------------------------------------------------------- general page

G = {}

G["en"] = f"""
<h1>Generalization plan — team work packages</h1>
<p class="lead">The goal is not another result on the sleep queue. It is a protocol that
survives a change of cohort and a change of domain.</p>
<div class="box amber"><b>Status: not done, not verified.</b> The belief-conditioned result is a single run.
Nothing below assumes it holds until WP1 reproduces it.</div>

<h2>1. What we believe, and what still needs checking</h2>
{table(["Claim", "Evidence today", "Status"],
       [["Belief-conditioned GNN + REINFORCE is best", "one run, seeds not fixed", "unverified — WP1"],
        ["Belief greedy beats static/observed GNN", "200 held-out graphs, paired CI", "in-repo, needs a second rerun"],
        ["Type partition explains the real queue", "1,048 flags, 68 labels", "in-repo, single lab"]])}

<h2>2. What "generalize" means — three rungs, in order</h2>
{table(["Rung", "Data", "Question", "Why"],
       [["<b>G1</b>", "second sleep cohort (KAIST 1,372/49, CC BY)", "does the row/field structure transfer?", "same schema, different people"],
        ["<b>G2</b>", "GO annotations (IEA vs experimental; GO is a DAG)", "does it transfer to another biological unit?", "real graph, real auto-vs-curator split"],
        ["<b>G3</b>", "clinical, only if licensed", "does it survive a regulated domain?", "highest cost, do last"]])}
<p><b>Operational definition:</b> generalization = the same table, from the same script, with the
same metrics, on a new dataset. If the columns change, it is not a transfer result.</p>
{table(["dataset", "unit", "type ceiling", "within-type gain", "cost gain"],
       [["sleep A", "row/field", "84%", "none", "2×"],
        ["sleep B (G1)", "row", "?", "?", "?"],
        ["GO (G2)", "gene–term", "?", "?", "?"]])}

<h2>3. Work packages</h2>
{cards([
 ("WP0", "P1 · protocol", "One job: make everyone's numbers comparable",
  ["<code>eval.py</code>: the only recall / CI implementation", "table template, seed protocol", "reject any table without a CI or a script path"],
  "Acceptance: others import your eval instead of copying it. Frozen by D2."),
 ("WP1", "P2 · verify", "Does RL lose on representation or on credit assignment?",
  ["belief / static / observed / belief-greedy", "5 seeds × 200 held-out × paired bootstrap", "publish every seed"],
  "Acceptance: one command, one table; a negative result is still a delivery.<br>Blocked by: WP2."),
 ("WP2", "P3 · environment", "The choke point: move it and every number dies",
  ["tag and freeze the generator", "define the item schema", "write the KAIST adapter"],
  "Acceptance: <code>--dataset kaist</code> runs end to end."),
 ("WP3·4", "P4 · baselines", "Survey first, implement two",
  ["VOI, MCTS, BC, offline RL, transformer", "two cheapest on the same harness", "diagnostics only under Option 2"],
  "Acceptance: one-page fit/effort/risk table + two working baselines."),
 ("WP5", "P5 · datasets", "The only truly independent job",
  ["KAIST → GO → Manchester, licence and fields verified", "open the real files", "no data in the repo"],
  "Acceptance: every row has a licence and a load command that runs."),
])}

<h2>4. Rules for every package</h2>
<ul>
<li><b>One table, one script.</b> If a number cannot be regenerated by a command, it does not exist.</li>
<li><b>Paired comparisons only</b>, bootstrap CI, at least 5 seeds.</li>
<li><b>Report the interval, not the winner.</b> Below ~10 pp on the real queue is noise.</li>
<li><b>No dataset in the repo.</b> Code and aggregates only.</li>
<li><b>Status labels:</b> every claim is <code>verified</code> / <code>unverified</code> / <code>retracted</code>.</li>
</ul>

<h2>5. Dependencies, honestly</h2>
<p>Only two tasks are independent: the dataset survey and the reading half of the model survey.
Everything else is on one chain.</p>
{table(["Package", "Blocked by", "Blocks"],
       [["WP0", "—", "all"], ["WP2", "WP0", "WP1, WP3 impl, G1/G2"], ["WP1", "WP2", "the Option 1/2 decision"],
        ["WP4", "WP1 + decision", "—"], ["WP5 adapter", "WP2 schema", "G1"]])}
<div class="box red"><b>Single choke point: the environment freeze.</b> If the simulator changes after
verification, every number invalidates. Changing the environment is a new version and a full rerun.</div>
<p>Parallelism is bought with four interfaces frozen by day 2:
<code>eval.py</code>, the item schema, the env tag + seed protocol, and the table template.</p>
"""

G["ko"] = f"""
<h1>일반화 계획 — 팀 작업 패키지</h1>
<p class="lead">목표는 수면 큐에서 결과를 하나 더 내는 것이 아니라, 코호트와 도메인이 바뀌어도 살아남는
프로토콜을 만드는 것이다.</p>
<div class="box amber"><b>상태: 미완료, 미검증.</b> belief 조건화 결과는 단 한 번의 실행이다.
WP1이 재현하기 전까지 아래 어떤 것도 이를 전제로 하지 않는다.</div>

<h2>1. 우리가 믿는 것, 아직 확인해야 하는 것</h2>
{table(["주장", "현재 증거", "상태"],
       [["belief 조건화 GNN + REINFORCE가 최고", "1회 실행, 시드 미고정", "미검증 — WP1"],
        ["belief greedy가 static/observed GNN을 이김", "200 held-out, 짝지은 CI", "저장소 내, 재현 필요"],
        ["타입 분할이 실제 큐를 설명", "1,048 플래그, 68 라벨", "저장소 내, 단일 실험실"]])}

<h2>2. "일반화"의 정의 — 세 단계</h2>
{table(["단계", "데이터", "질문", "이유"],
       [["<b>G1</b>", "두 번째 수면 코호트 (KAIST 1,372/49, CC BY)", "행/필드 구조가 전이되는가?", "같은 스키마, 다른 사람"],
        ["<b>G2</b>", "GO 주석 (IEA vs 실험; GO는 DAG)", "다른 생물학적 단위로 전이되는가?", "실제 그래프, 자동 대 큐레이터"],
        ["<b>G3</b>", "임상, 라이선스가 있을 때만", "규제 도메인에서도 통하는가?", "비용 최대, 마지막"]])}
<p><b>조작적 정의:</b> 일반화 = 같은 표, 같은 스크립트, 같은 지표, 새 데이터셋. 열이 바뀌면 전이가 아니다.</p>
{table(["데이터셋", "단위", "타입 상한", "타입 내 이득", "비용 이득"],
       [["sleep A", "행/필드", "84%", "없음", "2×"],
        ["sleep B (G1)", "행", "?", "?", "?"],
        ["GO (G2)", "유전자–용어", "?", "?", "?"]])}

<h2>3. 작업 패키지</h2>
{cards([
 ("WP0", "P1 · 프로토콜", "한 가지 일: 모두의 숫자를 비교 가능하게",
  ["<code>eval.py</code>: 유일한 recall / CI 구현", "표 템플릿, 시드 프로토콜", "CI나 스크립트 경로 없는 표는 반려"],
  "검수: 다른 사람이 import 한다. D2까지 확정."),
 ("WP1", "P2 · 검증", "RL은 표현에서 지는가, 크레딧 할당에서 지는가",
  ["belief / static / observed / belief-greedy", "5 시드 × 200 held-out × 짝지은 부트스트랩", "모든 시드 공개"],
  "검수: 한 명령, 한 표; 부정적 결과도 납품.<br>차단: WP2."),
 ("WP2", "P3 · 환경", "병목: 움직이면 모든 숫자가 죽는다",
  ["생성기 동결", "item 스키마 정의", "KAIST 어댑터"],
  "검수: <code>--dataset kaist</code>가 끝까지 실행."),
 ("WP3·4", "P4 · 베이스라인", "먼저 조사, 두 개 구현",
  ["VOI, MCTS, BC, 오프라인 RL, 트랜스포머", "가장 싼 두 개를 같은 harness에", "진단은 Option 2일 때만"],
  "검수: fit/effort/risk 표 + 작동하는 베이스라인 두 개."),
 ("WP5", "P5 · 데이터", "유일하게 진짜 독립인 일",
  ["KAIST → GO → Manchester, 라이선스·필드 확인", "실제 파일을 연다", "데이터는 저장소에 넣지 않는다"],
  "검수: 모든 행에 라이선스와 실행되는 로드 명령."),
])}

<h2>4. 모든 패키지에 적용되는 규칙</h2>
<ul>
<li><b>표 하나, 스크립트 하나.</b> 명령으로 재생성할 수 없는 숫자는 존재하지 않는다.</li>
<li><b>짝지은 비교만</b>, 부트스트랩 CI, 최소 5 시드.</li>
<li><b>승자가 아니라 구간을 보고하라.</b> 실제 큐에서 ~10pp 이하는 노이즈다.</li>
<li><b>데이터는 저장소에 넣지 않는다.</b> 코드와 집계만.</li>
<li><b>상태 표기:</b> 모든 주장은 <code>verified</code> / <code>unverified</code> / <code>retracted</code>.</li>
</ul>

<h2>5. 의존성, 정직하게</h2>
<p>독립은 두 개뿐이다: 데이터셋 조사, 그리고 모델 조사의 문헌 읽기 부분. 나머지는 한 사슬 위에 있다.</p>
{table(["패키지", "차단", "차단하는 것"],
       [["WP0", "—", "전부"], ["WP2", "WP0", "WP1, WP3 구현, G1/G2"], ["WP1", "WP2", "Option 1/2 결정"],
        ["WP4", "WP1 + 결정", "—"], ["WP5 어댑터", "WP2 스키마", "G1"]])}
<div class="box red"><b>단일 병목: 환경 동결.</b> 검증 후 시뮬레이터가 바뀌면 모든 숫자가 무효다.
환경 변경은 새 버전 + 전면 재실행이다.</div>
<p>병렬성은 2일 차까지 고정하는 네 인터페이스로 산다:
<code>eval.py</code>, item 스키마, 환경 태그 + 시드 프로토콜, 표 템플릿.</p>
"""

G["zh"] = f"""
<h1>泛化计划 —— 团队工作包</h1>
<p class="lead">目标不是在睡眠队列上再出一个结果，而是一个换队列、换领域都还成立的协议。</p>
<div class="box amber"><b>状态：未完成，未验证。</b>belief 条件化结果只是一次运行。
在 WP1 复现之前，下面任何内容都不以它为前提。</div>

<h2>1. 我们相信什么，还需要查什么</h2>
{table(["主张", "现有证据", "状态"],
       [["belief 条件化 GNN + REINFORCE 最好", "一次运行，种子未固定", "未验证 — WP1"],
        ["belief greedy 赢 static/observed GNN", "200 held-out，配对 CI", "仓库内有，需第二人重跑"],
        ["类型分区解释真实队列", "1,048 flag，68 标签", "仓库内有，单实验室"]])}

<h2>2.「泛化」的定义 —— 三级</h2>
{table(["级", "数据", "问题", "为什么"],
       [["<b>G1</b>", "第二个睡眠队列（KAIST 1,372/49，CC BY）", "行/字段结构能否迁移？", "同 schema，不同的人"],
        ["<b>G2</b>", "GO 注释（IEA vs 实验；GO 本身是 DAG）", "能否迁移到另一种生物单元？", "真图，真「自动 vs 人工」"],
        ["<b>G3</b>", "临床，有许可才做", "监管领域还成立吗？", "成本最高，放最后"]])}
<p><b>操作性定义：</b>泛化 = 同一张表、同一个脚本、同一套指标，换数据集。列变了就不算迁移。</p>
{table(["数据集", "unit", "类型天花板", "组内增益", "成本增益"],
       [["sleep A", "行/字段", "84%", "无", "2×"],
        ["sleep B (G1)", "行", "?", "?", "?"],
        ["GO (G2)", "基因–词条", "?", "?", "?"]])}

<h2>3. 工作包</h2>
{cards([
 ("WP0", "P1 · 协议", "唯一职责：让所有人的数字可比",
  ["<code>eval.py</code>：唯一的 recall / CI 实现", "表模板、种子协议", "没 CI 或没脚本路径的表一律退回"],
  "验收：别人 import 你的 eval。D2 前定死。"),
 ("WP1", "P2 · 验证", "RL 输在表示，还是输在信用分配",
  ["belief / static / observed / belief-greedy", "5 种子 × 200 held-out × 配对 bootstrap", "每种子都公开"],
  "验收：一条命令一张表；负结果也算交付。<br>阻塞：WP2。"),
 ("WP2", "P3 · 环境", "卡点：一动，全部数字作废",
  ["生成器打 tag 冻结", "定义 item schema", "写 KAIST 适配器"],
  "验收：<code>--dataset kaist</code> 跑通。"),
 ("WP3·4", "P4 · 基线", "先调研，再实现两个",
  ["VOI、MCTS、BC、离线 RL、Transformer", "最便宜的两个接同一 harness", "诊断只在 Option 2 时做"],
  "验收：一页 fit/effort/risk 表 + 两个能跑的基线。"),
 ("WP5", "P5 · 数据", "唯一真正独立的活",
  ["KAIST → GO → Manchester，核实许可与字段", "打开真实文件", "数据不进 repo"],
  "验收：每行都有许可 + 能跑的加载命令。"),
])}

<h2>4. 适用于每个包的规矩</h2>
<ul>
<li><b>一表一脚本。</b>不能用命令重新生成的数字，等于不存在。</li>
<li><b>只做配对比较</b>，bootstrap CI，至少 5 种子。</li>
<li><b>报区间，不报赢家。</b>真实队列上 ~10pp 以内是噪声。</li>
<li><b>数据不进仓库。</b>只放代码和聚合。</li>
<li><b>状态标签：</b>每条主张只能是 <code>verified</code> / <code>unverified</code> / <code>retracted</code>。</li>
</ul>

<h2>5. 依赖，说实话</h2>
<p>独立的只有两个：数据集调研、模型调研的文献部分。其余都在一条链上。</p>
{table(["包", "被谁阻塞", "阻塞谁"],
       [["WP0", "—", "全部"], ["WP2", "WP0", "WP1、WP3 实现、G1/G2"], ["WP1", "WP2", "Option 1/2 决策"],
        ["WP4", "WP1 + 决策", "—"], ["WP5 适配器", "WP2 schema", "G1"]])}
<div class="box red"><b>唯一卡点：环境冻结。</b>验证之后环境再动，所有数字作废。改环境 = 新版本 + 全量重跑。</div>
<p>并行靠第 2 天前定死的四个接口买来：<code>eval.py</code>、item schema、环境 tag + 种子协议、表模板。</p>
"""

# --------------------------------------------------------------------- rl page

R = {}

R["en"] = f"""
<h1>The RL plan, in detail</h1>
<p class="lead">Course-facing only. No external partner, no restricted data, every number from one script.</p>

<h2>1. G0 — the experiment that decides the paper</h2>
<p>Give the policy the belief posterior (marginal, entropy, reviewed mask) so it sees exactly what
belief greedy sees. Everything else unchanged.</p>
{table(["G0 result", "Reading", "Course claim"],
       [["RL ≥ belief greedy (CI excludes 0)", "the loss was representation", "<b>Option 1</b> — RL is the method"],
        ["RL < belief greedy", "the loss is credit assignment", "<b>Option 2</b> — the analysis is the result"]])}

<h2>2. MDP, stated once</h2>
{table(["Element", "Definition"],
       [["State", "per node: type, confidence, downstream count, reviewed mask, budget left; <b>belief variant adds</b> posterior marginal and entropy"],
        ["Action", "pick an unreviewed node, or stop"],
        ["Transition", "review → observation (flagged w.p. <code>p_catch</code>) → fix only at the source; recompute descendants"],
        ["Reward", "terminal only: −(# wrong sinks). Variants: potential shaping, n-step"],
        ["Horizon", "budget B (80-node: 16), γ &lt; 1"]])}

<h2>3. What gets compared</h2>
{table(["Class", "Policy", "Role"],
       [["baselines", "no review / random / threshold / structural greedy", "traditional"],
        ["model-based", "<b>belief greedy</b>", "the one to beat"],
        ["model-free", "REINFORCE (MLP), PPO, DQN", "preliminary / control"],
        ["graph", "GNN + REINFORCE (static / observed)", "upgrade path"],
        ["constrained", "CMDP + PPO-Lagrangian (naive)", "negative result"],
        ["new", "<b>GNN + REINFORCE, belief-conditioned</b>", "G0"],
        ["ceiling", "oracle greedy", "upper bound"]])}

<h2>4. Experiment matrix</h2>
{table(["Axis", "Levels"],
       [["environment", "80-node synthetic (main), N=500 modular/BA/ER (heuristics), N=21 real pipeline"],
        ["seeds", "5 training seeds × 20k episodes"],
        ["evaluation", "200 held-out graphs, paired by graph, bootstrap CI"],
        ["state ablation", "static / observed / belief"],
        ["reward ablation", "terminal only / potential shaping / n-step (3, 5)"],
        ["budget", "8, 16, 32 (eval only)"]])}
<p><b>Reporting rule.</b> Every comparison is a paired difference with a CI. A point estimate without a
CI does not enter the paper — five seeds already fooled us once.</p>

<h2>5. If RL loses: four diagnostics</h2>
<ol>
<li><b>Credit assignment.</b> Correlation between per-step advantage and the action's realized contribution.</li>
<li><b>Return variance.</b> Terminal-only reward over a 16-step horizon at fixed policy.</li>
<li><b>Interventions.</b> Potential shaping, n-step, batch size, 100k episodes.</li>
<li><b>Information control.</b> Already covered by G0.</li>
</ol>
<p>The write-up becomes: policy gradient fails here because X, and here are three tests that would have falsified X.</p>

<h2>6. Timeline to 12/05</h2>
{table(["Week", "Work", "Gate"],
       [["11/10–11/16", "G0 run; freeze environment", "G0 decided"],
        ["11/17–11/23", "diagnostics or seed tightening; one transfer set", "every table from one script"],
        ["11/24–11/30", "draft, figures, ceiling section", "draft complete"],
        ["12/01–12/05", "slides, ≥2 rehearsals", "talk delivered"]])}

<h2>7. Definition of done</h2>
<p><b>Option 1:</b> belief-conditioned RL beats belief greedy on 200 held-out graphs, paired CI excluding 0,
5 seeds, and the gain survives the state ablation.<br>
<b>Option 2:</b> a named mechanism, at least one intervention that moves RL toward parity or provably
cannot, and the information control reported.</p>

<h2>Appendix — public datasets worth testing</h2>
{table(["Dataset", "Unit", "Fit", "Gap"],
       [["<b>SYNERGY</b> (ASReview)", "record", "best for the screening task: fully labelled, many fields", "no graph, no cost"],
        ["<b>GO annotations</b> (IEA vs experimental)", "gene–term", "best for the DAG story and the real auto-vs-curator split", "no cost"],
        ["KAIST / Manchester diaries", "row", "does the row/field structure transfer?", "labels must be built"],
        ["GitHub code review (HF)", "PR/hunk", "the AI-review narrative", "no correctness labels"],
        ["FEVER / Bugzilla", "claim / issue", "other flavours", "not review scheduling"]])}
"""

R["ko"] = f"""
<h1>RL 계획, 상세</h1>
<p class="lead">과정용. 외부 파트너 없음, 제한 데이터 없음, 모든 숫자는 하나의 스크립트에서.</p>

<h2>1. G0 — 논문의 방향을 결정하는 실험</h2>
<p>정책에 belief 사후분포(주변확률, 엔트로피, 검토 마스크)를 준다. belief greedy가 보는 것과 동일하게.</p>
{table(["G0 결과", "해석", "과정 주장"],
       [["RL ≥ belief greedy (CI가 0 제외)", "손실은 표현 문제", "<b>Option 1</b> — RL이 방법"],
        ["RL < belief greedy", "손실은 크레딧 할당", "<b>Option 2</b> — 분석이 결과"]])}

<h2>2. MDP</h2>
{table(["요소", "정의"],
       [["상태", "노드별: 타입, 신뢰도, 하류 수, 검토 마스크, 남은 예산; <b>belief 변형은</b> 사후 주변확률과 엔트로피 추가"],
        ["행동", "미검토 노드 선택 또는 종료"],
        ["전이", "검토 → 관측(<code>p_catch</code>로 flagged) → 원인 노드만 수정; 하류 재계산"],
        ["보상", "종료 시점만: −(잘못된 sink 수). 변형: potential shaping, n-step"],
        ["지평", "예산 B (80노드: 16), γ &lt; 1"]])}

<h2>3. 비교 대상</h2>
{table(["분류", "정책", "역할"],
       [["베이스라인", "무검토 / 무작위 / 임계값 / 구조적 탐욕", "전통"],
        ["모델 기반", "<b>belief greedy</b>", "이겨야 할 대상"],
        ["모델 프리", "REINFORCE (MLP), PPO, DQN", "예비 / 대조"],
        ["그래프", "GNN + REINFORCE (static / observed)", "업그레이드 경로"],
        ["제약", "CMDP + PPO-Lagrangian (naive)", "부정적 결과"],
        ["신규", "<b>GNN + REINFORCE, belief 조건화</b>", "G0"],
        ["상한", "oracle greedy", "상한"]])}

<h2>4. 실험 매트릭스</h2>
{table(["축", "수준"],
       [["환경", "80노드 합성(주), N=500 modular/BA/ER(휴리스틱), N=21 실제 파이프라인"],
        ["시드", "학습 5 시드 × 20k 에피소드"],
        ["평가", "200 held-out 그래프, 그래프 단위 짝지음, 부트스트랩 CI"],
        ["상태 소거", "static / observed / belief"],
        ["보상 소거", "종료만 / potential shaping / n-step (3, 5)"],
        ["예산", "8, 16, 32 (평가만)"]])}
<p><b>보고 규칙.</b> 모든 비교는 CI가 있는 짝지은 차이. CI 없는 점추정은 논문에 넣지 않는다 —
5 시드에 이미 한 번 속았다.</p>

<h2>5. RL이 지면: 네 가지 진단</h2>
<ol>
<li><b>크레딧 할당.</b> 단계별 advantage와 실제 기여의 상관.</li>
<li><b>리턴 분산.</b> 고정 정책에서 16스텝 종료 보상의 분산.</li>
<li><b>개입.</b> potential shaping, n-step, 배치 크기, 100k 에피소드.</li>
<li><b>정보 대조.</b> G0가 이미 처리.</li>
</ol>
<p>서술은 이렇게 된다: 정책 경사는 여기서 X 때문에 실패하며, X를 반증했을 세 가지 검사를 함께 보고한다.</p>

<h2>6. 12/05까지 일정</h2>
{table(["주", "작업", "관문"],
       [["11/10–11/16", "G0 실행, 환경 동결", "G0 확정"],
        ["11/17–11/23", "진단 또는 시드 강화, 전이 하나", "모든 표가 한 스크립트에서"],
        ["11/24–11/30", "초안, 그림, 상한 절", "초안 완성"],
        ["12/01–12/05", "슬라이드, 2회 이상 리허설", "발표"]])}

<h2>7. 완료의 정의</h2>
<p><b>Option 1:</b> 200 held-out에서 belief 조건화 RL이 belief greedy를 이기고, 짝지은 CI가 0을 제외,
5 시드, 이득이 상태 소거 후에도 유지.<br>
<b>Option 2:</b> 명명된 기제, RL을 동등 수준으로 옮기는 개입 최소 하나(또는 불가능함의 증명),
그리고 정보 대조 보고.</p>

<h2>부록 — 시험해 볼 공개 데이터셋</h2>
{table(["데이터셋", "단위", "적합성", "결핍"],
       [["<b>SYNERGY</b> (ASReview)", "레코드", "스크리닝 과제에 최적: 완전 라벨, 다분야", "그래프·비용 없음"],
        ["<b>GO 주석</b> (IEA vs 실험)", "유전자–용어", "DAG 이야기와 실제 자동 대 큐레이터", "비용 없음"],
        ["KAIST / Manchester", "행", "행/필드 구조 전이 여부", "라벨을 만들어야 함"],
        ["GitHub 코드 리뷰 (HF)", "PR/hunk", "AI 리뷰 서사", "정답 라벨 없음"],
        ["FEVER / Bugzilla", "주장 / 이슈", "다른 결", "리뷰 스케줄링 아님"]])}
"""

R["zh"] = f"""
<h1>强化学习计划（细化）</h1>
<p class="lead">只面向课程。无外部合作方、无受限数据、每个数字来自一个脚本。</p>

<h2>1. G0 —— 决定整篇写法的实验</h2>
<p>把 belief 后验（边际概率、熵、已审掩码）喂给策略，让它看到的和 belief greedy 完全一样。</p>
{table(["G0 结果", "解释", "课程主张"],
       [["RL ≥ belief greedy（CI 排除 0）", "之前输是表示问题", "<b>Option 1</b> — RL 是方法"],
        ["RL < belief greedy", "输是信用分配", "<b>Option 2</b> — 分析即结果"]])}

<h2>2. MDP</h2>
{table(["要素", "定义"],
       [["状态", "每节点：类型、置信度、下游数、已审掩码、剩余预算；<b>belief 变体加</b>后验边际与熵"],
        ["行动", "选未审节点，或停止"],
        ["转移", "审阅 → 观测（以 <code>p_catch</code> 报错）→ 只修源头；重算下游"],
        ["奖励", "仅终局：−（错误 sink 数）。变体：potential shaping、n-step"],
        ["时间跨度", "预算 B（80 节点：16），γ &lt; 1"]])}

<h2>3. 对比对象</h2>
{table(["类别", "策略", "角色"],
       [["基线", "不审 / 随机 / 阈值 / 结构贪心", "传统"],
        ["模型基", "<b>belief greedy</b>", "要打赢的对象"],
        ["无模型", "REINFORCE (MLP)、PPO、DQN", "初步 / 对照"],
        ["图", "GNN + REINFORCE（static / observed）", "升级路径"],
        ["约束", "CMDP + PPO-Lagrangian（naive）", "负结果"],
        ["新", "<b>GNN + REINFORCE，belief 条件化</b>", "G0"],
        ["上界", "oracle greedy", "上界"]])}

<h2>4. 实验矩阵</h2>
{table(["轴", "水平"],
       [["环境", "80 节点合成（主）、N=500 modular/BA/ER（启发式）、N=21 真实管道"],
        ["种子", "5 个训练种子 × 20k episode"],
        ["评估", "200 张 held-out 图，按图配对，bootstrap CI"],
        ["状态消融", "static / observed / belief"],
        ["奖励消融", "仅终局 / potential shaping / n-step（3、5）"],
        ["预算", "8、16、32（仅评估）"]])}
<p><b>报告规则。</b>所有比较都是带 CI 的配对差。没有 CI 的点估计不进论文——5 个种子已经骗过我们一次。</p>

<h2>5. 如果 RL 输了：四个诊断</h2>
<ol>
<li><b>信用分配。</b>每步 advantage 与该步实际贡献的相关性。</li>
<li><b>回报方差。</b>固定策略下 16 步终局奖励的方差。</li>
<li><b>干预。</b>potential shaping、n-step、batch、100k episode。</li>
<li><b>信息对照。</b>G0 已经覆盖。</li>
</ol>
<p>写法：策略梯度在这里失败，原因是 X，并附上三个本可以证伪 X 的检验。</p>

<h2>6. 到 12/05 的时间线</h2>
{table(["周", "工作", "关卡"],
       [["11/10–11/16", "跑 G0；冻结环境", "G0 定案"],
        ["11/17–11/23", "诊断或收紧种子；一个迁移集", "所有表来自一个脚本"],
        ["11/24–11/30", "草稿、图、上界一节", "初稿完成"],
        ["12/01–12/05", "slides、≥2 次排练", "交付"]])}

<h2>7. 完成定义</h2>
<p><b>Option 1：</b>belief 条件化 RL 在 200 张 held-out 上赢 belief greedy，配对 CI 排除 0，5 种子，
且增益在状态消融后仍成立。<br>
<b>Option 2：</b>说出机制、至少一个把 RL 推向平手的干预（或证明不可能），并报告信息对照。</p>

<h2>附录 —— 值得一试的公开数据集</h2>
{table(["数据集", "单元", "契合点", "缺什么"],
       [["<b>SYNERGY</b>（ASReview）", "记录", "筛选题最佳：全标注、多领域", "无图、无成本"],
        ["<b>GO 注释</b>（IEA vs 实验）", "基因–词条", "DAG 故事 + 真实的自动 vs 人工", "无成本"],
        ["KAIST / Manchester", "行", "行/字段结构能否迁移", "需自造标签"],
        ["GitHub code review（HF）", "PR/hunk", "「AI review」叙事", "无正确性标签"],
        ["FEVER / Bugzilla", "claim / issue", "其他口味", "不是审阅调度"]])}
"""


def write(name: str, title: str, md: str, nav: str, blocks):
    html = (SHELL.replace("__TITLE__", title).replace("__CSS__", CSS)
                 .replace("__NAV__", nav).replace("__MD__", md)
                 .replace("__BLOCKS__", "\n".join(blocks)))
    (ROOT / name).write_text(html, encoding="utf-8")
    print("wrote", name, len(html))


write("GENERALIZATION_PLAN.html",
      "Generalization plan / 일반화 계획 / 泛化计划", "GENERALIZATION_PLAN.md", "📋 Generalization",
      [block("en", G["en"], True), block("ko", G["ko"]), block("zh", G["zh"])])

write("RL_PLAN.html",
      "RL plan / RL 계획 / 强化学习计划", "RL_PLAN.md", "🧠 RL plan",
      [block("en", R["en"], True), block("ko", R["ko"]), block("zh", R["zh"])])
