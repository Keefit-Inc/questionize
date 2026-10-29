# C3 improvement history

Generated from `research/ledger.jsonl` by `python -m questionize.scoreboard`; do not edit by hand. Trials remain visible and are not full evaluations. Each sub-capability uses its own metric; these observations do not automatically establish an improvement.

| Date | Subject | Scope | Run | Protocol | What changed | Models | Result |
|---|---|---|---|---|---|---|---|
| 2026-10-29 | CR | trial | 20261029T190207Z-4c0169 | E1 v2 | trial, 5 items | muse-spark-1.3, muse-spark-1.3 | C3.1: B0 1.00 [0.5655, 1.00] (n=5) · B1 1.00 [0.5655, 1.00] (n=5); C3.2: not measured yet; provisional (see qualifications) |
| 2026-10-29 | CR | full | 20261029T191708Z-83575b | E1 v2 | baseline, test split | muse-spark-1.3, muse-spark-1.3 | C3.1: B0 0.9487 [0.8311, 0.9858] (n=39) · B1 0.9487 [0.8311, 0.9858] (n=39); C3.2: not measured yet; provisional (see qualifications) |
| 2026-10-29 | CR | trial | 20261029T200138Z-60ec5a | E1 v2 | trial: memory from train split | muse-spark-1.3, muse-spark-1.3 | C3.1: B0+M 1.00 [0.5655, 1.00] (n=5) · B1+M 1.00 [0.5655, 1.00] (n=5); C3.2: not measured yet; provisional (see qualifications) |
| 2026-10-29 | CR | full | 20261029T230630Z-a335be | E1 v2 | memory from train split; full test evaluation | muse-spark-1.3, muse-spark-1.3 | C3.1: B0+M 0.9487 [0.8311, 0.9858] (n=39) · B1+M 0.9487 [0.8311, 0.9858] (n=39); C3.2: not measured yet; provisional (see qualifications) |

## Data and method qualifications

These annotations qualify interpretation; the recorded results and runs are retained.

- **capture-emphasis-spans:** This dataset contains 11 usable structure items without explicit emphasis spans: 7 train and 4 test. C3 comparisons are provisional pending capture verification. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E1.md)
- **e1-v2-final-confidence:** E1 v2 B1 retains the initial Solver confidence after a Judge override. Its ECE is not validated as confidence in the final decision. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E1.md)
- **e1-v2-judge-task-direction:** E1 v2 routes the Argument Judge by subtype alone. EXCEPT tasks can receive an inappropriate ranking direction, and the Judge can override a correct Solver answer. [Report](https://github.com/Keefit-Inc/questionize/blob/main/research/results/E1.md)
