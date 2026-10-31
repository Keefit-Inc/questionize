# Scoreboard

Generated from `research/ledger.jsonl` by `python -m questionize.scoreboard`; do not edit by hand. Full evaluations and trials are separate. Each row shows only its capability's own metric; solving accuracy is not an explanation rating. Bars from research/README.md.

| Capability | Subject | Scope | Bar | Latest result | Run |
|---|---|---|---|---|---|
| C1.1 Capture: extract |  |  | items with every role right ≥ 98%; CER ≤ 1% scans, ≤ 2% photos | not measured yet |  |
| C1.2 Capture: reconstruct |  |  | solvability equivalence ≥ 95% on items with figures | not measured yet |  |
| C2 Understand the item |  |  | skill agreement ≥ 90%; trap tags ≥ 80%; difficulty ρ ≥ 0.4 | not measured yet |  |
| C3.1 Solve | CR | full | accuracy against the key ≥ 95% (CR) | A 0.9548 [0.9097, 0.9780] (n=155) · M 0.9484 [0.9015, 0.9736] (n=155) · MV 0.9290 [0.8774, 0.9599] (n=155) | E14 v1 · 20261031T030145Z-e14-b5b672 · muse-spark-1.3 · provisional (see qualifications) |
| C3.1 Solve | CR | trial | accuracy against the key ≥ 95% (CR) | base 0.3125 (n=16) · procedure 0.1875 (n=16) · choice 0.00 (n=16) · choice-adapter 0.3125 (n=16) | E16 v1 · 20261031-e16-og-development · Llama-3.2-1B-Instruct MLX 4bit |
| C3.1 Solve | CR | regression | accuracy against the key ≥ 95% (CR) | baseline 1.00 [0.9011, 1.00] (n=35) · candidate 1.00 [0.9011, 1.00] (n=35) | E8 v1 · cycle-b02877966acd06b9 · muse-spark-1.3 · provisional (see qualifications) |
| C3.1 Solve | CR-formal-logic | trial | accuracy against the key ≥ 95% (CR) | choice 0.0833 (n=24) · choice-adapter 0.1667 (n=24) | E16 v1 · 20261031-e16-logic-development · Llama-3.2-1B-Instruct MLX 4bit |
| C3.2 Explain | CR | full | explanations rated correct ≥ 90% | not measured yet |  |
| C3.2 Explain | CR | trial | explanations rated correct ≥ 90% | not measured yet |  |
| C3.3 Explain at the learner's level |  |  | readability in band ≥ 90%; preferred to generic | not measured yet |  |
| C3.4 Validate candidate correctness | CR | full | reject constructed defects; report valid-control rejection and parent clustering separately | legacy 1.00 (n=26) · guarded 1.00 (n=26) | E10 v2 · 20261030T200529Z-e10-6dd8bb · muse-spark-1.3 · provisional (see qualifications) |
| C3.4 Validate candidate correctness | CR | trial | reject constructed defects; report valid-control rejection and parent clustering separately | legacy 1.00 (n=4) · guarded 1.00 (n=4) | E10 v2 · 20261030T200342Z-e10-fca10d · muse-spark-1.3 · provisional (see qualifications) |
| C4 Diagnose the learner |  |  | misconception top-3 ≥ 70%; next-miss AUC ≥ 0.65 | not measured yet |  |
| C5 Write practice | CR | trial | first-draft verification rate rising with memory; two-answer rate ≤ 2% | baseline 0.90 [0.6990, 0.9721] (n=20) · candidate 0.90 [0.6990, 0.9721] (n=20) | E2 v2 · 20261030T225620Z-e2-2994f9 · muse-spark-1.3 · provisional (see qualifications) |
| C6 Choose practice |  |  | success on recommended 60%–80%; gains over unrecommended | not measured yet |  |

## Data and method qualifications

These annotations qualify interpretation; the recorded results and runs are retained.

- **capture-emphasis-spans:** This dataset contains 11 usable structure items without explicit emphasis spans: 7 train and 4 test. C3 comparisons are provisional pending capture verification. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E1.md)
- **e1-v2-final-confidence:** E1 v2 B1 retains the initial Solver confidence after a Judge override. Its ECE is not validated as confidence in the final decision. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E1.md)
- **e1-v2-judge-task-direction:** E1 v2 routes the Argument Judge by subtype alone. EXCEPT tasks can receive an inappropriate ranking direction, and the Judge can override a correct Solver answer. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E1.md)
- **e10-v1-development:** Constructed mutations share eight parent items. Controls and capture limitations differ by protocol version. Not independent population defect samples or evidence of learner benefit. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E10.md)
- **e10-v2-development:** Constructed mutations share eight parent items. Controls and capture limitations differ by protocol version. Not independent population defect samples or evidence of learner benefit. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E10.md)
- **e11-private-local-pilot:** Fresh paired local pilot with source-keyed labels. Repeated passes are correlated; results do not establish untouched-holdout generalization, human explanation quality or learner growth. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/protocols/E11-upload-driven-memory.md)
- **e12-format-development:** Restored-format development cohorts. Fifteen completion questions observed twice are not thirty independent items. Input guard contracts do not prove whole-source fidelity or semantic reliability. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E12.md)
- **e14-post-run-routing-and-source-review:** Post-run diagnosis: procedures were retrieved for 103/155 items; A and M both scored 98/103 there. On 52 unrouted items the inputs were identical. Targeted agent-assisted review flagged three source cases for independent expert adjudication; these are not confirmed source errors. Original scores and keys remain unchanged. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E14-diagnostics.md)
- **e14-source-reference-budget-scope:** Source-key agreement on a frozen newly acquired source set; possible model pretraining exposure and no independent human adjudication. Equal uncached token-price ceilings do not imply identical actual spending. The same-model verifier is correlated with its Solver. No production adoption, human explanation or learner-benefit claim. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E14.md)
- **e2-v2-proxy:** Twenty matched original generation tasks. First-draft verification by same-model agents is an AI proxy, not human item quality or learner benefit; v1 memory-size study remains unexecuted. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E2.md)
- **e8-development-replay:** Recorded decision replay on a known development regression set. No new solver inference, untouched holdout or learner-growth measurement. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/protocols/E8-policy-evolution.md)
- **e9-v1-development:** Known development data; source repairs and fixture changes are versioned. No untouched holdout, human explanation ratings or 99.9% reliability certification. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E9.md)
- **e9-v2-development:** Known development data; source repairs and fixture changes are versioned. No untouched holdout, human explanation ratings or 99.9% reliability certification. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E9.md)
