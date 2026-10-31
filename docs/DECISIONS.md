# Decisions

The product and technical decisions that shape Questionize, with the reason for each. New work should fit these; changing one means adding a dated entry here that says what changed and why. Details live in `ARCHITECTURE.md`, `KNOWLEDGE_MODEL.md` and `LEARNING_MODEL.md`.

## Product

| # | Decision | Why |
|---|---|---|
| P1 | **Critical Reasoning first, with Reading Comprehension.** Sentence Correction is off by default; logic games and other subjects come later as subject packs. | Argument reasoning is what tests and schools share across ages, and what readers practice least. |
| P2 | **The core asset is a measured knowledge model, not a pile of questions.** Competencies, misconceptions, trap patterns and question designs, each with evidence. | Questions are cheap to generate; knowing which designs and traps work for whom is not. |
| P3 | **Every question is measured before and after it is published.** Blind solver, critic, Argument Judge and copy check before; answers, votes, reports and re-review after. | A plausible question is not a correct one. |
| P4 | **Snap (the error log) is the main way in.** One photographed question at a time, cropped by the learner; the same intake for every future subject. | Questions people actually miss are the densest evidence of what they need and of which traps work. |
| P5 | **No copy of a learner's book on our servers.** Photos are read once and deleted; the question's words go only to the learner's device; only abstract designs reach the commons. | Copyright, and the learner's trust. |
| P6 | **Practice questions written from abstract designs join the shared bank**, rated by the learners who answer them. | They contain nothing from the source, and every learner benefits. |
| P7 | **One global level per learner** (Grades 3–5, 6–8, 9–12, College & adult, GMAT, LSAT, GRE). Everything written for them follows it; it changes only in Me. | Same reasoning at every age; the language and subtlety change. |
| P8 | **Three tabs: Snap, Questions (My misses · Bank · Archived), Me (Analysis · Stats).** A snapped question opens on Question, then Analysis, then Practice. | Camera first; review second; insight third. |
| P9 | **Web app (Vue, installable) now; native app (Flutter) after the MVP; the extension stays Vue.** | One code base to validate the flow before porting it. |
| P10 | **Built on Meta:** Muse Spark models by default, Facebook Login, sharing to Facebook, Threads, WhatsApp and Instagram. | The demo runs on Meta models; Meta's surfaces are where learners share. |
| P11 | **13 and older; photo analysis in the United States at launch.** Grades 3–5 is for a parent or teacher with the child until parental-consent accounts exist. | Children's privacy law (COPPA) and a contained launch. |
| P12 | **Licenses:** code MIT; questions and descriptive knowledge CC BY-NC-SA 4.0 from 2026-10-29 (CC BY-SA before); numeric data and learner analytics not openly licensed. | Open to learn from, while calibrated data remains Keefit's. |
| P13 | **Capture is model-first.** The model is expected to know what a question can contain (passage, options, figures, tables, graphs, formulas, worked examples, the book's key and explanation) and to find and rebuild whatever this one has, returned as simple structured fields. OCR and layout rules check its text where they are available; they do not replace it. | Learners will snap every kind of question; parts cannot be hand-structured per subject, and a question missing its figure cannot be solved again. |
| P14 | **Expose GMAT, LSAT and GRE first, with GMAT as the default.** The other four levels stay in the catalog and can be shown with the single web build setting `VITE_ALL_LEVELS=true`; existing profiles and the data model remain valid. Expand to younger audiences before adding subjects, with an audience brief, suitable item formats, independent evaluation data, and the required account flows for each expansion. (2026-10-29) | Keep the initial experience focused on the reasoning tasks we can evaluate, while retaining the path to broader education. |

## Research

| # | Decision | Why |
|---|---|---|
| R1 | **Claims are tested as experiments** with preregistered protocols, an append-only ledger and written results (`research/`). | "Better than just using an LLM" has to be shown in numbers. |
| R2 | **Answer keys are the learning signal.** Curated items enter with the book's key letter; designs learned without keys are not trusted to improve generation. | Accumulating observations without a signal can reinforce errors (see research/README.md, prior work). |
| R3 | **Learn first, generate later.** Seeding extracts designs; level-wide generation waits for designs corroborated by several independent sources. | Early, unverified designs produce weak questions at scale. |
| R4 | **Official items stay private.** Only aggregate results and our own abstract designs are published. | Copyright; evaluation use only. |
| R5 | **AI work is organized as six capabilities**, each with a ground truth, a primary measure and a bar: C1 capture, C2 understand the item, C3 solve and explain, C4 diagnose the learner, C5 write practice, C6 choose practice. Each is measured in isolation and end to end; a change is kept only if it wins on its capability's measure; `research/results/SCOREBOARD.md` shows where each stands. | Errors flow downstream from capture to practice; measuring each step separately shows where to improve. |

## Data and modeling

| # | Decision | Why |
|---|---|---|
| D1 | **PostgreSQL is the only database.** Rails owns all state; the AI service is stateless. | One store to back up, secure and reason about on a small server. |
| D2 | **The knowledge model is a graph stored as tables** (`competency_edges` for prerequisites, link tables for competency–misconception and trap–target), queried with recursive SQL. No graph database. | Hundreds to thousands of nodes; the queries we need (prerequisites of a weak skill, misconceptions of a competency) are a few joins. Apache AGE inside PostgreSQL is the upgrade path if graph queries grow. |
| D3 | **Similarity search with pgvector in the same PostgreSQL**, when we add it: near-duplicate items, retrieving designs and similar verified items as examples for generation, clustering observations into designs, retrieving candidate misconceptions for a wrong answer before ranking them. No separate vector database. | Retrieval improves distractors and misconception matching in prior work; pgvector is proven at our scale and keeps one store. Needs an embedding model: computed in the AI service or offline, not on the small app server. |
| D4 | **Learner modeling uses established psychometrics, not a custom neural model.** Elo online now; a Rasch / 2PL IRT fit per level offline once items have about 100 answers; Bayesian Knowledge Tracing per skill when answer sequences exist; deep knowledge tracing only at a scale of hundreds of thousands of answers. | These methods work with little data, are interpretable ("weak at assumptions, based on 12 answers"), and are what the research questions need to measure. |
| D5 | **Recommendations are rules on top of the measurements** (weakest skills, target about 70% success, spaced review), evaluated by observed success rate; a contextual bandit replaces the rules only when enough outcomes exist to beat them. | A learned recommender needs outcome data we don't have yet; the rules are testable today. |
| D6 | **Choose specialization methods by measured capability and resource gains.** Compare prompts, retrieved designs, independent tools and open-weight adapter training against the same base. Adopt changes only after paired quality, regression and resource checks. Start with reliable solving, then learner diagnosis and verified writing. Keep source-private references separate from rights-cleared distributable training data. | Neither a more expensive base model nor running a learning pipeline demonstrates our contribution. Local Meta specialization is a supported path; its benefit must be measured. Training, explanation quality and learner outcomes require separate evidence. |
