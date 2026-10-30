# E12: Restored completion questions and upload readiness (v1)

Registered 2026-10-30 before model evaluation. Capabilities: C1.1 (source audit), C3.1 (blind solving), C3.4 (format guard). This is development evaluation, not an independent population accuracy estimate.

## Problem and data

All fifteen `not_as_printed` items excluded from the 109 eligible OG records are passage/argument completion questions. The previous 39-item test therefore omits an entire format. Inspect their scans and restore explicit blanks without changing their printed answers. Preserve the parent dataset and the old 70/39 split; assign the fifteen a separate `completion_validation` split before inference. Keep originals, keys, explanations and per-item results local. Agent inspection is not independent human certification.

## Conditions and measures

1. Audit all fifteen restoration patches against source scans and existing dual OCR. Report coverage, patch scope and remaining defects; this is not a CER estimate.
2. Run the current service blind Solver, without reference key or explanation, twice on the fifteen restored items and once on the existing 39 test items. Fixed Meta model, temperature zero, no retries; report accuracy, uncertainty, per-format counts and repeat disagreement separately. Do not pool repeated answers into independent-item sample size.
3. Exercise a deterministic completion-format guard on the fifteen normal records and fifteen copies with the blank removed, plus the 109 previous normal records. Missing blank is a transcription defect; a sentence ending in `since` is not itself evidence of corruption when an explicit blank exists. Report valid acceptance and defect blocking separately.

## Stopping and interpretation

Three-item smoke, then the registered remainder if operational. Maximum 69 solve calls (including smoke observations reused in the first pass), two concurrent calls, 90-second timeout. Errors remain in the denominator; no selective reruns or source/key edits after seeing answers. No memory is fitted on validation answers. A format guard may ship only if it blocks all fifteen removed-blank mutations and accepts all 124 normal records. Semantic success does not prove 99.9% reliability, explanation quality or learner benefit.

## Explanation contract

Test offline that unresolved evidence cannot expose a definitive correct option, learner error or misconception; a generated explanation for a different answer must be withheld rather than relabeled. These are engineering contracts, not expert correctness ratings for C3.2. Record live explanatory quality separately when rated.
