# E2: Does a memory of question designs improve generated questions? (v1)

- **Research question:** RQ1
- **Hypotheses:** H1b: as the number of learned items n grows (0, 25, 50, 100), items generated with the design memory pass verification on the first draft more often, with larger Argument Judge margins and better blind expert ratings. H1c (secondary): designs learned without answer keys help less than designs learned with them.
- **Registered:** 2026-10-29, before any results were seen

## Dataset
Designs consolidated from E1's items (with keys), split by learning order; a fixed set of 10 articles and 2 snapped-question designs used as generation inputs for every condition.

## Conditions
B1 with design memory off (n = 0) and on with memories built from n = 25, 50, 100 items (100 only if E1 reaches it). Same inputs, seeds and models in every condition.

## Metrics
- **Primary:** first-draft verification pass rate.
- **Secondary:** judge margin and first-rate; critic distractor quality; share of items with two defensible answers; blind pairwise expert preference (memory vs no memory).

## Analysis
Pass rate per condition with Wilson 95% CIs; trend across n (logistic regression on n); pairwise preference with a sign test.

## Human judgments
Pairs of items for the same input, one from each condition, shown side by side in random order; the rater picks the better item and flags any with a wrong key.

## Stopping rule and budget
20 generated items per condition.
