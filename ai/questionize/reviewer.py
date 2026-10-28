"""Re-review of a published item after learner signals (docs/ARCHITECTURE.md §5.4).

The Argument Judge re-measures the item, the Reviewer weighs flags, answer patterns and the
judge, and a "revise" verdict sends the item through the same solve / critique / judge loop
as a new draft. Rails turns a verified revision into a new item version.
"""

from __future__ import annotations

from . import prompts
from .pipeline import QuestionPipeline, _noop
from .schemas import ReviewDecision, ReviewRequest, ReviewResult


async def review(pipeline: QuestionPipeline, req: ReviewRequest) -> ReviewResult:
    q = req.question
    judged = await pipeline.judge.judge(q) if pipeline.judge is not None else None
    decision = await pipeline.primary.complete(
        prompts.REVIEWER_SYSTEM,
        prompts.reviewer_user(q, [f.model_dump() for f in req.flags], req.crowd.model_dump(), judged),
        ReviewDecision,
        temperature=0.0,
    )
    if decision.verdict != "revise":
        return ReviewResult(decision=decision, judge=judged)

    guidance = decision.revision_guidance or "; ".join(decision.findings)
    revised = await pipeline.verify(0, "", "", q, q.type, _noop, first_guidance=guidance)
    return ReviewResult(decision=decision, judge=judged, revised=revised)
