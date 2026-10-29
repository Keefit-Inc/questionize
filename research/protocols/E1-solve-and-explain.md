# E1: Solving and explaining official-style items (v1)

- **Research question:** RQ1
- **Hypotheses:** H1a: B1 and B2 reach a higher solving accuracy against the answer key than B0, and their explanations are judged correct more often.
- **Registered:** 2026-10-29, before any results were seen

## Dataset
50–80 Critical Reasoning / Logical Reasoning items from published GMAT and LSAT practice books owned by the team, photographed one at a time, with the book's answer key entered as a letter. Private dataset id `official-cr-v1`. Items kept outside the repository.

## Conditions
- **B0:** Muse Spark 1.3 answers and explains in one call.
- **B1:** Our pipeline's solver, critic and Argument Judge decide the answer; the explanation is written after the decision.
- **B2:** Muse Spark 1.3 and Muse Spark Open answer independently, exchange reasoning for two rounds, and settle the answer and explanation; if no Baseten access, two differently-instructed runs of one model (reported as B2′).
Held fixed: transcription (from the same Snap reading), temperatures, seeds, prompts hash.

## Metrics
- **Primary:** accuracy against the key.
- **Secondary:** explanation correctness (blind human rating: correct / partly / wrong); calibration of stated confidence; cost per item.

## Analysis
Paired comparison per item; McNemar's test and a paired bootstrap 95% CI for B1−B0 and B2−B0 accuracy. With 60 items a 15-point gain is detectable only if B0 is well below ceiling; report the CI whatever it shows.

## Human judgments
One rater (Andrew) rates explanations with the condition hidden and order shuffled; a second rater on 20% if available.

## Stopping rule and budget
One pass per condition; stop at 80 items or the agreed credit budget.
