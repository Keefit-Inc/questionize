# Scoreboard

Generated from `research/ledger.jsonl` by `python -m questionize.scoreboard`; do not edit by hand. Full evaluations and trials are separate. Each row shows only its capability's own metric; solving accuracy is not an explanation rating. Bars from research/README.md.

| Capability | Subject | Scope | Bar | Latest result | Run |
|---|---|---|---|---|---|
| C1.1 Capture: extract |  |  | items with every role right ≥ 98%; CER ≤ 1% scans, ≤ 2% photos | not measured yet |  |
| C1.2 Capture: reconstruct |  |  | solvability equivalence ≥ 95% on items with figures | not measured yet |  |
| C2 Understand the item |  |  | skill agreement ≥ 90%; trap tags ≥ 80%; difficulty ρ ≥ 0.4 | not measured yet |  |
| C3.1 Solve | CR | full | accuracy against the key ≥ 95% (CR) | solver 1.00 [0.9103, 1.00] (n=39) · legacy 0.9744 [0.8682, 0.9955] (n=39) · guarded 1.00 [0.9103, 1.00] (n=39) | E9 v2 · 20261030T200342Z-e9-45a237 · muse-spark-1.3 · provisional (see qualifications) |
| C3.1 Solve | CR | trial | accuracy against the key ≥ 95% (CR) | baseline 1.00 (n=16) · candidate 1.00 (n=16) | E11 v1 · memory-cycle-524e3c74907182cd · muse-spark-1.3 · provisional (see qualifications) |
| C3.1 Solve | CR | regression | accuracy against the key ≥ 95% (CR) | baseline 1.00 [0.9011, 1.00] (n=35) · candidate 1.00 [0.9011, 1.00] (n=35) | E8 v1 · cycle-b02877966acd06b9 · muse-spark-1.3 · provisional (see qualifications) |
| C3.2 Explain | CR | full | explanations rated correct ≥ 90% | not measured yet |  |
| C3.2 Explain | CR | trial | explanations rated correct ≥ 90% | not measured yet |  |
| C3.3 Explain at the learner's level |  |  | readability in band ≥ 90%; preferred to generic | not measured yet |  |
| C3.4 Validate candidate correctness | CR | full | reject constructed defects; report valid-control rejection and parent clustering separately | legacy 1.00 (n=26) · guarded 1.00 (n=26) | E10 v2 · 20261030T200529Z-e10-6dd8bb · muse-spark-1.3 · provisional (see qualifications) |
| C3.4 Validate candidate correctness | CR | trial | reject constructed defects; report valid-control rejection and parent clustering separately | legacy 1.00 (n=4) · guarded 1.00 (n=4) | E10 v2 · 20261030T200342Z-e10-fca10d · muse-spark-1.3 · provisional (see qualifications) |
| C4 Diagnose the learner |  |  | misconception top-3 ≥ 70%; next-miss AUC ≥ 0.65 | not measured yet |  |
| C5 Write practice |  |  | first-draft verification rate rising with memory; two-answer rate ≤ 2% | not measured yet |  |
| C6 Choose practice |  |  | success on recommended 60%–80%; gains over unrecommended | not measured yet |  |

## Data and method qualifications

These annotations qualify interpretation; the recorded results and runs are retained.

- **capture-emphasis-spans:** This dataset contains 11 usable structure items without explicit emphasis spans: 7 train and 4 test. C3 comparisons are provisional pending capture verification. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E1.md)
- **e1-v2-final-confidence:** E1 v2 B1 retains the initial Solver confidence after a Judge override. Its ECE is not validated as confidence in the final decision. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E1.md)
- **e1-v2-judge-task-direction:** E1 v2 routes the Argument Judge by subtype alone. EXCEPT tasks can receive an inappropriate ranking direction, and the Judge can override a correct Solver answer. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E1.md)
- **e10-v1-development:** Constructed mutations share eight parent items. Controls and capture limitations differ by protocol version. Not independent population defect samples or evidence of learner benefit. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E10.md)
- **e10-v2-development:** Constructed mutations share eight parent items. Controls and capture limitations differ by protocol version. Not independent population defect samples or evidence of learner benefit. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E10.md)
- **e11-private-local-pilot:** Fresh paired local pilot with source-keyed labels. Repeated passes are correlated; results do not establish untouched-holdout generalization, human explanation quality or learner growth. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/protocols/E11-upload-driven-memory.md)
- **e8-development-replay:** Recorded decision replay on a known development regression set. No new solver inference, untouched holdout or learner-growth measurement. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/protocols/E8-policy-evolution.md)
- **e9-v1-development:** Known development data; source repairs and fixture changes are versioned. No untouched holdout, human explanation ratings or 99.9% reliability certification. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E9.md)
- **e9-v2-development:** Known development data; source repairs and fixture changes are versioned. No untouched holdout, human explanation ratings or 99.9% reliability certification. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E9.md)
