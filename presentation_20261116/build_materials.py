"""Build editable slides and matching vector PDF from a shared layout."""
from pathlib import Path
import json, zipfile, re
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
import fitz

OUT = Path(__file__).resolve().parent
DATA = Path('/Users/sloblucyra/Documents/rl-proposal-gaps/runs/proposal-gaps-full-v1/analysis.json')
A = json.loads(DATA.read_text())
TITLE = 'Review Scheduling on Dependency Graphs under a Limited Budget'
INK, PAPER, GREEN, RED, MUTED, PALE = '182C29','F6F5EF','267663','B74636','586C67','E2EAE3'
prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
prs.core_properties.title = TITLE; prs.core_properties.author = 'Team 6'
pdf = canvas.Canvas(str(OUT/'Team6_Proposal.pdf'), pagesize=(960,540))
pdf.setTitle(TITLE); pdf.setAuthor('Team 6')
slide = None; dark = False; notes = []

def box(x,y,w,h,color):
    sh=slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb=RGBColor.from_string(color); sh.line.fill.background()
    pdf.setFillColor(HexColor('#'+color)); pdf.rect(x*72,540-(y+h)*72,w*72,h*72,fill=1,stroke=0)

def text(s,x,y,w,h,size=22,color=None,bold=False):
    color=color or (PAPER if dark else INK)
    tb=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
    tf=tb.text_frame; tf.word_wrap=False
    tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0
    for i,line in enumerate(s.split('\n')):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph()
        p.text=line; p.font.name='Arial';p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=RGBColor.from_string(color)
        p.space_after=Pt(0)
    pdf.setFillColor(HexColor('#'+color));pdf.setFont('Helvetica-Bold' if bold else 'Helvetica',size)
    for i,line in enumerate(s.split('\n')):
        assert pdf.stringWidth(line,'Helvetica-Bold' if bold else 'Helvetica',size) <= w*72+3, (s,line,w)
        pdf.drawString(x*72,540-y*72-size-i*size*1.2,line)

def line(x,y,x2,y2,color=MUTED,width=2):
    from pptx.enum.shapes import MSO_CONNECTOR
    sh=slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x), Inches(y), Inches(x2), Inches(y2))
    sh.line.color.rgb=RGBColor.from_string(color);sh.line.width=Pt(width)
    from pptx.oxml.xmlchemy import OxmlElement
    arrow=OxmlElement('a:tailEnd');arrow.set('type','triangle');sh.line._get_or_add_ln().append(arrow)
    pdf.setStrokeColor(HexColor('#'+color));pdf.setLineWidth(width);pdf.line(x*72,540-y*72,x2*72,540-y2*72)
    import math
    angle=math.atan2(y2-y,x2-x);length=.13
    p=pdf.beginPath();p.moveTo(x2*72,540-y2*72)
    for side in (-1,1):
        px=x2-length*math.cos(angle)+side*.065*math.sin(angle)
        py=y2-length*math.sin(angle)-side*.065*math.cos(angle)
        p.lineTo(px*72,540-py*72)
    p.close();pdf.setFillColor(HexColor('#'+color));pdf.drawPath(p,fill=1,stroke=0)

def new(k,title,subtitle='',is_dark=False):
    global slide,dark
    dark=is_dark;slide=prs.slides.add_slide(prs.slide_layouts[6]);box(0,0,13.333,7.5,INK if dark else PAPER)
    text('TEAM 6  /  STA3145 REINFORCEMENT LEARNING',.6,.3,11,.25,11,GREEN if not dark else 'A6D4BC',True)
    text(title,.6,.88,12.1,1.1,32,bold=True)
    if subtitle:text(subtitle,.6,2.02,12.1,.5,16,MUTED if not dark else 'C2D4CC')
    text(f'{k:02d}   |   PROJECT PROPOSAL',.6,7.04,9,.2,10,MUTED if not dark else 'A6D4BC')

def end(script):
    slide.notes_slide.notes_text_frame.text=script
    notes.append(script);pdf.showPage()

def card(x,y,w,label,body):
    box(x,y,w,2.05,PALE);text(label,x+.22,y+.2,w-.44,.5,21,GREEN,True)
    text(body,x+.22,y+.85,w-.44,1.1,18)

new(1,'Review Scheduling on Dependency Graphs\nunder a Limited Budget',is_dark=True)
text('Which output should a human check next?',.65,2.65,12,.8,28,bold=True)
for x,n,label in [(0.7,'01','DEPENDENCIES'),(4.9,'02','PARTIAL FEEDBACK'),(9.05,'03','16 REVIEWS')]:
    text(n,x,4.1,2,.7,48,'A6D4BC',True);text(label,x,5.08,3.6,.4,15,PAPER,True)
text('Team 6  |  Yonsei University  |  November 2026',.65,6.35,12,.4,16,'C2D4CC')
end('We study how to allocate a limited human review budget across a graph of dependent outputs. An upstream error can affect several downstream conclusions, so reviewing the most suspicious item is not always the best choice. Our question is whether reinforcement learning can learn a better sequence of checks than a strong adaptive greedy policy.')

new(2,'One upstream check can protect several conclusions','Motivation: research pipelines reuse intermediate outputs.')
positions=[(.9,3.1,'Parsed input'),(4.65,2.8,'Derived metric'),(4.65,4.55,'Second metric'),(9.1,2.8,'Conclusion A'),(9.1,4.55,'Conclusion B')]
for a,b in [(0,1),(0,2),(1,3),(2,4)]:
    x,y,_=positions[a];xx,yy,_=positions[b];line(x+2.5,y+.42,xx,yy+.42,GREEN,3)
for i,(x,y,label) in enumerate(positions):
    box(x,y,2.5,.85,RED if i==0 else PALE);text(label,x+.14,y+.2,2.22,.5,18,PAPER if i==0 else INK,True)
text('Review reveals information and may repair an error.',.9,6.05,11.7,.5,22,bold=True)
end('Consider a pipeline that parses an input, computes derived metrics, and produces conclusions. A shared upstream mistake can contaminate multiple outputs. A review both reveals information and may repair an error, changing which node is useful to inspect next. The application is evidence review in research workflows. Our current performance experiments use synthetic graphs; they are not a validated deployment in a real research system.')

new(3,'A sequential decision problem with hidden errors','Partially observable environment; policies act on a particle-belief state.')
card(.65,2.85,3.85,'STATE','Graph + confidence\nReview history + belief\nRemaining budget')
card(4.73,2.85,3.85,'ACTION / TRANSITION','Choose an unreviewed node\nObserve review outcome\nRepair and update belief')
card(8.81,2.85,3.85,'OBJECTIVE','16 decisions per episode\nTerminal reward =\nnegative sink-error count')
text('Maximize expected return: fewer wrong conclusions after review.',.7,5.55,12,.55,24,GREEN,True)
text('Undiscounted finite horizon (gamma = 1). True errors are hidden from deployable policies.',.7,6.3,12,.4,15,MUTED)
end('We formulate the environment as partially observable and use a particle belief over hidden errors. The policy observes graph structure, confidence, review history, and remaining budget. Each action selects an unreviewed node. The outcome updates both the graph error state and the belief. After sixteen reviews, the reward is the negative number of erroneous sink nodes. We use an undiscounted finite horizon, with gamma equal to one.')

new(4,'Compare course methods against a strong baseline','The question is when learning adds value beyond one-step planning.')
card(.65,2.85,3.85,'BELIEF GREEDY','Update the posterior\nEstimate immediate benefit\nChoose the best next check')
card(4.73,2.85,3.85,'LEARNED POLICIES','Shared GNN policy\nREINFORCE / MC critic\n3-step / 5-step targets')
card(8.81,2.85,3.85,'CONTROLLED INPUTS','Observed-state features\nAdd estimated gain\nSame review budget')
text('2 input sets x 4 learning methods x 5 seeds x 3 signal conditions',.7,5.58,12,.5,23,GREEN,True)
text('Course links: policy gradients, Monte Carlo returns, TD bootstrap, function approximation.',.7,6.3,12,.4,15,MUTED)
end('Our baseline is belief greedy: it updates its posterior after each review and chooses the largest estimated immediate reduction in sink errors. The learned methods share a graph neural policy. We compare REINFORCE, a learned critic using full Monte Carlo targets, and three-step or five-step bootstrap targets. We also test whether providing estimated gain as an extra input helps. This connects directly to policy gradients, Monte Carlo learning, temporal-difference bootstrap, and function approximation.')

new(5,'Preliminary result: greedy remains ahead','Normal confidence, matched environment. Lower residual sink errors are better.')
text('Mean residual sink errors',4.2,2.52,7,.3,14,MUTED)
labels=['Belief greedy','Observed + 3-step','Gain + 3-step'];vals=[A['all_cells']['normal/matched'][x]['mean'] for x in ['belief greedy','observed/nstep3','gain/nstep3']]
for i,(label,val) in enumerate(zip(labels,vals)):
    y=2.95+i*.9;text(label,.75,y,3.35,.45,20,bold=True);box(4.2,y,val*3.9,.46,GREEN if i==0 else MUTED);text(f'{val:.3f}',9.45,y,1.7,.5,25,bold=True)
text('0 / 8',.75,5.86,2.2,.7,38,RED,True)
text('learned candidates outperform greedy in the primary analysis',3.0,5.98,9.5,.5,20,bold=True)
text('5 seeds; 200 held-out graphs; 100,000 crossed-bootstrap draws; multiplicity-adjusted intervals.',.75,6.65,12,.25,12,MUTED)
end('The completed development run trained one hundred and twenty policies, for two point four million episodes in total. In the primary condition, belief greedy leaves 1.020 sink errors on average. The best learned mean is 1.255, for gain plus three-step targets, about twenty-three percent worse. All eight learned candidates have worse performance, with multiplicity-adjusted difference intervals above zero. This is a negative result for the current implementation, not evidence that reinforcement learning can never help.')

new(6,'Next: test robustness to a misspecified model','Exploratory clue: under noisy confidence, some learned policies have lower mean error.')
card(.65,2.85,3.85,'OBSERVED CLUE','Noise / matched setting\nGreedy: 3.965 errors\nObserved 3-step: 3.477')
card(4.73,2.85,3.85,'DIAGNOSE FIRST','Inspect action choices\nAudit belief degeneracy\nCheck information parity')
card(8.81,2.85,3.85,'THEN CONFIRM','Freeze one hypothesis\nUse fresh graphs and seeds\nKeep all baselines')
text('Noise changes confidence and belief. The mechanism is unresolved.',.7,5.65,12,.65,23,RED,True)
text('This is a proposed follow-up, not an established robustness claim or online adaptation.',.7,6.38,12,.4,15,MUTED)
end('An exploratory result suggests a narrower follow-up. Under noisy confidence, observed three-step learning has 3.477 errors versus 3.965 for greedy. However, noise changes both confidence and the derived belief, and the particle filter sometimes degenerates. We will first inspect action choices and belief failures, rather than launch another large training run. If the pattern survives those checks, we will freeze a robustness hypothesis and evaluate on fresh graphs and training seeds. That confirmation has not been performed.')

new(7,'Deliverable: establish when learning is worth it',is_dark=True)
for x,n,label,body in [(.7,'1','DIAGNOSE','Action traces and belief failures'),(.7,'2','SPECIFY','One robustness hypothesis and criterion'),(.7,'3','VALIDATE','Held-out comparison and reproducible report')]:
    y=2.8+(int(n)-1)*1.02;text(n,x,y,.7,.7,36,'A6D4BC',True);text(label,1.6,y+.05,3,.5,21,'A6D4BC',True);text(body,4.6,y+.05,8,.5,21)
text('Success = a reliable boundary, even if greedy remains best.',.7,6.2,12,.6,26,bold=True)
end('Our project contribution is a reproducible evaluation of when learning is worth its complexity in graph review scheduling. The remaining deliverables are an action-level diagnosis, a precise follow-up hypothesis, and an independently checkable evaluation. We will report a negative result if greedy remains best. We will not claim real-system benefit before testing it. The central question is simple: under what information and model conditions does a learned review sequence improve on adaptive greedy? Thank you.')

new(8,'Backup: every primary candidate','Difference = learned minus belief greedy; positive values are worse.')
for label,x,w in [('Candidate',.8,4),('Mean',5,1.2),('Difference',6.6,1.8),('Adjusted interval',9,3.4)]:
    text(label,x,2.7,w,.4,18,GREEN,True)
for i,(k,v) in enumerate(A['primary'].items()):
    mean=A['all_cells']['normal/matched'][k]['mean'];lo,hi=v['adjusted_ci']
    for value,x,w in [(k,.8,4),(f'{mean:.3f}',5,1.2),(f'+{v["mean"]:.3f}',6.6,1.8),(f'[{lo:.3f}, {hi:.3f}]',9,3.4)]:
        text(value,x,3.25+i*.36,w,.35,16)
text('99.375% per interval for eight primary comparisons. Five training seeds limit precision.',.8,6.48,12,.4,14,MUTED)
end('Backup only. All eight primary contrasts use paired graph outcomes and crossed seed/graph resampling. All adjusted intervals lie above zero. All ten secondary adjusted intervals cross zero, so the current analysis does not establish gains from either the input augmentation or the learning-target changes.')

new(9,'Backup: anticipated questions','Keep scope, information access, and evidence levels explicit.')
qa=[('Why use RL if greedy wins?','Sequential effects motivate RL; an MDP alone does not guarantee an RL advantage.'),('Does noise prove a learned robustness advantage?','No. It is exploratory, with coupled signal/belief changes and posterior failures.'),('Is this tested on real scientific workflows?','Not yet. Current policy-performance evidence is from synthetic graphs.'),('What remains unverified?','Independent confirmation, clean-clone reproduction, and real-system acceptance.')]
for i,(q,a) in enumerate(qa):
    y=2.75+i*.87;box(.65,y,.09,.65,GREEN);text(q,.95,y,11.5,.35,20,bold=True);text(a,.95,y+.4,11.5,.3,15,MUTED)
end('Backup only. Belief greedy is adaptive and deployable given its assumed model; oracle information is not deployable. Negative results are informative only within the tested task, methods and information assumptions. A weak DQN result would not prove policy gradients are uniquely appropriate, and we do not make that claim.')

new(10,'Backup: references and reproducibility','Methods are grounded in course material; results come from the saved full-v1 artifacts.')
refs=[('Sutton & Barto (2018)','Reinforcement Learning: An Introduction, 2nd ed. Chapters 7, 9, 13.'),('Williams (1992)','Simple statistical gradient-following algorithms for connectionist reinforcement learning.'),('Kipf & Welling (2017)','Semi-Supervised Classification with Graph Convolutional Networks.'),('Project development artifacts','proposal-gaps-full-v1/results.json and analysis.json; graphs 1000-1199.'),('Frozen analysis protocol','PROPOSAL_GAPS_ANALYSIS_PROTOCOL.md; input and protocol hashes in analysis.json.')]
for i,(q,a) in enumerate(refs):
    y=2.65+i*.7;text(q,.8,y,11.8,.35,19,GREEN,True);text(a,.8,y+.35,11.8,.3,14)
end('Reference and reproducibility slide; not part of the five-minute delivery. This is a prospective development protocol written after training started, not a pre-training registration. No independent confirmation or clean-clone teammate reproduction has been completed.')

pdf.save();prs.save(OUT/'Team6_Proposal.pptx')
times=[25,35,45,45,55,50,35]
script=['# Team 6 - English speaker script','',f'Project title: {TITLE}','','Main delivery: 7 slides, 290 seconds plus 10 seconds of transitions. Backup slides 8-10 are not spoken unless requested.','']
for i,n in enumerate(notes):script.extend([f'## Slide {i+1}'+(f' ({times[i]} seconds)' if i<7 else ' (backup)'),'',n,''])
script.extend(['## Chinese preparation notes','','核心问题：有限预算下，怎样安排图上的人工审阅顺序？当前主结果支持 greedy，而不是 RL 优势。不要把任务具有序列结构，说成 RL 必然优于规划。','','模型：真实错误隐藏，用粒子 belief 近似；动作是选下一个未审阅节点。16 步后，以残余终端错误的负数作为奖励，gamma=1。','','主结果：greedy=1.020；最好学习均值=1.255，仍差约23%。噪声条件仅是下一步研究线索。真实系统部署、独立确认和队友复现均未完成。',''])
(OUT/'Speaker_Script_EN.md').write_text('\n'.join(script))
doc=fitz.open(OUT/'Team6_Proposal.pdf');pre=OUT/'preview';pre.mkdir(exist_ok=True)
for i,page in enumerate(doc):page.get_pixmap(matrix=fitz.Matrix(1,1)).save(pre/f'slide-{i+1:02d}.png')
from PIL import Image,ImageOps,ImageDraw
thumb=Image.new('RGB',(960,5*290),'#dddddd')
for i in range(10):
    im=Image.open(pre/f'slide-{i+1:02d}.png');im.thumbnail((470,265));thumb.paste(im,((i%2)*480,(i//2)*290+20))
    ImageDraw.Draw(thumb).text(((i%2)*480+8,(i//2)*290+3),f'Slide {i+1}',fill='black')
thumb.save(pre/'overview.png')
with zipfile.ZipFile(OUT/'Team6.zip','w',zipfile.ZIP_DEFLATED) as z:z.write(OUT/'Team6_Proposal.pdf','Team6_Proposal.pdf')
print('Created 10-slide PDF/PPTX, script, previews, and PDF-only Team6.zip')
print('Main script words:',sum(len(re.findall(r"\b[\w'-]+\b",x)) for x in notes[:7]))
