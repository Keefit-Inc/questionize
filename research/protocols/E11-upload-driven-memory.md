# E11: upload-driven, locally evaluated GMAT CR memory (v1)

Registered before implementation inference, 2026-10-30. New uploads provide blind-solving observations and abstract failure hypotheses. A private local worker proposes bounded reasoning rules and evaluates them against a disjoint, source-keyed local benchmark. Server storage contains no research question text, source answer-key corpus, expert explanations or uploaded images. Normal temporary request processing and device delivery remain distinct from research storage.

## Learner path

Capture question fields and visible reference material separately. Independent Solver calls receive question fields and their pinned memory only, never images, reference keys/explanations, learner choices or another Solver's output. With no reference key, agreement remains AI-estimated; disagreement is unresolved. A supplied or OCR-read key is attributed as supplied/extracted, not automatically expert-certified. Curator source attestation is separate. Store only scrubbed abstract failure cards, correctness/agreement flags, model identifiers and policy hashes in server research records. Originals stay on the learner's device and the operator's local research files.

## Candidate and evaluation

A dedicated worker polls scoped, authenticated leases. It receives abstract observations, not upload originals. It may use source-keyed local training examples while generating at most eight short rules, separately attributed to expert-reference extraction and usage-derived hypotheses. No executable code or question-specific answer rule is allowed. Actual rule payloads remain private; public console data includes counts/hashes only.

Freeze the local validation membership before candidate generation. Exclude training-source and triggering-upload fingerprints from validation. Require at least twelve distinct source-keyed validation items, two fresh paired baseline/candidate passes, no correctness regressions in either pass, and at least one identical gained item in both passes. AI-estimated labels cannot be validation gold. The local worker retains original questions, keys, explanations, prompts and individual outputs; it sends only opaque case hashes and paired correctness flags. Related repeated passes are not independent population samples.

## Release and operations

No-change, insufficient evidence, errors and losing candidates are held/failed with reasons; no fabricated improvement. A passing candidate is atomically selected and tested through the running AI's shared solving function on an original synthetic service contract. Failed application rolls back. Uploads pin immutable memory versions; a later confirmed reference regression against the control version can roll back the active candidate. Research jobs use a separate queue, bounded concurrency and daily budget; learner requests do not depend on a local worker being online. The console reports worker heartbeat, queued/held work, evidence status, evaluation provenance and active runtime versions.

This is a scoped engineering pilot, not proof of 99.9% accuracy, unseen generalization, human explanation quality or learner growth. Public data cannot include source wording or private rule payloads. Scripted integration tests and live Meta checks must be labeled separately.
