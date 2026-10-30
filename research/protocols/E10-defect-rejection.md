# E10: defect rejection contracts (v1)

Registered 2026-10-30 before new inference. Capability C3.4: validate candidate correctness. This is a constructed development stress test, not a population defect-rate estimate or validation of educational usefulness.

## Cases

Deterministically select the first two repaired test items of each of strengthen, weaken and assumption, plus the first two boldface-dependent test items (up to eight independent parent items). Preserve parent IDs privately and hash them publicly. For each parent, include the valid control, a deliberately wrong proposed key, an exact duplicate of the keyed option under another letter, and an explanation explicitly contradicting the proposed key. For boldface parents also remove the required span annotations. Correctness of these mutations follows their construction and the reference key, not AI voting. The valid controls have reference keys, but their explanation templates are minimal and not pedagogical-quality gold.

## Conditions

Compare the current blind-Solver/Critic gate with the same gate preceded by deterministic integrity checks. No revisions: evaluate rejection of the original draft, not the ability to repair it. Share model outputs between conditions whenever the guarded path does not short-circuit. Use the production verification implementation with the Argument Judge disabled to isolate the Solver/Critic gate; E9 evaluates that Judge separately. Record the exact configuration. Run five smoke cases before one complete pass. Bound concurrency and retries.

## Measures and stopping

Report defect rejection and false acceptance by defect type, valid-control acceptance, affected parent count, logical model calls, failures and elapsed time. Distinguish deterministic rejection from semantic/model rejection. Report both counts and denominators; related mutations are clustered by parent and are not independent samples. Do not claim 99.9% from this small, deliberately constructed suite. Model rejection of a valid control is a false rejection, even if the model disagrees with the book. Unexpected errors are failures, not successful rejections.

## Release rule

The integrity guard may ship only if offline tests pass, the complete live-model suite has no guarded false accepts, and it does not introduce a new valid-control rejection. Any semantic gate failure remains visible and blocks a broader automatic-publication claim. These contracts cannot certify subtle ambiguity, all misleading explanations, learner benefit or all GMAT subtypes. Private per-case material and expert explanations are never included in Git or the public console.
