# Research

Questionize depends on AI for six jobs. Each one is a claim that a demo cannot prove: it has to be measured against ground truth, tracked over time, and improved only by changes that win on its measure. This folder holds the map of those jobs, the preregistered experiments that test them, and the record of every run.

## The six capabilities

A learner's snapped question flows through them in order, so an error early on spoils everything after it. Each capability is therefore measured twice: **in isolation**, fed verified inputs (so a solving error is not really a reading error), and **end to end**, from the photo.

```
C1 Capture ─▶ C2 Understand the item ─▶ C3 Solve & explain ─▶ C4 Diagnose the learner ─▶ C5 Write practice
                                                                                      └─▶ C6 Choose practice
```

| | Capability | Question it answers | Ground truth | Experiments |
|---|---|---|---|---|
| C1 | Capture | Did we get the whole question, exactly, in a form that can be solved again? | The printed page, read by a person; OCR as an automatic check | E4 |
| C2 | Understand the item | What subject, skill, objective, difficulty and traps is this question built from? | The book's type labels and explanations; experts; answer statistics | E5, E3 (H2c) |
| C3 | Solve and explain | Which answer is right, and why is each option right or wrong, at the learner's level? | The book's key and explanations; blind expert ratings | E1, E6 |
| C4 | Diagnose the learner | What does this miss, and the learner's history, say about what they can and cannot do yet? | The learner's later answers; expert misconception labels | E3 |
| C5 | Write practice | Can we write new questions that train the same objective, at the same level, as well as published ones do? | Verification gates; blind expert ratings; how learners actually answer | E2 |
| C6 | Choose practice | Of the questions we have, which should this learner do next? | The learner's success rate and later gains | E7 |

Two levers cut across all six and are what the experiments vary: **verification** (independent solvers, the critic, the Argument Judge, debate between models) and **memory** (designs, misconceptions and examples learned from keyed items, retrieved into prompts). Changing models or prompts counts as an improvement only when it wins on the capability's measure (DECISIONS D6). The original research questions map onto this: RQ1 (a reliable writer and explainer without retraining) is C3 and C5; RQ2 (what a learner's misses reveal) is C2, C4 and C6.

Not every capability is a language-model job. C1 uses OCR as a check, C4 and C6 rest on psychometrics (Elo now, IRT and knowledge tracing later; DECISIONS D4–D5), and the language model names what numbers cannot: the misconception behind a choice, the objective of an item.

### C1 Capture: extract and reconstruct

**Tasks.**
- *C1.1 Extract.* Find every part of the question in the photo and assign each its role: passage, stem, options, and any figure, table, graph, diagram, worked example or code; plus, when the photo shows them, the book's key and explanation, and which option the learner marked. The parts are not fixed in advance: a math question has a figure, a reading set has a long passage and line numbers, a data question has a table. The model has to know what a question can contain and recognize what this one does.
- *C1.2 Reconstruct.* Rebuild the question so it can be solved again without the photo: text exactly as printed; tables as tables; charts as their data; functions as formulas; geometric figures as the given measures and relations (and a drawing generated from them); anything that cannot be rebuilt faithfully is marked so, not guessed.

**Approach.** The model reads the page and returns the parts as structured fields; OCR, where available (Apple Vision or Tesseract offline), checks the text word by word, and a printed key checks the key. The structure is simple fields, not line coordinates. **Current:** the Snap reader handles text questions; the scan importer extracts text, key and explanation from answer sections; figures, tables and formulas are not yet reconstructed.

**Measures and bars.** Character error rate of the text (≤ 1% printed scans, ≤ 2% phone photos); share of items with every role right (≥ 98%); key read correctly (≥ 99%). For reconstruction, **solvability equivalence**: a solver given the reconstruction reaches the same answer as one given the original image, and a person judges the reconstruction faithful (≥ 95% of items with figures). Reported by element type (text, table, chart, function, geometry) and input (scan, phone photo).

**Where the field is.** Printed-text OCR is close to solved; document models turn academic pages into markup (Nougat, Blecher et al. 2023). Charts and diagrams are the hard part: on ChartQA (Masry et al. 2022) and MathVista (Lu et al., ICLR 2024) models still trail people, and MathVerse (Zhang et al., ECCV 2024) shows multimodal models often answer from the text while ignoring the diagram. Geometry problems can be parsed into a formal language of measures and relations and then solved (Inter-GPS, Lu et al. 2021), which is the form C1.2 targets.

### C2 Understand the item

**Tasks.** Name the subject and skill (sub-type), the objective the item assesses (the competency in KNOWLEDGE_MODEL §3.2), its difficulty on our scale, and for each option the trap it sets.

**Measures and bars.** Skill agreement with the book's own type label (≥ 90%); trap tags judged correct against the book's per-option explanation (≥ 80%); difficulty: Spearman correlation with observed correct rates once items have answers (≥ 0.4), and with the book's difficulty ordering before that.

**Where the field is.** Predicting difficulty from item text is still weak: in the BEA 2024 shared task on medical exam items, most systems barely beat a predict-the-mean baseline. Language models tag skills and knowledge components reasonably well. Distractors carry the misconception they target, which is why traps are tagged per option.

### C3 Solve and explain

**Tasks.** *C3.1* choose the right answer; *C3.2* explain why it is right and why each other option is wrong; *C3.3* say it at the learner's level and address the option they chose.

**Measures and bars.** Accuracy against the book's key (≥ 95% on CR); explanations rated correct, blind, by an expert with the book's explanation as reference (≥ 90%, none rated wrong on the keyed option); calibration of stated confidence (ECE); for C3.3, readability inside the level's band (≥ 90%) and a blind comparison of a level-adapted explanation with a generic one.

**Where the field is.** Logical-reasoning sets built from GMAT and LSAT items (ReClor, Yu et al. 2020; LogiQA, Liu et al. 2020) are largely solved by frontier models, and GPT-4 scored around the 88th percentile on the LSAT (OpenAI 2023). Explanations lag answers: a correct letter can come with wrong reasons. Debate between models improves reasoning and factuality, more with different models (Du et al., ICML 2023).

### C4 Diagnose the learner

**Tasks.** From one miss: the misconception behind the choice and the skill it implicates. From a history: a profile of skills, traps and misconceptions with how sure we are (LEARNING_MODEL §3).

**Measures and bars.** Misconception top-3 agreement with an expert label (≥ 70%); the profile predicts the learner's next misses better than overall accuracy (AUC ≥ 0.65 and above the baseline); claims shown only with enough evidence (§3.2).

**Where the field is.** Knowledge tracing has a long line from Bayesian Knowledge Tracing (Corbett & Anderson 1994) to Deep Knowledge Tracing (Piech et al. 2015), with Elo as a strong, simple online method (Pelánek 2016). Cognitive diagnosis models (DINA) map answers to skills. Naming misconceptions from wrong answers with language models is promising but unsolved (Eedi's 2024 misconception competition).

### C5 Write practice

**Tasks.** From a missed question's abstract design, write new questions that train the same objective with the same trap, at the learner's level, with explanations; never reusing the source's wording.

**Measures and bars.** First-draft verification pass rate; Argument Judge first-rate and margin; share with two defensible answers (≤ 2%); blind expert preference against published items; once answered, observed difficulty inside the level's band and distractor health (LEARNING_MODEL §6.1); the same trap actually chosen by learners who fell for it before.

**Where the field is.** Generated questions are usually grammatical and answerable; distractor quality and difficulty control are the weak points. Retrieved examples improve distractors (Bitew et al. 2023); simulated students can estimate item quality before real ones (Generative Students, Lu & Wang 2024). Black-box models improve from accumulated experience without retraining (ExpeL, Zhao et al., AAAI 2024; Dynamic Cheatsheet, Suzgun et al. 2025), and accumulating it without a correctness signal can reinforce errors, which is why keys are required (DECISIONS R2).

### C6 Choose practice

**Tasks.** From the bank, pick the questions this learner should do next: their weakest skills, at about 70% expected success, with spaced review (LEARNING_MODEL §5).

**Measures and bars.** Success rate on recommended questions (60%–80%); rating gain on targeted skills over two weeks compared with learners practicing unrecommended questions; same-trap error rate falling.

**Where the field is.** Rules from psychometrics are a strong start; multi-armed bandits that track each learner's zone of proximal development beat expert sequences in classrooms (ZPDES, Clement et al. 2015), and are our next step once enough outcomes exist (DECISIONS D5).

## Experiments

| ID | Capability | Status | Protocol |
|---|---|---|---|
| E1 | C3.1, C3.2 solve and explain official items: single model (B0), verification loop (B1), two-model debate (B2); each again with a memory learned on the train split (+M) | Registered (v2); dataset being built | [E1](protocols/E1-solve-and-explain.md) |
| E2 | C5 does a memory of learned designs improve generated questions | Registered | [E2](protocols/E2-design-memory.md) |
| E3 | C4 (and C2 difficulty) what a learner's misses reveal | Registered, pilot | [E3](protocols/E3-error-log-diagnosis.md) |
| E4 | C1 capture fidelity: text, roles, key, and figure reconstruction; produces the verified, split dataset | Registered | [E4](protocols/E4-capture.md) |
| E5 | C2 item understanding: skill, objective and traps against the book | Planned | |
| E6 | C3.3 level-adapted explanations | Planned | |
| E7 | C6 recommendations: success rate and gains, simulated students first | Planned | |

Run with `ai/eval` runners; every run appends one line to [`ledger.jsonl`](ledger.jsonl) with the capability it measures, and `python -m questionize.scoreboard` turns the ledger into [`results/SCOREBOARD.md`](results/SCOREBOARD.md): the latest result for each capability against its bar.

## How experiments are recorded

Every experiment follows the same four steps, so results can be trusted and repeated.

1. **Preregister.** Before running, write `protocols/E<n>-<name>.md` from the template: hypothesis, conditions, dataset, metrics, analysis, stopping rule. Commit it. A protocol changed after results exist gets a new version number and says why.
2. **Run.** `ai/eval` runners execute a protocol and write one run directory outside the repository (see Data policy). Each run has a `manifest.json`:
   - `run_id`, `protocol` and version, `started_at`;
   - `git_sha` of the code, `prompts_hash` (hash of the prompts, levels, judge and runner source), `judge_version`;
   - providers and exact model IDs, temperatures, seeds;
   - `dataset_id` and the hash of its private contents;
   - per-condition costs (calls, tokens) and wall time.
3. **Record.** One line per run is appended to [`ledger.jsonl`](ledger.jsonl): the manifest's identifying fields, the capabilities measured (`capabilities`, e.g. `["C3.1", "C3.2"]`), plus the summary metrics per condition with confidence intervals. The ledger is append-only; a bad run is never deleted, it gets a later line `{"invalidates": "<run_id>", "reason": "…"}`.
4. **Report.** `results/E<n>.md` explains the outcome against the preregistered hypothesis, including null and negative results, and links the ledger lines it uses.

An experiment that changes how a capability works (a new prompt, model, memory or check) is kept only if it beats the current version on that capability's primary measure; the losing version stays in the ledger.

Human judgments (blind ratings of explanations and items, misconception labels) are collected on rating sheets with item IDs and condition labels hidden, then joined after rating. Inter-rater agreement is reported whenever there is more than one rater.

## Data policy

Official test items and learners' books are copyrighted, and learners' answers are personal. So:

| Kept in this repository (public) | Kept outside it (private storage, never committed) |
|---|---|
| Protocols, runners, prompts, templates | Item text, photos, transcriptions |
| Ledger lines and aggregate results | Per-item model outputs that quote items |
| Dataset manifests: counts, kinds of sources, hashes | Human rating sheets with item text |
| Abstract designs authored by us (`api/db/seeds/designs.json`) | Anything that identifies a learner |

Answer keys enter as letters only. Datasets of official items are used for internal evaluation only and are not redistributed.

Live product evidence (answer tallies, judge measurements, item statistics) stays in the application database; periodic `evidence_snapshots` are exported as aggregate results here.

