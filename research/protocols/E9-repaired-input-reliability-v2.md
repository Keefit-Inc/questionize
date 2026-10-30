# E9 v2: independent OCR reconciliation and separated solving

Registered 2026-10-30 after E9 v1 and E10 v1, before v2 inference. E9 v1 reached Solver 39/39 but its capture audit was incomplete; E10 v1 exposed a truncated source and placeholder rationales. Preserve those runs. This revision is development work informed by their outcomes, not independent confirmation.

Compare Apple Vision and Tesseract outputs for all source pages. Visually resolve detected stimulus omissions and the printed key not recovered by the second OCR. Keep original splits and the 15 previously held captures; do not admit them from model agreement. Store all source outputs privately and record hashes and the exact review scope. Cross-OCR agreement is not human certification.

Run the same 39 test items on official-cr-v3, with the same blind Solver and separately sampled Argument Judge as v1. Report the Solver, Judge applicable subset, legacy override and deployed EXCEPT-abstention results, including corrected/corrupted answers and missing cases. Skip new explanation generation: E9 v1 had 11 explanation timeouts and human explanation quality remains unmeasured. One full pass, no memory, no label shown to either Solver or Judge, bounded concurrency three, zero transport retries. This isolates the registered solving question and does not select better explanation outcomes.
