# E2 v2: Does an explicit CR design procedure improve first drafts?

Registered 2026-10-30 before generation. Capability C5. This replaces neither the unexecuted v1 memory-size experiment nor human evaluation. It tests a smaller deployable procedure scaffold first.

## Inputs and conditions

Twenty matched generation tasks: five subtypes (strengthen, weaken, assumption, inference, explain), four original topic briefs each. Both conditions receive exactly the same abstract objective, trap, difficulty and topic, with no OG question, reference explanation or answer key. Freeze task definitions before inference.

Baseline: current pattern-writer system and user prompt. Candidate: same prompt plus subtype-specific design procedures informed by the original 2017 *Fundamental Methods of Logic* (Matthew Knachel, CC BY 4.0). Procedures are our abstract adaptation, not copied examples or an empirical claim about that textbook. Equal model and one drafting call per condition, same temperature. Alternate order per pair; no revision or cherry picking.

## Evaluation

Every first draft goes through the existing blind Solver and Critic, with zero revisions and the current integrity guard. Applicable Argument Judge uses the same model/budget in both conditions. Primary: first-draft verification pass rate, with paired gained/lost counts and Wilson intervals. Secondary: solver agreement, critic key/ambiguity/explanation rejection, calls and time, copied-source checks. Judge stability is an AI proxy, not a calibrated probability of correctness.

Export a blinded, randomized pairwise rating sheet locally. Human quality, objective adherence, difficulty and learner benefit remain unmeasured until rated. Same-model evaluation cannot establish superiority to experts.

## Stopping and adoption

First run two matched smoke pairs, included in the registered twenty. If the runner fails, retain failed cases and stop for repair; report version changes. Maximum forty drafts, no paid retries, two tasks concurrent, per-call timeout. Candidate may replace the production drafting procedure only if all twenty pairs complete, first-draft passes increase, no baseline-passing pair regresses, and no deterministic integrity/source-copy violation is introduced. Otherwise retain the current production writer and record the held candidate. This is prompt/procedure optimization, not weight training or a measured benefit of OG-derived memory.
