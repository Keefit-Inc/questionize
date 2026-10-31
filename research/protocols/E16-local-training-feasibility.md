# E16 supplement — Original logic curriculum and local training feasibility

Registered before curriculum inference or training. This is a narrow training
feasibility experiment, distinct from the OG Solver pilot. It cannot establish
general CR accuracy, explanation teaching quality or student diagnosis.

Generate original propositional microtasks from four training structures: two-hop
implication, one-step contraposition, disjunctive syllogism and a conjunctive rule.
Use 32 named/order/option variants per structure (128 instances, only four
structures). Verify a unique correct option and satisfiable premises by exhaustive
Boolean enumeration, plus independently implemented rule derivation. Offline
tests recompute truth values with a second interpreter. No book wording or
explanations, AI teacher, paid service or learner record is used.

Development uses three different structures: three-hop implication, two-hop
contraposition and a disjunction followed by implication; eight variants each.
Confirmation reserves fork/join reasoning and three-hop contraposition, eight
variants each. These small, related generated structures are not an independent
natural-language GMAT benchmark. Report instance counts and structure counts.

Evaluate the pinned local 1B base on development. Then perform one fixed training
feasibility attempt: 80 iterations, batch two, four adapted layers, learning rate
1e-4, prompt masking, maximum sequence length 768, seed 41. No checkpoint search
on development accuracy. Save the final adapter. Compare that adapter on the same
development instances with the same base prompt, decoding and 256-token cap.
Measure format errors, task accuracy, time and peak memory; training compatibility
and training loss do not establish generalization. No confirmation inference is
performed during this smoke test. Any later confirmation needs frozen candidate
settings and an explicit new record.

Training outputs and machine measurements stay local during feasibility. Model
and data licensing/attribution must be packaged before any adapter distribution.
Do not activate this adapter in the live app, expose private source questions,
or claim 100% general accuracy from this experiment.

## Format diagnosis before training — v2 clarification

The initial untrained development generation probe scored 0/24, with 16 missing
final labels, under the 256-token cap. No adapter has been trained at this point.
Retain these results, but do not use this weak output-format baseline to claim
logical learning. Before training, add a matched, format-neutral classifier:
one forward pass, restrict the first assistant token to the five literal answer
tokens, select the largest logit. Use the same classifier before/after training;
it cannot omit a label or spend extra generated reasoning tokens. This measures
one direct-answer configuration, not the best attainable reasoning accuracy.

Create a separate v2 curriculum directory with the same original structures and
membership, but label-only assistant targets and the matching answer-only system
prompt. Keep the fixed 80-step training configuration. This intentionally tests
answer learning; it does not train or measure explanation quality. Compare the
untrained choice classifier against the trained choice classifier on the 24
development instances. Also record this stronger format control on the 16
previously exposed OG items. Any general CR transfer requires its own comparison.
