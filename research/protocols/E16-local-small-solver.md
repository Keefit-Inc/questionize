# E16 — Small Meta Solver, local and label-blind

Registered before the first source-question inference in this study. Hardware smoke
tests use separately authored examples and are not accuracy evidence. This study
does not resume the stopped E15 experiment or any paid API research.

## Goal and sequence

Target zero remaining errors on valid, adjudicated items, while keeping the
deployment small enough for local use. A finite observed 100% is not a guarantee
on arbitrary future questions. First improve C3.1 solving; measure C2 item
understanding and C3.2 explanations separately. C4 learner diagnosis requires
learner-response evidence; C5 writing also requires uniqueness, defect and
teaching-quality checks. A good Solver alone establishes neither capability.

Two work streams continue: (1) private source acquisition, restoration, provenance
and exact/near deduplication; (2) same-base Solver improvement and independent
evaluation. Newly acquired source questions are not silently mixed into training.
Expert originals, key-only references and AI-derived hypotheses keep distinct
origins. Publicly distributable training data needs a separate rights decision.

## First local feasibility cohort

Use the Meta Llama 3.2 1B Instruct base, in a pinned community MLX 4-bit conversion.
This is a small public-weight starting point, not a claim that it is the cheapest
possible deployment or the newest Meta model. Its Llama community license still
applies. Pin model revision, local file hashes, runtime versions and prompts.
No remote code, inference API, external judge or reference answer enters inference.

Take two deterministically selected items per available subtype from the existing
54-item OG development cohort (previous `test` and `completion_validation`). These
items have already been exposed during earlier research. They are development
and hardware feasibility evidence, never a fresh final benchmark. Freeze the
membership before inference. Report every attempt, including malformed output,
truncation and input failures; no retries or best-of sampling.

Run baseline and fixed procedure with the same checkpoint, temperature zero,
maximum generated tokens and question fields. The procedure explicitly identifies
task, conclusion, option scope and unsupported assumptions. Report changes in
correctness alongside measured tokens, time and memory; identical token caps do
not establish equal actual resource use. Preserve raw outputs locally. Source-key
agreement is not independent human adjudication; explanation quality is unmeasured.

## Next gates

Before model training, freeze original/rights-cleared training examples and
structural validation groups. A training smoke test proves tool compatibility,
not improvement. Compare the same base with/without the adapter under identical
inference settings; keep any checker identical in both and also ablate it.
Use held-out structures and boundary cases, not only renamed training templates.
Existing E15 partial confirmation outputs remain exposed and incomplete.

Do not deploy a candidate merely because the pipeline ran. Record unresolved
errors, fixes, regressions and resource use. When no improvement appears in the
small development pilot, diagnose before scaling the evaluation. Do not relabel
AI consensus as a reference key, count abstention as correct, remove misses after
seeing results, or infer learner improvement from Solver accuracy.

Only aggregate, explicitly projected evidence may enter the public ledger/console.
Original questions, source explanations, local paths and per-item outputs remain
private. The production model and upload-learning version are unchanged by E16.
