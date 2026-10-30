"""Candidate writing procedures; production activation requires E2 evidence.

Adapted, in our own words, from Matthew Knachel, Fundamental Methods of Logic
(2017), chapters 1, 2, 5, 6. CC BY 4.0.
https://wisconsin.pressbooks.pub/logicfundamentals/
https://creativecommons.org/licenses/by/4.0/
No source examples or official exam text are included. No author endorsement.
"""

VERSION = "cr-design-procedure-1"

COMMON = """DESIGN PROCEDURE:
Start with the exact inference the learner must evaluate. Distinguish the claim to be established
from the stated evidence; do not hide a second logical problem behind factual specialist knowledge.
Build the keyed option to satisfy the task operator, then try to construct a counterexample to it.
For every distractor identify one precise logical failure, not just a different topic or absurd wording.
Keep plausible options comparable in length and specificity; avoid accidental clues from quantifiers.
Check that the explanation and each rationale defend the same key and the same logical objective.
The argument, choices and explanation must be original. Do not mention these design instructions."""

PROCEDURES = {
    "strengthen": "Identify a specific gap between evidence and conclusion. Make the key close that gap without merely repeating the conclusion. Distinguish support for the proposed mechanism from irrelevant background information.",
    "weaken": "For causal claims, distinguish an alternative cause, reverse causation and selection bias. The key must attack this inference; a counterexample to a broader claim the argument never made is not enough.",
    "assumption": "Write a necessary bridge, not a sufficient guarantee. Negating the key must undermine the actual inference. Try negating every competing option too; avoid two necessary bridges among the options.",
    "inference": "Make the key follow from stated premises without importing likely real-world facts. Construct a countermodel for every distractor, keeping universal, existential and conditional statements distinct.",
    "explain": "State two facts that really appear to conflict. The key must make both facts unsurprising together without denying either; options that explain only one fact must remain insufficient.",
}


def scaffold(subtype: str) -> str:
    method = PROCEDURES.get(subtype)
    return COMMON + "\nTASK-SPECIFIC CHECK: " + method if method else ""
