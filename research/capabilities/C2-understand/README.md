# C2 Understand the item

**Tasks.** Name the subject and skill (sub-type), the objective the item assesses (the competency in KNOWLEDGE_MODEL §3.2), its difficulty on our scale, and for each option the trap it sets.

**Measures and bars.** Skill agreement with the book's own type label (≥ 90%); trap tags judged correct against the book's per-option explanation (≥ 80%); difficulty: Spearman correlation with observed correct rates once items have answers (≥ 0.4), and with the book's difficulty ordering before that.

**Where the field is.** Predicting difficulty from item text is still weak: in the BEA 2024 shared task on medical exam items, most systems barely beat a predict-the-mean baseline. Language models tag skills and knowledge components reasonably well. Distractors carry the misconception they target, which is why traps are tagged per option.

**Experiments.** E5 (planned), E3 H2c (see [`../../protocols/`](../../protocols/)).

**Improvement history.** [`HISTORY.md`](HISTORY.md), generated from the ledger: every run that measured this capability, what changed, and the result against the bar.
