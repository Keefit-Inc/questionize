# E9: repaired OG inputs, solver and verifier separation (v1)

Registered 2026-10-30 before new inference. Capabilities: C1 input audit and C3.1 solving. This is a development evaluation: the original E1 outcomes informed the repairs. It is not a new untouched holdout or a 99.9% reliability certification.

## Dataset and capture audit

Keep official-cr-v1 immutable. Create official-cr-v2 with a private, hashed correction manifest, original PDF hash and per-field evidence. Inspect every boldface-dependent item against the scan, restore exact target spans, and distinguish argument-strategy items that require no spans. Restore missing printed identifiers only after source inspection. Retain flagged captures until reviewed; never silently admit them or alter existing train/test membership. Report mechanical validation separately from visual inspection; OCR agreement alone does not establish source fidelity. Official wording, explanations, screenshots and corrections remain outside Git.

## Conditions

Use the same repaired test membership as E1 (39 items), no memory and no reference explanation in inference. First run a three-item smoke test, then the complete test. Run a blind Solver once per item. Independently sample the existing Argument Judge for its supported subtypes. Derive both the original subtype-only override and the deployed EXCEPT abstention policy from the same samples. The Judge never sees the official key or Solver answer. Explain the final decision separately; model-generated explanations are not expert-adjudicated correctness labels.

## Measures and stopping

Report Solver accuracy, Judge top-option accuracy on its applicable subset, unchanged/corrected/corrupted decisions, final policy accuracy, applicability/coverage, calls and elapsed time. Use Wilson intervals for binary accuracy. Do not substitute a subset accuracy for the full-test result or an agreement score for a probability of truth. Record errors and missing calls; failures count in completeness and cannot silently vanish. One registered complete pass after the smoke test; no best-of-run selection. No automatic adoption of a new reasoning method from these outcomes.

## Evidence lineage

Book keys and explanations are private expert-reference evidence. AI reflections are derived artifacts with their own model, input hash and namespace; they never become expert-authored explanations. All public exports contain aggregates and code/protocol links only.
