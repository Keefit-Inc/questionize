# E13: Real-photo evidence handling before a learner pilot (v1)

Registered 2026-10-30 after E12 identified two remaining Solver failures, before these photo calls. Development engineering checks, deliberately selected hard cases, not a random capture or accuracy sample.

Three local photo scenarios from two source-reviewed parents: a completion question alone, that same page with its printed expert reference, and a boldface role question alone. Render/crop from the private scan before inference. Keep image bytes, source questions, references and per-case output local; use the same Meta capture → independent blind solvers → analyst code as the upload service. No learner-account or Bank import.

Inspect text/choice coverage and emphasis against the local source record. Reference key/explanation must be absent from blind Solver inputs. Record each scenario's source status, source-key match, selected-answer presence and whether an unconfirmed answer was used to grade/diagnose a learner. AI agreement must remain `ai_estimated`; conflicting reference evidence must withhold a definitive verdict. Explanation/key inconsistency must withhold the explanation, never silently relabel it.

Maximum twelve logical model calls, no retries, three scenarios sequential. Preserve all failures. This does not establish whole-population OCR error, explanation correctness, or end-to-end learner benefit. Source-label matches are separate from the evidence-handling contract.
