# E14 v1 — Source-disjoint GMAT CR memory and verification under equal budgets

Registered 2026-10-30 before new inference. Scope: C3.1 blind source-key agreement; diagnostic verifier rescue/harm. No human explanation or question-generation claim.

## Membership and blinding

Build the private manifest before any teacher/proposal or evaluation calls. Preserve original OG v4 train membership (70) and previously exposed development membership (39 + 15). Detect exact aliases and shared/near-identical stimuli across all 279 explanation-backed records. Remove training records that overlap development; quarantine new evaluation records overlapping any OG source. Link within-test stimulus groups. New 155 explanation-backed source records supply final evaluation, subject to these pre-inference checks. Source-native completion blanks and boldface spans remain intact. Report every exclusion. The key-only user compilation is excluded.

Training calls receive only the training source questions, keys and attributed reference explanations. Learn one structured procedure artifact for each training subtype, recording applicability, steps, counterexample tests and common traps. No evaluation questions, labels, explanations or outcomes enter those calls. Freeze candidate artifacts and hashes before the final test. Development smoke uses at most three preselected exposed items; repairs must be recorded before final evaluation. Public artifacts contain only aggregates, technical hashes and limitations.

## Budget conditions

Pin Standard `muse-spark-1.3`, Responses API, `reasoning.effort=medium`, `store=false`, no tools, no generation retries, at most three concurrent items. This is a controlled research configuration, not the production default-effort configuration.

Each condition gets the same **$0.03 per-item uncached token-price ceiling**. A uses the existing production Solver instruction without learned memory, one call. M adds the frozen, stem-routed training-derived procedure, one call. MV uses the same memory with a first Solver allocated half the envelope; a separate verifier sees the problem and proposed public answer/rationale (never the source key/reference), and receives the remaining envelope after actual first-call normalised spend. Its final answer is the MV answer. The verifier is a separate call to the same model, not an independently trained judge. No extra answer calls after scoring.

Preflight count the fully rendered request with Meta's token-count endpoint, reserve input at full input price, then bound output (including hidden reasoning) by the remaining allowance. Preflight context is a conservative reservation, not billing usage. Compute actual normalised cost from response usage at $1.25/M input and $4.25/M output; separately estimate billed token cost with $0.15/M cached input. Cache discounts do not increase an arm's envelope. Missing usage or envelope violation invalidates the cost comparison; report it rather than treating it as zero. Fixed budgets need not produce identical expenditure. Record actual spending, tokens, latency, errors and incomplete outputs. Caps are identical; actual equality is not claimed.

Reference rates reviewed 2026-10-30: https://dev.meta.ai/docs/pricing-rate-limits . Token count semantics: https://dev.meta.ai/docs/token-counting . Reasoning: https://dev.meta.ai/docs/reasoning . These are token-price estimates, not account invoices. Teacher construction cost is recorded separately, with at most eight calls of $0.25 each and at most 4096 output tokens per call; report inference plus construction cost as well as inference alone. The whole generation envelope is at most $2 + 3×3×$0.03 development + 155×3×$0.03 final = $16.22; provider failures may have unreported billing, which makes cost accounting incomplete.

## Scoring and bottlenecks

All registered final items remain in the intention-to-evaluate denominator; no reruns or post-result exclusions. Report A/M/MV correct/n, Wilson intervals, errors, priced token totals and latency; paired gains/losses and paired bootstrap uncertainty. Preserve shared-stimulus groups for clustered comparisons. Also report task-operator/type slices defined from the source stem before seeing results; source tags remain secondary metadata.

For MV, compare its first answer and verifier answer against the hidden reference afterwards: wrong→right rescue, right→wrong harm, both wrong, both right. Count cases where either proposed answer is correct but final selection is wrong; this is a diagnostic opportunity, not a deployable oracle accuracy. Neither candidate correct indicates a proposal/reasoning limitation under this configuration, not proof of a model's fundamental ceiling. An independent source error remains possible. Output truncation, budget and schema failures are operational bottlenecks, not semantic failures.

## Decision and interpretation

The final test is used once for this frozen candidate. Positive observed net gain without cost violations is a candidate for a separately registered confirmation; automatic production adoption is not part of this study. No gain or any unresolved cost-accounting failure means hold. Do not tune on final test failures and report the same set as fresh evidence. Compare with strongest models or humans only in a later explicit study. Publisher/source-key agreement, possible pretraining exposure, source-quality differences, small subgroups, correlated model errors and the limited source population qualify every result. This experiment does not certify 99.9%, novel-item generalization, explanation quality or learner benefit.
