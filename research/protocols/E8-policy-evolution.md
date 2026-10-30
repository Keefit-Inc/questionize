# E8: GMAT CR policy evolution through recorded decision replay (v1)

- **Capability:** C3.1, the policy that decides whether the Argument Judge may replace a solver answer.
- **Scope:** `CR` / `gmat`; `evaluation_scope=regression`; engineering regression evidence.
- **Registered:** 2026-10-29, before E8 candidate generation and evaluation. The E1 outcomes and failure audit were already known.
- **Question:** Can a bounded model-proposed policy pass an explicit regression gate, become the active service version, and leave a reproducible record of the proposal, comparison, decision and service application?
- **Hypothesis:** A policy that abstains from an unsupported EXCEPT ranking objective can prevent an audited incorrect override without changing standard-task decisions on the fixed replay set.

## What this experiment does and does not measure

This is a development regression test informed by the [E1 audit](../results/E1.md). It reuses recorded solver and Judge outputs. It is not an untouched holdout, a new blind model-solving run, evidence of statistically significant generalization, a validation of all C3 behavior, an E2 generation experiment, or a measurement of learner growth. Adoption means that this narrow service guard passed the registered engineering contract; it does not promote a general knowledge claim to canonical status.

The model weights remain fixed. The learned object is a versioned, bounded service policy. Candidate generation, replay evaluation, acceptance and service application are separate stages.

## Fixed evidence and benchmark

The initial private replay pack is built from `official-cr-v1` and E1 baseline run `20261029T191708Z-83575b`. Exclude every flagged item and the entire structure/boldface subtype, whose required emphasis spans were not preserved. Use the remaining **35 test items**, without selecting cases by whether the proposed change succeeds.

The pack contains only hashed case identifiers, subtype, a task operator (`standard` or literal `EXCEPT`), recorded solver and Judge answer letters, recorded Judge ranking stability, the official key letter, and the recorded legacy final answer. It contains no question wording, options, explanations, images, bibliographic positions or private filesystem paths. The private parent dataset, source run, pack content hash, case count, exclusion rule and builder version identify its provenance.

Before import, verify unique case identifiers, the expected count, valid labels and numerical fields, and that the **legacy decision rule** reproduces every recorded legacy final answer. This integrity check remains against the historical legacy rule even after another policy becomes active. The current service baseline is evaluated independently and need not reproduce the old legacy answer.

The benchmark is immutable for a cycle. An altered pack requires a new benchmark identity/hash and cannot silently replace an evaluation already in progress. The initial 35-item pack is a minimum-size requirement for this registered demonstration; smaller packs are tests or trials and cannot pass this adoption gate.

## Candidate and controls

- **Baseline:** the active policy version pinned when the cycle starts, with its immutable identifier and content hash.
- **Candidate:** a Meta `muse-spark-1.3` proposal from aggregate evidence and the current policy. The permitted payload is exactly `{"except_mode": "legacy"}` or `{"except_mode": "abstain"}`. The accompanying reason and hypothesis are explanatory metadata, not executable instructions.
- **Legacy:** use the recorded Judge decision when the existing subtype and stability rules allow an override.
- **Abstain:** for supported GMAT CR tasks whose question operator is literal EXCEPT, do not use the incompatible Judge ranking to replace the solver answer. Standard tasks keep the existing decision rule.

The proposer receives no private question text, held-back answer set or arbitrary code-execution capability. An unsupported payload fails validation. The service guard is scoped to CR at the GMAT level; this experiment makes no claim about other negative operators, other tests or other subjects.

Both versions replay the **same cases and recorded model outputs** through the same policy interpreter. There are no new solver or Judge model calls during evaluation. Record the candidate generator model, prompt/code version, generation call count and duration separately from the zero model-call replay evaluation.

## Lifecycle and triggers

A cycle records queued, candidate-generation, evaluation, decision and service-verification events with timestamps. Terminal outcomes include adopted, held and failed; failures and losing candidates remain visible.

An operator may explicitly start the initial research cycle. Automatic usage-triggered batches use separately recorded readiness rules: at least three new trusted, independent keyed source observations or twenty new rated CR/GMAT attempts, a 24-hour cooldown, at most one active cycle per scope, and a configured daily proposal limit. Freeze the actual trigger settings in the cycle record. A user miss is a learner response, not proof that the solver, question or key is wrong. Unknown or disputed keys do not qualify as trusted source observations.

The initial research replay is labeled as such; it must not be presented as a batch learned from a large live user population. No cycle creates, imports or modifies a learner's Snap entry or a public Bank question.

## Metrics and acceptance gate

Report baseline and candidate n, correct count, accuracy and Wilson 95% interval; paired gained/lost counts and accuracy difference; paired bootstrap interval and McNemar p; EXCEPT gains; changed standard-task decisions; missing results; and generation/evaluation resource measurements available from the implementation.

Adopt only when all registered checks pass:

1. Scope, payload, benchmark identity/hash, unique cases and complete paired results are valid, with at least the registered 35 cases.
2. At least one recorded case changes from incorrect to correct, with a strictly positive net accuracy difference.
3. No case changes from correct to incorrect.
4. Every standard-task final answer is unchanged, including answers that were already wrong. A zero count of correctness regressions alone is insufficient.
5. At least one EXCEPT case improves, and no unsupported policy change or unmeasured prompt change is included in the release.
6. The actual AI service can execute the candidate policy with the expected identifier, hash and decision trace.
7. The active release still equals the cycle's pinned baseline when adoption is committed.

An unchanged or non-improving candidate is held even when its absolute accuracy is high. Invalid evidence, incomplete evaluation or service failure cannot be called an improvement. Statistical tests describe this fixed development sample; this gate does **not** require or imply a statistically significant population improvement.

## Service application and rollback

Use the same bounded policy interpreter in evaluation and production verification. An accepted version must be selected by Rails for real generation/practice requests, pinned to the request/run, and passed to the stateless AI service. Changing a registry row without using it in the service does not complete the cycle.

Switch the active release atomically with an expected-baseline check. Concurrent or stale candidates are held rather than overwriting another accepted version. Verify the active service identifier/hash and the recorded probe outcome after the switch. If application verification fails, retain or restore the previous release with a compare-and-swap check, record the failure and rollback, and do not leave the failed candidate reported as active.

## Recording and public projection

PostgreSQL retains policy versions, the frozen benchmark, cycle metadata, aggregate comparisons, decisions and event history. Private case evidence remains access-controlled. Public console data and the append-only research ledger expose only whitelisted aggregate evidence and version/hash metadata.

Export runs as `protocol=E8`, `protocol_version=1`, `evaluation_scope=regression`, capability `C3.1`, with an explicit recorded-decision-replay qualification. Keep this scope separate from E1 full evaluations and trials in the scoreboard and capability history. Publish adopted, held and failed outcomes without rewriting the earlier E1 record. A research report must say which stages were actually executed and whether the live service version was verified.

## Stopping rule and next evidence

One bounded proposal and one paired replay per cycle; no retry-until-win search. The initial demonstration permits at most two explicitly requested proposal cycles so both a first decision and a subsequent no-improvement decision can be observed. Transport/model failures consume the attempt budget and preserve the current service version. Automatic daily limits are independent of this explicit demonstration budget.

Before extending the policy or making a broader quality claim, verify the affected source formatting, define additional task operators and independent contract cases, register a new protocol version, and collect a separate benchmark not used to design the fix. C3.2 explanation quality, C5 generated-question quality and learner growth require their own measurements.
