# E14 post-run diagnosis — routing, verification and reference quality

This is a diagnostic annotation of `20261031T030145Z-e14-b5b672`, not another experiment. No model calls, key changes, question exclusions, candidate edits or outcome reruns were made for this review. The [primary result](E14.md) remains 148/155, 147/155 and 144/155.

## Memory applicability was incomplete

The frozen stem router retrieved a procedure for 103/155 items. It returned unknown for 52/155, including valid task paraphrases and source-native completion formats. The router is a limitation of this research implementation; this finding is not evidence of the production upload classifier's accuracy.

| Predefined routing subset | n | A correct | M correct | MV correct |
|---|---:|---:|---:|---:|
| Procedure retrieved | 103 | 98 | 98 | 96 |
| No procedure retrieved | 52 | 50 | 49 | 48 |

Where the procedure was actually supplied, memory alone had zero net accuracy gain. On the 52 unrouted items A and M had identical request construction; their answers differed on three items. The one-item aggregate M deficit is in this identical-input subset and must not be attributed to a causal harmful memory effect. This is a descriptive subset analysis, not a new selected primary endpoint or proof of no population benefit.

The next routing candidate should handle the task operator and completion format, preserve an explicit uncertain fallback, and account for any classification-call cost. It needs a fresh confirmation set; fixing the router and rescoring these exposed 155 items would be development evidence.

## Verification caused observed losses and operational failures

Within MV, the verifier rescued no wrong first answer and changed two source-key-matching first answers to nonmatching answers. Seven completed cases remained wrong in both stages. Two further verifier calls used their output-token limits without completing a structured answer. Their billed output included hidden reasoning; they remained failures in the 155-item denominator.

The two-call workflow and its first/second budget allocation are part of the tested system. A correct first answer being overturned is a direct selection failure against the fixed reference. Exhausted output budget is an execution/planning failure. Neither observation establishes that base-model weight training is required.

Broad, unconditional same-model rechecking has no demonstrated benefit here. A future verifier should be tested for both rescue and harm, require a concrete text-supported reason to override, and handle an unfinished check without losing a completed initial answer. These are proposed changes, not changes silently applied to this run or the service.

## Reference confidence remains separate

An agent-assisted, reference-informed inspection of four selected cases flagged three for independent expert review: one terminology inconsistency and two scope/answer-ranking concerns. These are review requests, not adjudicated source errors or a defect-rate estimate. The selected cases came from the 13-case union of condition failures, not a random audit of the corpus. All original keys, scores and case membership remain unchanged.

One source-key-matching answer overturned by the verifier is among the terminology-review flags. Therefore even the source-based harm count must not be presented as two independently human-certified semantic errors. The other inspected override introduces an unsupported inference despite an available source rationale. Originals and per-case reasoning remain in the operator's private local review artifact, separate from this public annotation.

Solving limitations are still present against the fixed source references, but the current evidence does not cleanly isolate an intrinsic model-capacity ceiling from routing, procedure, budget allocation, stochastic inference and reference quality. Prioritise reliable source adjudication, task routing and verifier harm controls before inferring a need for fine-tuning from this study.
