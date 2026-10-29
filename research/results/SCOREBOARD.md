# Scoreboard

Generated from `research/ledger.jsonl` by `python -m questionize.scoreboard`; do not edit by hand. Full evaluations and trials are separate. Each row shows only its capability's own metric; solving accuracy is not an explanation rating. Bars from research/README.md.

| Capability | Subject | Scope | Bar | Latest result | Run |
|---|---|---|---|---|---|
| C1.1 Capture: extract |  |  | items with every role right ≥ 98%; CER ≤ 1% scans, ≤ 2% photos | not measured yet |  |
| C1.2 Capture: reconstruct |  |  | solvability equivalence ≥ 95% on items with figures | not measured yet |  |
| C2 Understand the item |  |  | skill agreement ≥ 90%; trap tags ≥ 80%; difficulty ρ ≥ 0.4 | not measured yet |  |
| C3.1 Solve | CR | full | accuracy against the key ≥ 95% (CR) | B0+M 0.9487 [0.8311, 0.9858] (n=39) · B1+M 0.9487 [0.8311, 0.9858] (n=39) | E1 v2 · 20261029T230630Z-a335be · muse-spark-1.3, muse-spark-1.3 · provisional (see qualifications) |
| C3.1 Solve | CR | trial | accuracy against the key ≥ 95% (CR) | B0+M 1.00 [0.5655, 1.00] (n=5) · B1+M 1.00 [0.5655, 1.00] (n=5) | E1 v2 · 20261029T200138Z-60ec5a · muse-spark-1.3, muse-spark-1.3 · provisional (see qualifications) |
| C3.2 Explain | CR | full | explanations rated correct ≥ 90% | not measured yet |  |
| C3.2 Explain | CR | trial | explanations rated correct ≥ 90% | not measured yet |  |
| C3.3 Explain at the learner's level |  |  | readability in band ≥ 90%; preferred to generic | not measured yet |  |
| C4 Diagnose the learner |  |  | misconception top-3 ≥ 70%; next-miss AUC ≥ 0.65 | not measured yet |  |
| C5 Write practice |  |  | first-draft verification rate rising with memory; two-answer rate ≤ 2% | not measured yet |  |
| C6 Choose practice |  |  | success on recommended 60%–80%; gains over unrecommended | not measured yet |  |

## Data and method qualifications

These annotations qualify interpretation; the recorded results and runs are retained.

- **capture-emphasis-spans:** This dataset contains 11 usable structure items without explicit emphasis spans: 7 train and 4 test. C3 comparisons are provisional pending capture verification. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E1.md)
- **e1-v2-final-confidence:** E1 v2 B1 retains the initial Solver confidence after a Judge override. Its ECE is not validated as confidence in the final decision. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E1.md)
- **e1-v2-judge-task-direction:** E1 v2 routes the Argument Judge by subtype alone. EXCEPT tasks can receive an inappropriate ranking direction, and the Judge can override a correct Solver answer. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E1.md)
