"""Build the feedback-response appendix deck (EN) that answers the six teacher points.

Same visual system as build_materials.py (ink/paper/green/red, Arial, 13.333x7.5),
so the appendix can be appended to Team6_Proposal.pptx without a style break.
Slides: A1 error definition, A2 four-stage DAG, A3 three requirements -> MDP, A4 error rates.
"""
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

OUT = Path(__file__).resolve().parent
DAG = OUT.parent / 'experiments' / 'sleep_dag_4stage_en.png'
TITLE = 'Review Scheduling on Dependency Graphs under a Limited Budget'
INK, PAPER, GREEN, RED, MUTED, PALE = '182C29', 'F6F5EF', '267663', 'B74636', '586C67', 'E2EAE3'

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
prs.core_properties.title = 'Team 6 - feedback appendix'
prs.core_properties.author = 'Team 6'
pdf = canvas.Canvas(str(OUT / 'Team6_Feedback_Appendix.pdf'), pagesize=(960, 540))
pdf.setTitle('Team 6 - feedback appendix')
pdf.setAuthor('Team 6')

slide = None
dark = False


def box(x, y, w, h, color):
    sh = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = RGBColor.from_string(color)
    sh.line.fill.background()
    pdf.setFillColor(HexColor('#' + color))
    pdf.rect(x * 72, 540 - (y + h) * 72, w * 72, h * 72, fill=1, stroke=0)


def wrap(s, size, w, bold=False):
    font = 'Helvetica-Bold' if bold else 'Helvetica'
    limit = w * 72 + 2
    out = []
    for raw in s.split('\n'):
        if not raw.strip():
            out.append('')
            continue
        cur = ''
        for word in raw.split(' '):
            trial = (cur + ' ' + word).strip()
            if not cur or pdf.stringWidth(trial, font, size) <= limit:
                cur = trial
            else:
                out.append(cur)
                cur = word
        out.append(cur)
    return out


def tblock(s, x, y, w, size=15, color=None, bold=False, lead=1.34):
    """Wrapped paragraph. Returns the y after the last line."""
    color = color or (PAPER if dark else INK)
    lines = wrap(s, size, w, bold)
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(size / 72 * lead * len(lines)))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = ln
        p.font.name = 'Arial'
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = RGBColor.from_string(color)
        p.space_after = Pt(0)
    pdf.setFillColor(HexColor('#' + color))
    pdf.setFont('Helvetica-Bold' if bold else 'Helvetica', size)
    for i, ln in enumerate(lines):
        pdf.drawString(x * 72, 540 - y * 72 - size - i * size * lead, ln)
    return y + len(lines) * size * lead / 72


def rule(x, y, w, color='C8CFCB', width=1.1):
    pdf.setStrokeColor(HexColor('#' + color))
    pdf.setLineWidth(width)
    pdf.line(x * 72, 540 - y * 72, (x + w) * 72, 540 - y * 72)
    from pptx.enum.shapes import MSO_CONNECTOR
    sh = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x), Inches(y), Inches(x + w), Inches(y))
    sh.line.color.rgb = RGBColor.from_string(color)
    sh.line.width = Pt(width)


def new(k, title, subtitle='', is_dark=False):
    global slide, dark
    dark = is_dark
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box(0, 0, 13.333, 7.5, INK if dark else PAPER)
    tblock('TEAM 6  /  STA3145 REINFORCEMENT LEARNING', .6, .3, 11, 11,
           GREEN if not dark else 'A6D4BC', True)
    tblock(title, .6, .85, 12.1, 30, bold=True)
    if subtitle:
        tblock(subtitle, .6, 1.95, 12.1, 15, MUTED if not dark else 'C2D4CC')
    tblock(f'A{k}   |   FEEDBACK APPENDIX', .6, 7.04, 9, 10,
           MUTED if not dark else 'A6D4BC')


def end(script):
    slide.notes_slide.notes_text_frame.text = script
    pdf.showPage()


def head_row(cells, xs, widths, y, size=12):
    for c, x, w in zip(cells, xs, widths):
        tblock(c, x, y, w, size, GREEN, True)
    rule(.62, y + .30, 12.1)
    return y + .48


def body_row(cells, xs, widths, y, size=13, bold_first=True, color=None):
    maxy = y
    for c, x, w in zip(cells, xs, widths):
        bold = bold_first and c is cells[0]
        maxy = max(maxy, tblock(c, x, y, w, size, color, bold))
    return maxy + .18


# ---------------------------------------------------------------- A1 error definition
new('1', 'An error is a wrong output value, not a bug',
    'The pipeline produced a plausible record; a human later corrected it. Code bugs are caught by tests.')

xs = [.65, 3.45, 8.40, 10.80]
ws = [2.75, 4.75, 2.30, 1.95]
y = head_row(['Error type', 'Concrete example from the real extract', 'Share of fixes', 'Base rate'], xs, ws, 2.62)
rows = [
    ('order_error', 'wake-up timestamp earlier than sleep onset; AM/PM flipped; span over 24 h',
     '57/75 = 76%', '0.35'),
    ('every other type',
     'diff / metric_spike / sleep_awake_equal: gap wrong, metric jump, efficiency over 100%, zero-length sleep',
     '10 labelled + 8 unlabelled = 18/75', '0.05 - 0.15'),
]
for r in rows:
    y = body_row(list(r), xs, ws, y, 13)
    rule(.62, y - .06, 12.1)

y += .12
tblock('75 corrections in 13,990 daily records (0.54%). The file records that a value was corrected, '
       'not who caused it: these are corrections to automated output, not claims about AI inference.',
       .65, y, 12.1, 13.5, MUTED)
y += .62
box(.62, y, .10, .72, GREEN)
tblock('Scope: a human reviewer never sees a code bug. Here the human has minutes and an already-produced '
       'evidence chain, and must decide which link is wrong.', 1.0, y + .04, 11.5, 15, bold=True)

end('The teacher asked what we mean by error. It is a wrong value in an automated pipeline output, not a bug in the code. '
    'The real extract has seventy-five human corrections in thirteen thousand nine hundred ninety daily records. '
    'Seventy-six percent are time-order errors: a wake-up earlier than sleep onset, a flipped AM/PM, a span over twenty-four hours. '
    'The correction file records the fix, not the culprit, so we call these corrections to automated output rather than claims about AI inference. '
    'Scoping matters: a reviewer never sees a code bug, because tests catch those. The reviewer sees a finished evidence chain and limited time.')

# ---------------------------------------------------------------- A2 four stages
new('2', 'Every pipeline output is a node',
    'Collect, preprocess, analyze, conclude. Four conclusion nodes are sinks, and the reward counts only those.')
DAG_W, DAG_H = 6.62, 6.62 / 1.6485
slide.shapes.add_picture(str(DAG), Inches(.5), Inches(2.36), width=Inches(DAG_W))
pdf.drawImage(str(DAG), .5 * 72, 540 - 2.36 * 72 - DAG_H * 72,
              width=DAG_W * 72, height=DAG_H * 72, mask='auto')

tx, tw = 7.42, 5.35
ty = 2.42
terms = [
    ('Node', 'one output value of one stage: raw field, derived gap, metric, verdict. 21 in total.'),
    ('Hidden error', 'whether the node\'s own value is wrong. Unobservable; the policy sees type, confidence, sink reach, belief.'),
    ('Stage node', 'any of the four layers. The conclusion layer is the sink layer; here it holds four sinks.'),
    ('State', 'per node: type, confidence, sink reach, reviewed, P(base), P(error); plus remaining budget. H = B.'),
]
for name, body in terms:
    tblock(name, tx, ty, tw, 12.5, GREEN, True)
    ty = tblock(body, tx, ty + .27, tw, 12.5) + .18

tblock('Conclusion nodes can carry their own error. A review clears that node\'s own error and recomputes downstream.',
       .5, 6.62, 12.2, 12.5, MUTED)

end('This is the answer to the per-stage question. Collect has eight raw diary fields, preprocess has five derived gaps, analyze has four sleep metrics, '
    'and conclude has four verdicts. Every one of those is a node: twenty-one in total. The four verdicts are the sinks, and the reward is minus the number of erroneous sinks. '
    'A conclusion node can hold its own error, so reviewing it is meaningful; a review clears the node\'s own error and downstream nodes are recomputed. '
    'The numbers inside the boxes are the model prior for the base error rate, not per-node measurements, and the figure says so.')

# ---------------------------------------------------------------- A3 three requirements
new('3', 'Three requirements, one MDP',
    'Not three literatures side by side: three components that feed each other.')

xs = [.65, 5.95, 10.65]
ws = [5.1, 4.6, 2.1]
y = head_row(['Requirement', 'Component in our method', 'Anchor'], xs, ws, 2.45)
rows = [
    ('Hand the decision back to a human\n(learning-to-defer)',
     'action = review an unreviewed node; inspection may miss (p_catch = 0.9); reward = minus residual sink errors',
     'proposal 4 / spec 2.3'),
    ('Allocate reviews under a budget\n(budgeted allocation)',
     'state carries budget_left; finite horizon H = B; the episode ends when the budget is spent',
     'proposal 4'),
    ('Errors accumulate downstream\n(error cascade)',
     'dependency DAG with parents and sinks; hidden-error belief P(base), P(error); repair clears base, downstream recomputed',
     'spec 2.2-2.5'),
]
for r in rows:
    y = body_row(list(r), xs, ws, y, 12.5)
    rule(.62, y - .07, 12.1)

y += .05
tblock('Why all three, in one MDP', .65, y, 12.1, 15, GREEN, True)
items = [
    'Deferral alone decides per item whether to escalate. Without the graph it cannot tell that fixing one upstream row saves several conclusions, nor rank what to check first.',
    'Budget allocation alone treats items as independent arms. Without a hidden-error belief it cannot rank by error probability times downstream impact.',
    'Error cascade alone shows errors accumulate but never says which link a time-limited human should inspect.',
    'Together: the graph supplies candidates and impact weights, the belief supplies the ranking, the budget supplies horizon and stopping. Remove one and the ranking is undefined.',
]
col_x, col_w = [.65, 6.9], 5.75
ycol = [y + .34, y + .34]
for i, s in enumerate(items):
    c = i % 2
    cx, cy = col_x[c], ycol[c]
    tblock(f'{i + 1}', cx, cy, .35, 13, RED, True)
    ycol[c] = tblock(s, cx + .4, cy, col_w - .4, 12, bold=(i == 3)) + .15

end('The teacher asked how the three elements connect. They are not three literatures standing next to each other; they are three components of one MDP. '
    'Deferral is the action and the terminal reward. Budgeted allocation is the remaining-budget state variable and the finite horizon. '
    'Error cascade is the dependency graph, the hidden-error belief, and the transition that recomputes downstream nodes. '
    'Take any one away and the ranking is undefined: without the graph you cannot weigh downstream impact, without the belief you cannot rank, without the budget there is no horizon or stopping rule.')

# ---------------------------------------------------------------- A4 error rates
new('4', 'Appendix: which error rate are we quoting?',
    'Three different denominators. Do not mix them, and do not claim a per-stage measured rate.')

xs = [.65, 4.05, 10.35]
ws = [3.3, 6.1, 2.4]
y = head_row(['Measure', 'Meaning', 'Value'], xs, ws, 2.44)
rows = [
    ('Correction rate, full extract', 'share of all daily records a human edited', '75/13,990 = 0.54%'),
    ('Audit-queue precision', 'flagged rows that were actually wrong', '68/1,048 = 6.5%'),
    ('Single-type concentration', 'order_error share of all corrections', '57/75 = 76%'),
]
for r in rows:
    y = body_row(list(r), xs, ws, y, 14)
    rule(.62, y - .07, 12.1)

y += .18
y = tblock('Type shares are measured. Per-node base rates (0.35, 0.15, ...) are a model prior mapped from those '
           'shares, not per-node measurements: the correction file does not record the pipeline stage.',
           .65, y, 12.1, 13, MUTED)

y += .28
tblock('Hidden errors are estimated, not merely defined', .65, y, 12.1, 14.5, GREEN, True)
y += .36
y = tblock('Random audits estimate the base error rate; v5 passes its pre-registered gate on all 9 cells: '
           '|bias| <= 0.05, coverage >= 0.90, calibration pass rate 1.00.', .65, y, 12.1, 13)

y += .28
tblock('A strong baseline already exists on the real graph', .65, y, 12.1, 14.5, GREEN, True)
y += .36
tblock('Only heuristics run at N=21 (belief greedy is not run at this size). 8 seeds, budget 8/21 '
       '(main synthetic setting: 16): no review 2.12, random 1.88, degree 1.88, confidence 0.50 — '
       'paired against random +1.38 [0.12, 2.63], and one seed still ends at 3.', .65, y, 12.1, 13)

end('Two honesties. First, the three rates have three denominators and we never mix them. Type shares are measured; the per-node base rates are a model prior mapped from '
    'those shares, because the correction file does not record which stage failed. Second, hidden errors are estimated, not only defined: random audits, with v5 passing its '
    'pre-registered gate on all nine cells. On the real graph a simple confidence threshold reaches 0.50 residual errors against 2.12 for no review, so that is the bar '
    'any learned policy has to clear. Third, and say this before anyone asks: our own replays (results.md section 12) show that within a record two reviews clear it, '
    'and across records a one-line QC rule is within 0.014 of the oracle. Per-node scheduling is justified by the 80-node synthetic setting, not by our 21-node data; '
    'on our data the open question is block review, which is a proposed next experiment, not a result.')

pdf.save()
prs.save(OUT / 'Team6_Feedback_Appendix.pptx')
print('wrote Team6_Feedback_Appendix.pptx / .pdf')
