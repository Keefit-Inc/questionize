# E3: What a learner's missed questions reveal (pilot, v1)

- **Research question:** RQ2
- **Hypotheses:** H2a (profile predicts next misses), H2b (misconception agreement), H2c (difficulty correlation); H2d with simulated students only.
- **Registered:** 2026-10-29, before any results were seen

## Dataset
About 30 questions a learner actually missed (snapped), and 20 unseen items of the same tests answered afterwards; plus simulated students (LLM respondents with set weaknesses) for H2d.

## Conditions
- Weakness profile from the snapped misses (skills, traps, misconceptions) vs two baselines: overall accuracy, and overall rating.
- For H2b: our diagnosis vs a plain single-model diagnosis of the same photo.

## Metrics
- **H2a:** AUC for predicting misses on the 20 unseen items.
- **H2b:** top-1 / top-3 agreement with the expert's misconception label.
- **H2c:** Spearman correlation between diagnosed difficulty and observed correct rate (when available) or the book's difficulty marking.
- **H2d:** change in same-trap error rate for simulated students after same-trap practice vs random practice.

## Analysis
Bootstrap CIs; a pilot with one learner is reported as a feasibility result, not as evidence of effect.

## Stopping rule and budget
One pass.
