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

Each capability has its own folder under [`capabilities/`](capabilities/), numbered so they sort in pipeline order: the definition, ground truth, measures and bars, where the field stands, and its improvement history.

| Folder | Capability |
|---|---|
| [`C1-capture`](capabilities/C1-capture/) | Extract the question's parts from a photo or scan and reconstruct it so it can be solved again |
| [`C2-understand`](capabilities/C2-understand/) | Name the item's subject, skill, objective, difficulty and per-option traps |
| [`C3-solve-explain`](capabilities/C3-solve-explain/) | Find the right answer and explain every option, at the learner's level |
| [`C4-diagnose`](capabilities/C4-diagnose/) | Say what a miss, and the learner's history, show about their skills and misconceptions |
| [`C5-write-practice`](capabilities/C5-write-practice/) | Write new questions that train the same objective as well as published ones |
| [`C6-choose-practice`](capabilities/C6-choose-practice/) | Pick the bank questions this learner should do next |

**Where the boundaries are.** C2 describes the item (the trap a distractor is built to set); C4 describes the learner (which traps and misconceptions actually catch them). C3.3 uses C4's profile but is judged as an explanation. C5 writes; C6 only selects. Verification and memory are levers that change several capabilities, not capabilities themselves; so are the eligibility checks (live-exam suspicion, content flags), which are policy gates measured separately.

### Subjects

Capabilities are the same for every subject; what changes per subject is the content they work on. So the research is a matrix, **capability × subject**: every ledger line names its `subject` (`CR`, `RC`, later `math-geometry`, `physics-mechanics`, …), and the scoreboard and each capability's `HISTORY.md` keep subjects apart, so a gain in math never hides a loss in CR.

A new subject is added as a **subject pack** in [`subjects/`](subjects/): its skills and objectives, the parts its questions contain (figures, tables, formulas, units), its traps and misconceptions, its levels, its datasets, and any bar that differs from the default (for example C1.2 reconstruction for geometry figures). No capability folder changes; each gains rows for the new subject.

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
| E8 | C3.1 GMAT CR policy proposal, recorded decision replay, acceptance/hold and verified service application | Registered (v1); engineering regression scope, not fresh model accuracy | [E8](protocols/E8-policy-evolution.md) |

Run with `ai/eval` runners; every run appends one line to [`ledger.jsonl`](ledger.jsonl) with the capability it measures, and `python -m questionize.scoreboard` turns the ledger into [`results/SCOREBOARD.md`](results/SCOREBOARD.md) (the latest result for each capability against its bar) and each capability's `HISTORY.md` (every run, what changed, the result).

The same command exports [`results/dashboard.json`](results/dashboard.json), a versioned, aggregate-only data contract for the separate Vue + TypeScript research console at `/admin`. The console filters by subject, capability, evaluation scope and condition; shows uncertainty and provenance; and compares recorded runs without treating changed datasets, prompts or samples as a controlled improvement. Trial runs stay separate from full evaluations, and a capability stays unmeasured until its own metric is recorded. It exposes no item text, private outputs, rating sheets, credentials or experiment execution. Refreshing the console fetches the current deployed ledger snapshot; new runs are published by regenerating the export and deploying the app image.

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

