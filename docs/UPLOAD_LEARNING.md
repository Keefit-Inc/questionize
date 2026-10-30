# GMAT CR upload learning (E11)

The learner service and the local evaluator are separate. A sleeping/offline Mac delays research; it must not block normal Snap analysis.

## Upload path

1. A capture-only call separates the question, visible reference key and publisher/teacher explanation.
2. Two separate solving calls receive only question fields and their pinned memory context. Neither receives images, keys, reference explanations, learner choices or the other call's reasoning. Both calls may currently use the same Meta model: this is independent context, not independent model training.
3. A separate diagnosis call can use attributed reference material after solving. AI agreement stays estimated. Conflicting printed/entered keys are disputed. Only explicit curator source attestation produces a confirmed reference label; it does not certify every interpretation or capture character.
   Completion blanks and required emphasis must survive capture. Unresolved evidence cannot identify a correct option or diagnose a learner misconception. An explanation generated for another answer is withheld rather than relabeled. The service runtime and observed guard version are shown separately from the active solving-memory version.
4. The source and captured reference explanation are delivered to the owner's IndexedDB. New clients acknowledge a committed local save before the temporary server cache is removed. Raw photos are consumed once; no permanent research question/explanation table is created.
5. Server research records keep scrubbed abstract failure cards, source-confidence categories, model identifiers, normalized source-group fingerprints, agreement flags and applied memory hashes. Originals and reference answer corpora stay on user devices/local research files. Unverified and expert-reference-derived practice remains private.

## Local research

One failure/disagreement or three distinct observed source groups schedules a batch check. A no-failure batch is held without a paid proposal. Checks are coalesced; heavy inference is not run in a learner job. A scoped local-worker token can lease abstract batches and submit bounded candidates/proofs. It cannot access learners' original questions because those originals are not stored in the research service.

The worker uses its private, source-keyed corpus. It freezes validation membership before generating rules, excludes training/triggering source groups, and retains all detailed questions, keys, teacher context and inference outputs in private local artifacts. New aliases from another edition cannot move a validation group into training. Expert-reference-derived and experience-derived rules have separate fields; both are model-extracted hypotheses, not newly expert-authored truth. Rule payloads are encrypted in the service database and available only to authenticated curators or scoped workers; public views show counts and hashes.

Two fresh paired passes on at least twelve distinct validation items are required. No regression is allowed; the same gained item must improve in both passes. Reused pilot benchmarks and repeated passes do not prove population accuracy, human explanation quality or learner growth. A candidate may legitimately remain held because the baseline is already correct.

A passing candidate is selected atomically, verified using the running AI's shared solving function, and rolled back if service verification fails. New requests pin immutable versions. A later confirmed-source loss against the control version can restore the parent. Terminal experimental ledger entries are frozen; a later rollback is visible in cycle history without rewriting the earlier measured result.

## Operator setup

Keep every configuration, token and corpus file outside Git. The local JSON configuration has these fields:

```json
{
  "server": "https://questionize.org",
  "token_file": "PRIVATE_WORKER_TOKEN_FILE",
  "dataset": "PRIVATE_VERIFIED_DATASET_JSON",
  "artifacts": "PRIVATE_LOCAL_ARTIFACT_DIRECTORY",
  "validation_items": 24,
  "method_references": "PRIVATE_ATTRIBUTED_METHOD_UNITS_JSON"
}
```

`datasets` may replace `dataset` with a list of separately cleared local files. Missing splits are assigned deterministically by normalized source-group hash; all aliases of a held-out group are excluded from training. AI-estimated or unchecked labels are not eligible for validation.

`completion_validation` is a reserved validation split, never reassigned to training. A batch covers at least four available completion questions as well as subtype diversity. The optional method-reference file contains attributed, AI-authored abstract procedures with source hashes, explicit `ai_derived_from_open_reference` origin and `CC-BY-4.0` license. Relevant procedures can inform a candidate; reference documents are not GMAT gold labels. The frozen input hash includes this file. This does not automatically adopt the procedures or establish a measured benefit from them.

Register only a token digest through `questionize:worker_register` on the server. Use `questionize:memory_bootstrap` once, then run from `ai/`:

```sh
python -m questionize.local_research_worker --config PRIVATE_CONFIG --once
python -m questionize.local_research_worker --config PRIVATE_CONFIG
```

The desktop installation can use a per-user LaunchAgent with a private configuration path. Restart on configuration/credential changes. Source changes cause an idle worker to exit so the supervisor restarts it with matching code. The console at `/admin#uploads` shows heartbeat, queued work, budgets, source confidence, actual evaluation results and current memory. `/admin/cycles/ledger` and `python -m questionize.sync_cycles` connect completed E11 measurements to the existing scoreboard. A separate `research` queue keeps research scheduling/application checks apart from normal generation work.

Local storage is not offline inference: the worker still makes authorized Meta API calls. Storage controls do not themselves grant copyright or commercial-use permissions. Do not bulk-import website question banks merely because a logged-in account can view them. The source catalog and permission review remain private; originals never enter Git or the public console.
