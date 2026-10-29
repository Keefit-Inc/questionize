# Research

Questionize makes two claims that a demo cannot prove: that a general LLM can become a reliable question writer and explainer through verification and accumulated experience rather than retraining (RQ1), and that a learner's missed questions reveal their competencies well enough to guide practice (RQ2). This folder is where those claims are tested and where the record of every test is kept.

## Questions and hypotheses

**RQ1. Can a general LLM be turned into a reliable question writer and explainer without retraining?**

| Condition | What it adds |
|---|---|
| B0 | One model, asked directly |
| B1 | Our verification loop: blind solver, critic, Argument Judge, reviser |
| B2 | B1 + a debate between two different models (Muse Spark 1.3 and Muse Spark Open) to settle the key and the explanation |
| B3(n) | B1 + a memory of question designs (blueprints) consolidated from n learned items, n = 0, 25, 50, 100 |

- H1a: B1 and B2 solve official-style items more accurately than B0, and their explanations are judged correct more often.
- H1b: Items generated under B3(n) pass verification on the first draft more often, with larger judge margins and better blind expert ratings, as n grows.
- H1c: Without answer keys, accumulated designs do not reliably improve quality (keys are the learning signal; see Prior work).

**RQ2. Can a learner's missed questions reveal their competencies and what to practice?**

- H2a: A weakness profile built from snapped misses predicts which unseen items the learner gets wrong better than overall accuracy or overall rating (AUC).
- H2b: The misconception named for a miss agrees with an expert's label (top-1 and top-3 agreement).
- H2c: Difficulty assigned at diagnosis correlates with observed correct rates.
- H2d: After same-trap practice, the learner falls for that trap less often than before (pilot; simulated students first).

## How experiments are recorded

Every experiment follows the same four steps, so results can be trusted and repeated.

1. **Preregister.** Before running, write `protocols/E<n>-<name>.md` from the template: hypothesis, conditions, dataset, metrics, analysis, stopping rule. Commit it. A protocol changed after results exist gets a new version number and says why.
2. **Run.** `ai/eval` runners execute a protocol and write one run directory outside the repository (see Data policy). Each run has a `manifest.json`:
   - `run_id`, `protocol` and version, `started_at`;
   - `git_sha` of the code, `prompts_hash` (hash of the prompts, levels, judge and runner source), `judge_version`;
   - providers and exact model IDs, temperatures, seeds;
   - `dataset_id` and the hash of its private contents;
   - per-condition costs (calls, tokens) and wall time.
3. **Record.** One line per run is appended to [`ledger.jsonl`](ledger.jsonl): the manifest's identifying fields plus the summary metrics per condition with confidence intervals. The ledger is append-only; a bad run is never deleted, it gets a later line marking it `invalidated` with the reason.
4. **Report.** `results/E<n>.md` explains the outcome against the preregistered hypothesis, including null and negative results, and links the ledger lines it uses.

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

## Prior work this builds on

- ReClor (Yu et al., ICLR 2020): logical reasoning items from GMAT and LSAT; separating items answerable from the options alone.
- ExpeL (Zhao et al., AAAI 2024) and Dynamic Cheatsheet (Suzgun et al., 2025): improving black-box models with accumulated natural-language experience instead of weight updates.
- Multiagent debate (Du et al., ICML 2023): models critiquing each other improve reasoning and factuality, more so with different models.
- Retrieved examples for distractor generation (Bitew et al., 2023); distractors compared with real student choices (2025).
- Eedi's misconception mining competition and follow-up work: linking wrong answers to misconceptions, and the current limits of LLM diagnosis.
- BEA 2024 shared task on item difficulty prediction; Generative Students (Lu & Wang, 2024) for simulated respondents.
