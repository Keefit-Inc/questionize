# E1: Solving and explaining official-style items (v2)

- **Capability:** C3.1, C3.2 (RQ1)
- **Hypotheses:** H1a: B1 and B2 reach a higher solving accuracy against the answer key than B0, and their explanations are judged correct more often. H1d: a memory of lessons learned on the train split (the model solves blind, then reflects against the book's key and explanation; lessons consolidated per sub-type, no item text) raises the same conditions' accuracy on the test split.
- **Registered:** 2026-10-29, before any results were seen

## Dataset
50–80 Critical Reasoning / Logical Reasoning items from published GMAT and LSAT practice books owned by the team, photographed one at a time, with the book's answer key entered as a letter. Private dataset id `official-cr-v1`. Items kept outside the repository. Items without a key, and items whose entered key the Snap key check disputed, are excluded and counted in the manifest.

## Split
Items verified by E4 (layout rules and model structuring agree on every field and the key) are split by a hash of dataset id and question number: 60% train, 40% test. All E1 scores are on the test split; the memory is learned only from train.

## Conditions
- **B0:** Muse Spark 1.3 answers and explains in one call.
- **B1:** Our pipeline's blind solver answers; for weaken, strengthen and assumption items the Argument Judge measures every option and replaces the solver's answer when its top option stays first in at least 80% of bootstrap resamples. The explanation is written after the decision, by a call told the settled answer and allowed to object. (The critic checks questions we write, not official ones, so it has no role here.)
- **B2:** Muse Spark 1.3 and Muse Spark Open answer independently, exchange reasoning for up to two rounds while they disagree, and settle (agreement, else the more confident final answer) the answer and explanation; if no Baseten access, two differently-instructed runs of one model (reported as B2′).
- **B0+M, B1+M (B2+M):** the same conditions with the memory's rules for the item's sub-type added to every system prompt. Paired against the same conditions' run without memory on the same test items.

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

## Changes
v1 → v2 (2026-10-30, before any results): added the train/test split and the memory conditions (H1d).
