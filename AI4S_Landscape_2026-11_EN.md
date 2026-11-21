# AI4S Landscape: From Self-Trained Scientific Models to Real-Instrument Closed Loops (November 2026)

> **One-line conclusion**
>
> For the first time, all three segments of the chain have public evidence in 2026: Shanghai AI Lab's [**Shusheng·Duanzhi**](https://www.shlab.org.cn/news/5444294) turned "compute–verify–validate" into a platform connected to large-scale scientific facilities; Tencent's [**Hyra 2.0**](https://hy.tencent.com/research/hyra2) had an agent train two protein models from scratch; DeepMind's [**Co-Scientist**](https://doi.org/10.1038/s41586-026-10644-y) and FutureHouse's [**Kosmos**](https://arxiv.org/abs/2511.02824) published auditable multi-agent research results; [**Lila Sciences**](https://cen.acs.org/business/start-ups/lila-ai-hydrogen-catalyst-electrolyzer/104/web/2026/10) and [**Periodic Labs**](https://techfundingnews.com/former-openai-and-deepmind-researchers-eye-7b-valuation-for-ai-startup-periodic-labs/) turned "robot lab + models" into a fundable neolab business.
>
> But "self-training models" is still confined to a few teams; the real bottleneck in instrument closed loops is **interface standards, failure-data feedback, and trustworthiness**, not model capability.

## 0. Forwardable summary (~500 words)

**China has split into three routes.**

1. **Platform route** ([Shanghai AI Lab Shusheng·Duanzhi](https://www.shlab.org.cn/news/5444294)): released July 2026, upgraded 13 September, "compute, verify, validate" in one. Models handle reasoning and hypotheses; **Science Harness** holds research state, cross-turn context, heterogeneous resource orchestration, and replanning; the **trusted research evidence chain** links literature, data, code, tool calls, compute results, and experiment logs; a **seven-dimension review agent** checks completeness, correctness, evidence and provenance, reproducibility, artifact quality, tool execution, and review history; below that sits a **distributed autonomous experiment network** connected to synchrotron, spallation-neutron, atomic-manufacturing, and pilot-scale facilities. It reports dry-lab/wet-lab closed loops in proteins and new materials.
2. **Model-bootstrap route** ([Tencent Hunyuan Hyra 2.0](https://hy.tencent.com/research/hyra2)): three agent layers (Overall / Mission / Worker), persistent tasks, code-and-log evidence for every conclusion, independent review agents, and skills distilled for reuse. It trained HyInv (1.96M parameters; inverse folding; ~57× faster than ProteinMPNN) and HyPLM-Flash (650M parameters, 726B tokens) from scratch, and took part in pretraining, post-training, and inference optimization of the next Hunyuan model.
3. **Robot-lab route** (USTC's [Xiaolai/Xiaolin](https://www.news.cn/liangzi/20260403/05bd0e6b42dc4dffb7822319e74ed8d1/c.html), [XtalPi](https://www.news.cn/tech/20260921/04a2cbef72444a32910cb3dd7c1833f2/c.html), SJTU's [AutoDNA](https://m.thepaper.cn/newsDetail_forward_34434147)): Xiaolai found the optimal Martian oxygen-evolution catalyst in six weeks from 3.76 million candidate formulations; XtalPi opened 80+ scientific skills and let agents schedule robot experiments; AutoDNA coordinated 20+ instrument classes over 11,000+ hardware steps at 97.8% single-step yield.

**Abroad, the shift is from "assistant" to "closed loop."** In May 2026 Nature published [Co-Scientist](https://doi.org/10.1038/s41586-026-10644-y) and [Robin](https://doi.org/10.1038/s41586-026-10652-y) (whose team later productized [Kosmos](https://arxiv.org/abs/2511.02824)): the former produced experimentally testable hypotheses in leukaemia, liver fibrosis, and antimicrobial resistance; the latter ran up to 12 hours per run, executed ~42,000 lines of code, read 1,500 papers, and had 79.4% of its statements judged accurate by independent scientists. [Lila Sciences](https://cen.acs.org/business/start-ups/lila-ai-hydrogen-catalyst-electrolyzer/104/web/2026/10) used a closed loop to find six families of palladium-based oxides (2,942 formulations; best candidate lasted 1,000 hours), and [Periodic Labs](https://techfundingnews.com/former-openai-and-deepmind-researchers-eye-7b-valuation-for-ai-startup-periodic-labs/) raised a USD 300M seed and was in talks at a USD 7B valuation. The UK's [ARIA](https://www.technologyreview.com/2026/01/20/1131462/the-uk-government-is-backing-ai-scientists-that-can-run-their-own-experiments/) funded 12 of 245 proposals with ~£500K each over nine months, requiring a novel finding.

**Three judgments.** (1) The competition has moved from "can the model think" to "can the research state survive and can the evidence be checked." (2) "Self-training models" is still a demo, not a general capability. (3) The bottleneck in real instrument loops is **device interfaces, failure-data feedback, and the ability to say "insufficient evidence"**—which is exactly the opening for a verifiable orchestration layer like SciForge.

## 1. Scope and method

- **Time window:** mainly public material from November 2025 to November 2026; older work appears only as background (with year).
- **Inclusion:** a system must cover at least two stages of the chain (Section 2) and have public evidence (paper, official release, or reputable media).
- **Evidence grades:**
  - **A peer-reviewed:** Nature / Science / formal journals;
  - **B preprint:** arXiv / medRxiv, not peer-reviewed;
  - **C official release:** institution site, official blog, official launch;
  - **D media:** reputable outlets; numbers treated as reported, not verified.
- **Not read:** the Hyra technical reports, the full AutoDNA Nature paper, the full Co-Scientist and Kosmos Nature papers (only abstracts, press releases, and secondary coverage). Section 9 marks this per item.

## 2. Five stages of the chain

```
S0 problem framing ──► S1 model bootstrap ──► S2 compute validation ──► S3 instrument loop ──► S4 evaluation/governance
    humans set goals      agents train/improve      simulation / structure / docking      robots and instruments      trust, safety, reproducibility
                          domain models             property prediction                    real data feedback
```

| Stage | Question | State in 2026 |
|---|---|---|
| **S0** | Who poses the problem and defines success? | Still mostly human; Co-Scientist can generate sub-questions, but topic choice remains human |
| **S1** | Can an agent build or train a domain model? | **Scarcest:** Hyra 2.0 is the clearest public case; Co-Scientist's Agent_H is an early signal of "designing a model architecture" |
| **S2** | Can the computation be trusted? | Mature: AlphaFold 3 / ESM3 / Uni-Mol / MatterGen; but "computes correctly" ≠ "experiment holds" |
| **S3** | Can it actually drive instruments? | Maturing fast: AutoDNA, Xiaolai, XtalPi, Lila, Periodic, Shusheng·Duanzhi; bottleneck is interfaces and failure feedback |
| **S4** | How do we know it got it right? | Only taken seriously in 2026: Kosmos 79.4%, Co-Scientist 4% hallucination, BioBasicsBench 66.7% |

> The point is not that all five stages have someone working on them, but whether a system **connects them and leaves a checkable trace at each stage**. On public evidence, only six do three or more stages with an evidence chain: Shusheng·Duanzhi, Hyra 2.0, AutoDNA, Co-Scientist, Kosmos, and Lila (to different degrees).

---

## 2.5 Closed loop ≠ RL: where RL would actually fit

Start by removing a common misreading: these systems are all **closed loops**, but most of their decision cores are not RL. [Co-Scientist](https://doi.org/10.1038/s41586-026-10644-y) is multi-agent generation/debate/evolution plus Elo ranking; [Kosmos](https://arxiv.org/abs/2511.02824) is data-analysis and literature agents over a shared world model; [AutoDNA](https://m.thepaper.cn/newsDetail_forward_34434147) is a central planner plus six specialist agents; [Lila](https://cen.acs.org/business/start-ups/lila-ai-hydrogen-catalyst-electrolyzer/104/web/2026/10) uses sequential learning (closer to Bayesian optimization or active learning); [Xiaolai](https://www.news.cn/liangzi/20260403/05bd0e6b42dc4dffb7822319e74ed8d1/c.html) uses expert decision models. Only a minority explicitly use RL: [Hyra 2.0](https://hy.tencent.com/research/hyra2)'s HyInv is trained with "supervised learning plus structure-reward RL"—but that trains a **model**, not an agent policy; robot control and resource scheduling may use RL, but public detail is thin.

**If we are going to use RL, three conditions should hold:**

1. **Sequential + delayed + budgeted:** the decision is not a single generation but "which one first, inspect the result, then decide the next," feedback arrives late, and human or machine time is limited. That is an MDP, not a prompt.
2. **Verifiable reward:** the reward comes from checkable outcomes (sink errors, reproduction failures, experiment cost), not an LLM score.
3. **Offline replay:** there are logs and counterfactuals, so offline or conservative RL can be tried before any deployment.

**Where not to use RL:** single-step writing, retrieval, summarization, code generation—LLMs and tools are more direct; open-ended research without a reliable reward—build the evaluation first, then talk about policy.

**Where it lands for SciForge:** review scheduling satisfies all three conditions (choose the next node to review under a budget, errors propagate to sinks, reward is the number of sink errors). The right posture is therefore: build a **read-only advisor** first (belief-greedy or heuristic), compare RL only in offline experiments, do not put it on the product path, and never let the machine seal. In one line: **do not dress a closed loop up as RL**—the first review question will be "where is the policy, where is the reward, and where is the update?"

---

## 3. China

### 3.1 Shanghai AI Lab: Shusheng·Duanzhi, "compute–verify–validate" in one (C)

Released July 2026, [upgraded and opened as a full-stack service](https://www.shlab.org.cn/news/5444294) on 13 September at the Pujiang Innovation Forum. It is positioned as a trusted research execution platform for complex tasks, not a chatbot.

**Three layers:**

| Layer | What it does | Key design |
|---|---|---|
| Model | Scientific reasoning, hypothesis generation, strategy, knowledge organization | Shusheng scientific multimodal model **S2** (science-specific, long-horizon, agentic); Shusheng physical-world model **W0** (native force/tactile, duplex coordination, preparation for the physical world) |
| Science Harness | Research-state retention, cross-turn context, heterogeneous resource orchestration, multi-role coordination, experiment-feedback intake, replanning | New results, data, or expert opinions are written into the current research state; models re-evaluate; effective paths, failures, and key decisions are retained |
| Validation | Trusted research evidence chain + distributed autonomous experiment network | Evidence chain covers delivery alignment, independent verification, and execution replay; the network connects real devices |

**Seven-dimension review agent** (the part most worth benchmarking): completeness against the request, correctness, evidence and provenance, reproducibility, artifact quality, tool execution, and review history—each checked independently and graded. Execution keeps key parameters, tool versions, experiment conditions, and logs so runs can be repeated under the same conditions.

**Real closed loop:** with the Shanghai Synchrotron Radiation Facility, China Spallation Neutron Source, atomic-manufacturing facility, and electrosynthesis institute, it extends the loop to large-scale facilities and pilot platforms; it reports deployment in six domains (life sciences, critical materials, semiconductors, nuclear fusion, quantum, Earth and weather) and dry/wet closed loops in proteins and new materials.

**Why it matters:** it is the only public system that combines an **evidence chain, a review agent, and a real experiment network** in one product; it is the closest benchmark for SciForge's evidence governance.

### 3.2 Tencent Hunyuan Hyra 2.0: an agent that trains foundation models (C/D)

[Released](https://hy.tencent.com/research/hyra2) in November 2026 ([Wallstreetcn](https://wallstreetcn.com/articles/3785563), [BlockBeats](https://en.theblockbeats.news/flash/375029)). The point is not "another model" but that the research process itself became a product:

- **Three agent layers:** Overall (resource coordination) / Mission (research planning) / Worker (experiment execution); tasks are persisted, so other work can proceed while training runs.
- **Evidence constraint:** every conclusion needs checkable support such as code and logs; an independent agent reviews when needed.
- **Experience distillation:** effective practice becomes a reusable **Skill**.
- **From scratch:** HyInv (1.96M parameters, inverse folding; 402 residues × 128 sequences in 50.6 ms on one H20 vs 2,907 ms for ProteinMPNN, ~57×), HyPLM-Flash (650M parameters, 726B tokens), and the cell model HyCell (16.1M parameters, pretrained on 79.5M human cells).
- **Evaluation:** the internal TenureTrail benchmark (123 tasks across 7 disciplines); the biosecurity benchmark Hy-BioExperimentBench scores 30.4/100, with the official conclusion that knowledge is solid but converting it into executable protocols remains limited.
- The same route improved the RISC-V "XiangShan" core (+5.79% SPEC/GHz, +0.3% area), designed a spiral-staircase hand (+28.6%), and contributed to pretraining, post-training, and inference optimization of the next Hunyuan model.

**Reading:** a public sample of "AI helping AI do research," but humans still set goals and make final judgments; "self-training" is confined to small models and narrow tasks and cannot be extrapolated to "agents can independently build large models."

### 3.3 USTC's robotic chemists: Xiaolai / Xiaolin (C/D)

According to [Xinhua's Outlook Weekly, April 2026](https://www.news.cn/liangzi/20260403/05bd0e6b42dc4dffb7822319e74ed8d1/c.html) (National Key Laboratory of Precision and Intelligent Chemistry):

- **Xiaolai** (2021): 2 mobile robots, 19 intelligent chemistry workstations, high-throughput computing; 2,000 precise operations per day, able to lift 0.1 mm carbon paper. Signature result: 3.76 million candidate formulations for a Martian oxygen-evolution catalyst would take 2,000 years by hand; Xiaolai read 50,000 papers, fused experiment and simulation, and found the optimum in **six weeks**.
- **Xiaolin** (2023): generative models, an extra arm, autonomous experiment design and optimization, and learning from failure (after hundreds of failed formulations it identified the key variable). It helped Dr Fang Tiancheng develop an energy-absorbing material in seven months versus a ten-year conventional screen.
- **Scale:** 19 distributed facilities, 80 AI-driven chemistry and materials platforms, 110 research robots, 196 intelligent chemistry workstations; the AICHEM cloud lets users place experiments remotely.
- **Standards:** a 120-member Intelligent Scientist Ecosystem Alliance (2023); in September 2025 it open-sourced the robotic-chemist instruction set, interface functions, operating system, and research templates.

**Reading:** the earliest and most complete "AI decision + robot execution" loop in China, strong in chemistry, materials, and engineering; weak on model bootstrap—it calls expert models ("Professor Xiong Yujie's brain," "Professor Zhang Guoqing's brain") rather than training new ones.

### 3.4 XtalPi Science: 80+ scientific skills + robot lab (C)

[Upgraded on 21 September 2026](https://www.news.cn/tech/20260921/04a2cbef72444a32910cb3dd7c1833f2/c.html): 80+ proprietary scientific skills and tools packaging real R&D experience, proprietary datasets, algorithms, and compute tools, covering target and patent analysis, molecule generation and property prediction, protein preparation and docking, retrosynthesis, structure–activity analysis, LC-MS parsing, and data/workflow automation. The form is **Tools / Skills / Recipes**; typing "/" opens the skill list and the agent executes. Capability now extends from the digital side to experiment execution: it connects research data systems and autonomous labs, schedules robot experiments, collects data, and adjusts subsequent tasks.

**Reading:** a "skill marketplace + robot scheduling" route, commercially the closest to deployment; closed source and drug-discovery-centric.

### 3.5 SJTU AutoDNA: 20+ instrument classes, 11,000+ steps (A, via secondary coverage)

[2026 Nature paper](https://www.nature.com/articles/s41586-026-11228-6) ([The Paper](https://m.thepaper.cn/newsDetail_forward_34434147)). A central planning agent plus six specialist agents (literature, reagents, protocols, code, hardware, hypotheses) form a design–experiment–optimize loop; a hardware abstraction layer wraps 20+ instrument classes (pipetting, incubation, sequencing) into **composable atomic services**, so the model commands the lab like an API.

- Scale: 20+ instrument classes, 11,000+ hardware steps; humans only refill reagents, replace consumables, and maintain equipment.
- Results: 97.8% single-step yield in enzymatic DNA synthesis, 3.2× parallel protocol speedup, zero-error recovery in DNA data storage, and autonomous identification of KRAS G13D in an unknown-sequence colorectal cancer sample (first primer passed validation).
- Precision: microliter liquid handling, micron positioning; multi-user concurrency and dynamic resource scheduling.

**Reading:** the cleanest public example of "instrument atomization + scheduling"; it complements Hyra's "model bootstrap" precisely.

### 3.6 Other names in the ecosystem (C, details not individually verified)

- **CAS "ChemBrain agent + ChemBody robot":** reported by [Outlook Weekly](https://www.news.cn/liangzi/20260403/05bd0e6b42dc4dffb7822319e74ed8d1/c.html) for autonomous labs.
- **Beijing Institute for AI for Science, Uni-Lab-OS:** an operating system for autonomous-lab scheduling and device access.
- **DP Technology:** compute-side capabilities such as Uni-Mol and Bohrium; it co-hosted an [AI4S workshop with XJTLU](https://www.xjtlu.edu.cn/zh/news/2026/10/shenshikeji4syantaohui) in October 2026. No public 2026 evidence of an instrument closed loop was found, so it is not counted under S3.
- **Huawei, Baidu, Alibaba:** mostly at the compute/platform layer; not included in the table.

---

## 4. International

### 4.1 Google DeepMind Co-Scientist: from hypothesis generator to research partner (A + B)

- [**Nature, 19 May 2026**](https://doi.org/10.1038/s41586-026-10644-y) (Gottweis et al.): a Gemini 2.0-based multi-agent system; it proposed drug candidates and combination therapies for acute myeloid leukaemia (cell-line experiments showed potential benefit), found a new liver-fibrosis target, and uncovered genetic mechanisms of antimicrobial resistance. The authors stress that preclinical and clinical validation are still required.
- [**August 2026 extension**](https://arxiv.org/abs/2608.26701) (B): three autonomy levels—
  - **Materials:** coupled to a semi-automated high-temperature furnace, it found a safer synthesis route for a 2D material (avoiding dangerous etching) and produced a growth recipe tailored to lab equipment; after 25 human-in-the-loop rounds it obtained layered structures, though atomic structure is not yet confirmed; three semiconductor films grew on the **first attempt**, with Gemini 3 Deep Think controlling the device directly, cutting recipe development from days to minutes.
  - **Biology:** it built an image-analysis pipeline predicting engineered E. coli colony morphology across inducer concentrations; Gemini-3-Pro-Image predictions matched unpublished lab measurements on 3 of 4 morphological features; the authors concede it only interpolates among known conditions.
  - **Computer science:** it autonomously designed Agent_H (request classification, parallel candidate generation, refinement), which beat six frontier models on health benchmarks; but in a blinded review by three physicians it was significantly better than the base Gemini 3.1 Pro on only one of nine dimensions—reduced harm.
- **Reliability modules** (the most transferable part): penalties for fabrication and plagiarism, plus an **independent checker that aligns every number in the text with the actual execution log of the code**. In a double-blind study with 30 experts, 450 independent reviews, and 150 autonomously generated papers, hallucination fell from **46%** without the modules to **4%** (the comparison system: 90%); fully fabricated data was zero (comparison: 44%); plagiarism/derivative content fell from 60% to 16%; a safety layer rejected 98.7% of potentially harmful directions. Residual problems remain: selective reporting and method descriptions that do not match the actual code.

### 4.2 FutureHouse / Edison: Robin and Kosmos (A + B + C)

- [**Nature, 19 May 2026**](https://doi.org/10.1038/s41586-026-10652-y) (Ghareeb et al.): Robin, using OpenAI o4-mini and Anthropic Claude 3.7, targets experimental biology; for dry age-related macular degeneration it identified a modifiable process in retinal cells, proposed a drug candidate not previously used for the disease, and suggested follow-up mechanism studies.
- [**Kosmos**](https://arxiv.org/abs/2511.02824) (B): data-analysis and literature agents coordinate through a shared world model; each run lasts up to 12 hours, executes ~42,000 lines of code, and reads 1,500 papers. Independent scientists judged 79.4% of statements accurate: 85.5% of data-analysis statements were reproducible, 82.1% of literature statements matched primary sources, and 57.9% of synthesis statements were accurate. Every statement cites executed code, source data, or literature, including page and figure.
- **Commercial:** on 29 October 2026 it [signed with Pfizer](https://www.rdworldonline.com/edisons-kosmos-ai-scientist-moves-into-pfizer-r-edison-details-the-math-behind-its-99-million-per-program-estimate/) to deploy Kosmos across oncology, internal medicine, immunology, and other R&D data; an earlier Incyte collaboration (19 May 2026); USD 70M raised. A case study claims ~75% reduction in IND preparation time and ~USD 99M in recovered peak sales per programme (C, company-reported; discount accordingly).

### 4.3 Lila Sciences: closed-loop catalyst discovery, the first detailed "physical-science closed loop" (B + D)

- Founded in 2023 inside Flagship Pioneering; emerged in March 2025 with a USD 200M seed, and by October 2025 had raised **USD 550M** in total (including Nvidia's venture arm).
- [September 2026 preprint](https://arxiv.org/abs/2609.30133) (B): LLMs plus statistical methods choose catalytic metal combinations; automated equipment deposits thin films and instruments measure activity and stability; **2,942 formulations** were evaluated, yielding **six families of palladium-based oxides**; the most durable, an In-Mn-Pd oxide, held for **1,000 hours** in a lab endurance test. The company says sequential learning beat some alternative search strategies.
- **The discount you must apply** ([C&EN, 4 November 2026](https://cen.acs.org/business/start-ups/lila-ai-hydrogen-catalyst-electrolyzer/104/web/2026/10), quoting UC Irvine professor Iryna Zenyuk): the test used catalyst samples, not a complete electrolyser; commercial PEM electrolysers run at roughly **300×** the current density and near 80 °C, so low-current durability cannot be extrapolated to industry; palladium is cheaper than iridium (USD 1,140 vs USD 9,100 per troy ounce), but usage and supply chain remain open. Lila's own CSO says "this is probably not the material we put in electrolysers."
- In January 2026 it received [ARIA funding](https://www.technologyreview.com/2026/01/20/1131462/the-uk-government-is-backing-ai-scientists-that-can-run-their-own-experiments/) for an "AI nano-scientist" that designs and runs quantum-dot synthesis/processing experiments.

### 4.4 Periodic Labs: the capital sample of a neolab (D)

Founded in May 2025 by former OpenAI research VP Liam Fedus and former DeepMind scientist Ekin Dogus Cubuk; in September 2025 it raised a **USD 300M** seed at a **USD 1.3B** valuation; in March 2026 it was reported to be raising hundreds of millions at ~**USD 7B** ([Bloomberg, via TFN](https://techfundingnews.com/former-openai-and-deepmind-researchers-eye-7b-valuation-for-ai-startup-periodic-labs/)). The route is robotic powder synthesis + LLM reasoning and optimization + fast ML simulation, aiming at an AI lab that runs experiments, analyses data, and improves results autonomously; it already has semiconductor customers and revenue.

### 4.5 UK ARIA: 12 of 245, "show a novel finding in nine months" (D)

In January 2026, [ARIA](https://www.technologyreview.com/2026/01/20/1131462/the-uk-government-is-backing-ai-scientists-that-can-run-their-own-experiments/) funded **12** of **245** proposals with about **£500K over nine months**; half the teams are in the UK, the rest in the US and Europe. Winners include Lila (quantum dots), the University of Liverpool (a robot chemist using a vision-language model to troubleshoot), and London stealth startup ThetaWorld (battery materials experiment design plus an automated lab). ARIA CTO Ant Rowstron's judgment: all funded projects still call existing tools; none yet reaches "the tool I need does not exist, so I will build it." He cites Lossfunk's [*Why LLMs aren't scientists yet*](https://arxiv.org/abs/2601.03315): LLM agents failed three out of four attempts to run a full research workflow, with failure modes of "drifting from the original specification toward simpler, familiar solutions" and "declaring success despite obvious failure."

### 4.6 Other European autonomous labs (C/D, background)

Liverpool's Materials Innovation Factory (MIF, one of Europe's most advanced), France's IKTOS, Switzerland's Atinary SDLabs, Germany's FULL-MAP, the US "Genesis Mission," and autonomous labs at MIT and national laboratories. Common ground: **device-level standardization plus closed-loop scheduling**, though most remain confined to chemistry and materials (European list per [Outlook Weekly](https://www.news.cn/liangzi/20260403/05bd0e6b42dc4dffb7822319e74ed8d1/c.html)).

### 4.7 Evaluation: OpenAI's two benchmarks (B/C)

- [**HealthBench**](https://openai.com/zh-Hans-CN/index/healthbench/) (May 2025): 5,000 real medical dialogues, 262 practising physicians, 48,562 weighted rubric criteria; worst-of-n reliability and comparison against a physician baseline. It turns the rubric itself into a reusable asset.
- [**BioBasicsBench**](https://openai.com/index/measuring-how-ai-agents-handle-wet-lab-science/) (November 2026): 100 tasks across five areas, with **raw wet-lab evidence** as input (gels/blots 31, protocols and records 27, tables and instrument exports 20, bench photos 18, microscopy 14, instrument screens 13, sequencing 12, protocol videos 7, plates 7); expert rubrics award partial credit; seven models, 37 model-by-reasoning-effort settings, five attempts per task, 18,500 runs, best score 66.7%. The failure taxonomy is directly reusable: assumptions overriding controls, ignoring contradictory observations, miscounting, and mistaking a z-stack for disappearing cells.
- **Why it matters:** these benchmarks do not test "can it run an experiment" but "can it read experimental evidence and know when it does not know"—the foundation of S4. OpenAI's public work so far is evaluation plus (per media) an internal plan; no closed-loop system has been published.

---

## 5. Side-by-side comparison

| System | Org / country | S1 model bootstrap | S2 compute | S3 instruments | Public evidence | Maturity | Verifiability |
|---|---|---|---|---|---|---|---|
| [Shusheng·Duanzhi](https://www.shlab.org.cn/news/5444294) | Shanghai AI Lab / China | Medium (S2/W0 models, no self-training) | Strong | **Strong** (facilities / pilot) | Official release | Platform, six domains | C |
| [Hyra 2.0](https://hy.tencent.com/research/hyra2) | Tencent / China | **Strong** (HyInv/HyPLM/HyCell) | Strong | No wet-lab evidence in public materials | Official page + media | Research platform | C/D |
| [Xiaolai/Xiaolin](https://www.news.cn/liangzi/20260403/05bd0e6b42dc4dffb7822319e74ed8d1/c.html) | USTC / China | Weak (expert models) | Medium | **Strong** (110 robots / 196 workstations) | Xinhua | Engineered, industrial use | C/D |
| [XtalPi Science](https://www.news.cn/tech/20260921/04a2cbef72444a32910cb3dd7c1833f2/c.html) | XtalPi / China | Weak | Strong (drug discovery) | Strong (robot lab) | Official release | Commercial | C |
| [AutoDNA](https://m.thepaper.cn/newsDetail_forward_34434147) | SJTU / China | Weak | Medium | **Strong** (20+ instruments, 11k steps) | Nature | Prototype → platform | A (secondary) |
| [Co-Scientist](https://doi.org/10.1038/s41586-026-10644-y) | DeepMind / UK | Medium (Agent_H architecture) | Strong | Medium (semi-automated furnace) | Nature + arXiv | Research system | A/B |
| [Kosmos](https://arxiv.org/abs/2511.02824) | FutureHouse/Edison / US | Weak | Strong (data analysis) | Weak (no wet lab) | Nature + arXiv | Commercial (Pfizer) | A/B |
| [Lila](https://cen.acs.org/business/start-ups/lila-ai-hydrogen-catalyst-electrolyzer/104/web/2026/10) | Lila Sciences / US | Medium (ML + sequential learning) | Strong | **Strong** (closed loop, 2,942 formulations) | Preprint + C&EN | Pre-commercial | B/D |
| [Periodic](https://techfundingnews.com/former-openai-and-deepmind-researchers-eye-7b-valuation-for-ai-startup-periodic-labs/) | Periodic Labs / US | Medium | Strong | Strong (robotic powder synthesis) | Media / funding | Early commercial | D |

> Reading the table: **no one is strong on both S1 and S3.** Hyra is strong on S1 and weak on S3; AutoDNA/Xiaolai are strong on S3 and weak on S1; Shusheng·Duanzhi is the most balanced, but S1 still relies on external models. **That gap is the opportunity.**

---

## 6. Five judgments

1. **The competition has shifted from "model capability" to "research state + evidence."** Hyra's persistent tasks, Shusheng·Duanzhi's Science Harness, and Kosmos's sentence-level citations to code, data, and pages say the same thing: the bottleneck in long-horizon research is context and checkability, not a single inference. This matches our evidence-chain thesis, and big labs now publicly endorse it.

2. **"Self-training models" is still a demo, not a general capability.** Hyra trained 1.96M- and 650M-parameter models; Co-Scientist's Agent_H designs an architecture rather than training a large model. Public evidence contains no case of an agent independently training a state-of-the-art scientific foundation model. Public claims should stay restrained.

3. **The bottleneck in instrument loops is interfaces and failure feedback, not models.** AutoDNA wraps instruments as atomic services, Xiaolai unifies instruction sets, interfaces, and templates, and Shusheng·Duanzhi builds a unified physical-layer protocol—all three are solving "how do devices speak the same language." The underrated point is **failure and negative-data feedback**: Shusheng·Duanzhi explicitly writes failures and anomalies back into the research process; that matters more than success stories for sustaining a loop.

4. **Evaluation only became first-class in 2026.** Kosmos 79.4%, Co-Scientist 4% hallucination, BioBasicsBench 66.7%, Hy-BioExperimentBench 30.4/100—the common message is that **"it runs" and "it is trustworthy" are far apart**. Whoever turns "insufficient evidence" into an explicit action gets closer to usable.

5. **Business models are arriving before scientific breakthroughs.** Lila (USD 550M raised), Periodic (USD 300M seed / USD 7B talks), and Edison (Pfizer/Incyte contracts) show that a closed loop itself can be sold; but Lila's electrolyser gap and Kosmos's 57.9% synthesis accuracy show that **industrial-grade trust is still far away**.

---

## 7. What it means for SciForge

### 7.1 What we should not do

- **Do not build instruments, robots, or wet labs.** The moat of AutoDNA, Xiaolai, and Lila is hardware and engineering, not models.
- **Do not chase the "general AI scientist" narrative.** Kosmos's lesson is that synthesis statements are the least reliable (57.9%), while data-analysis and literature statements are far more reliable (85.5% / 82.1%). SciForge's strength is exactly those two.

### 7.2 What we can do (ordered by differentiation)

| Opportunity | Basis | Minimum move |
|---|---|---|
| **Verifiable orchestration layer** | Shusheng·Duanzhi's seven-dimension review + evidence chain; Kosmos's sentence-level citations | Map the seven dimensions onto SciForge's existing evidence DAG / artifact-versions; start with 2–3 (evidence and provenance, reproducibility, review history) |
| **Make "insufficient evidence" explicit** | BioBasicsBench scores it; Co-Scientist's 4% hallucination relies on a checker | Add an `insufficient` verdict with reasons at the claim/note layer, as a scorable action |
| **Cross-institution / cross-instrument adapter contract** | AutoDNA's atomic services; Shusheng·Duanzhi's physical-layer protocol; Xiaolai's instruction set | Define a read-only "instrument adapter" schema (capabilities, inputs, outputs, failure codes); connect simulators and public data first |
| **Local-first / auditable** | Duanzhi is cloud plus a local client; SciForge is desktop plus local evidence | Emphasize "data never leaves the machine, evidence travels"—the differentiation from the platform route |

### 7.3 Three concrete moves (three months)

1. **Benchmark decomposition:** turn Shusheng·Duanzhi's seven dimensions, Co-Scientist's reliability modules, and Kosmos's citation granularity into a "have / can borrow / will not borrow" table (one week).
2. **One end-to-end demo:** pick a public paper, a public dataset, and a simulated instrument (or a public instrument log); run the chain "claim → evidence → compute → instrument record → review," with every node clickable back to the original text or record (four to six weeks).
3. **One-page external note:** use the gap in Section 5 (no one is strong on both S1 and S3) to position SciForge: not the strongest model, not the strongest robot, but **the most verifiable layer between them** (one week).

---

## 8. Counter-evidence and risks (do not read only the good news)

| Counter-evidence | Source | Implication |
|---|---|---|
| LLM agents failed three of four attempts to run a full research workflow | [Lossfunk, arXiv 2601.03315](https://arxiv.org/abs/2601.03315) (D) | "Fully automated science" is overhyped; failure modes are downgrading to familiar plans and declaring success |
| Only 57.9% of an AI scientist's synthesis statements are accurate | [Kosmos, arXiv 2511.02824](https://arxiv.org/abs/2511.02824) (B) | The further toward synthesis and interpretation, the less reliable; citation granularity is key |
| Lab results ≠ industrial conditions | [Lila, C&EN, 4 Nov 2026](https://cen.acs.org/business/start-ups/lila-ai-hydrogen-catalyst-electrolyzer/104/web/2026/10) (D) | Commercial PEM current density is ~300× the test; do not tell an industrial story from lab data |
| Co-Scientist's physician review was significant on only 1 of 9 dimensions | [arXiv 2608.26701](https://arxiv.org/abs/2608.26701) (B) | Benchmark scores ≠ clinical value; automated review agrees weakly with experts |
| "No precedent" claims are easy to refute | This survey found six systems covering three or more stages | Write "we did not find," not "there is none" |
| Most systems are closed and not reproducible in detail | Duanzhi / XtalPi / Hyra / Periodic | Mark "company-reported" and do not treat it as independent validation |

---

## 9. Sources (by evidence grade)

**A peer-reviewed**

- Gottweis, J., Weng, W-H., Daryin, A. et al. *Accelerating scientific discovery with Co-Scientist.* Nature (19 May 2026). [https://doi.org/10.1038/s41586-026-10644-y](https://doi.org/10.1038/s41586-026-10644-y)
- Ghareeb, A.E., Chang, B., Mitchener, L. et al. *A multi-agent system for automating scientific discovery.* Nature (19 May 2026). [https://doi.org/10.1038/s41586-026-10652-y](https://doi.org/10.1038/s41586-026-10652-y)
- AutoDNA: [Nature (2026)](https://www.nature.com/articles/s41586-026-11228-6) (paper is A-level; this survey read only secondary coverage, so the evidence is used as D)
- Nature editorial *Why AI cannot do good science without humans*: [https://www.nature.com/articles/d41586-026-01551-3](https://www.nature.com/articles/d41586-026-01551-3)

**B preprints**

- Co-Scientist extension: [arXiv 2608.26701](https://arxiv.org/abs/2608.26701) (August 2026).
- Kosmos: [arXiv 2511.02824](https://arxiv.org/abs/2511.02824) (November 2025).
- Lila catalysts: [arXiv 2609.30133](https://arxiv.org/abs/2609.30133) (September 2026).
- *Why LLMs aren't scientists yet*: [arXiv 2601.03315](https://arxiv.org/abs/2601.03315) (January 2026).

**C official releases**

- Shanghai AI Lab, *Shusheng·Duanzhi opens full-stack services*, 13 September 2026: [https://www.shlab.org.cn/news/5444294](https://www.shlab.org.cn/news/5444294)
- Tencent Hyra 2.0 official page: [https://hy.tencent.com/research/hyra2](https://hy.tencent.com/research/hyra2)
- XtalPi Science upgrade (Xinhua/Global Times, 21 September 2026): [https://www.news.cn/tech/20260921/04a2cbef72444a32910cb3dd7c1833f2/c.html](https://www.news.cn/tech/20260921/04a2cbef72444a32910cb3dd7c1833f2/c.html)
- Nature press release (Co-Scientist + Robin, 20 May 2026): [https://www.natureasia.com/en/info/press-releases/detail/9330](https://www.natureasia.com/en/info/press-releases/detail/9330)

**D media**

- Outlook Weekly / Xinhua, *Intelligent Scientists Are Here*, 3 April 2026: [https://www.news.cn/liangzi/20260403/05bd0e6b42dc4dffb7822319e74ed8d1/c.html](https://www.news.cn/liangzi/20260403/05bd0e6b42dc4dffb7822319e74ed8d1/c.html)
- Wallstreetcn, *Tencent's Yao Shunyu: AI will soon truly master biology*, 9 November 2026: [https://wallstreetcn.com/articles/3785563](https://wallstreetcn.com/articles/3785563)
- BlockBeats, *Hyra 2.0 English flash*: [https://en.theblockbeats.news/flash/375029](https://en.theblockbeats.news/flash/375029)
- C&EN, *Lila Sciences tests AI's ability to find hydrogen catalysts*, 4 November 2026: [https://cen.acs.org/business/start-ups/lila-ai-hydrogen-catalyst-electrolyzer/104/web/2026/10](https://cen.acs.org/business/start-ups/lila-ai-hydrogen-catalyst-electrolyzer/104/web/2026/10)
- MIT Technology Review, *The UK government is backing AI that can run its own lab experiments*, 20 January 2026: [https://www.technologyreview.com/2026/01/20/1131462/the-uk-government-is-backing-ai-scientists-that-can-run-their-own-experiments/](https://www.technologyreview.com/2026/01/20/1131462/the-uk-government-is-backing-ai-scientists-that-can-run-their-own-experiments/)
- R&D World, *Edison's Kosmos AI scientist moves into Pfizer R&D*, 6 November 2026: [https://www.rdworldonline.com/edisons-kosmos-ai-scientist-moves-into-pfizer-r-edison-details-the-math-behind-its-99-million-per-program-estimate/](https://www.rdworldonline.com/edisons-kosmos-ai-scientist-moves-into-pfizer-r-edison-details-the-math-behind-its-99-million-per-program-estimate/)
- Tech Funding News, *Periodic Labs*, 26 March 2026: [https://techfundingnews.com/former-openai-and-deepmind-researchers-eye-7b-valuation-for-ai-startup-periodic-labs/](https://techfundingnews.com/former-openai-and-deepmind-researchers-eye-7b-valuation-for-ai-startup-periodic-labs/)
- The Paper, *From assisting experiments to organizing experiments: SJTU's AutoDNA*, 9 November 2026: [https://m.thepaper.cn/newsDetail_forward_34434147](https://m.thepaper.cn/newsDetail_forward_34434147)

**Not verified / to be added**

- Hyra technical reports (HyInv / HyPLM-Flash / HyCell); details of TenureTrail and Hy-BioExperimentBench; the full AutoDNA Nature paper; the full Co-Scientist and Robin Nature papers; the full Kosmos arXiv paper; the full Lila preprint.
- ChemBrain/ChemBody, Uni-Lab-OS, and DP Technology's 2026 instrument-loop evidence.
- The scale and project list of the US "Genesis Mission."

---

## 10. If you remember only three things

1. **All three stages have been demonstrated, but no one is strong on all three.** Duanzhi is the most balanced, Hyra is strong on model building, AutoDNA/Xiaolai are strong on instrument control; on public evidence, no system is strong on both S1 and S3.
2. **Trustworthiness is the 2026 battleground.** 4% hallucination, 79.4% statement accuracy, 57.9% synthesis accuracy, 30.4/100 biosecurity—these numbers matter more than another model release.
3. **For SciForge, the right position is the middle layer.** Not the strongest model, not the strongest robot, but the layer where evidence can be checked, state is not lost, and failures flow back—precisely what Duanzhi is building but has not open-sourced.
