"""Multi-agent question pipeline.

    Analyst ──► Item Writer ──► Blind Solver ──► Critic ──► Argument Judge ──► (pass) ──► question
                      ▲                │            │
                      └──── Reviser ◄──┴── fail ────┘   (up to MAX_REVISIONS)

The solver never sees the intended answer. A question ships as "verified"
only when the solver independently reaches the keyed answer and the critic
confirms a unique, source-faithful answer with good distractors. Before any
of that, a passage that copies a long run of article text goes straight back
for a rewrite, because shared items must not republish the source.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from . import levels, prompts
from .judge import ArgumentJudge, judge_feedback
from .integrity import INTEGRITY_VERSION, integrity_issues
from .llm import StructuredLLM
from .operator_policy import policy_trace, task_operator
from .schemas import (
    LABELS,
    SUBTYPES,
    ArticleAnalysis,
    CriticResult,
    CapabilityPolicy,
    GenerateRequest,
    GenerateResponse,
    Question,
    SolverResult,
    Verification,
    VerifiedQuestion,
)

Emit = Callable[[dict[str, Any]], Awaitable[None]]

log = logging.getLogger(__name__)

_WORD = re.compile(r"[\w']+")


async def _noop(_: dict[str, Any]) -> None:
    return None


class Declined(Exception):
    """The input is not something we work from; the stream ends with a reason."""

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


class ArticleDeclined(Declined):
    """The analyst judged the page unsuitable; no questions are written."""

    def __init__(self, analysis: ArticleAnalysis):
        super().__init__(analysis.suitability, analysis.suitability_reason)


def normalize_question(q: Question, qtype: str) -> Question:
    """Enforce invariants the model may slip on: family, A-E order, rationale order, trap tags."""
    choices = sorted(q.choices, key=lambda c: c.label)
    rationales = sorted(q.choice_rationales, key=lambda r: r.label)
    if [c.label for c in choices] != list(LABELS) or [r.label for r in rationales] != list(LABELS):
        raise ValueError("Question must have exactly one option and one rationale for each of A-E")
    fixed = []
    for r in rationales:
        is_key = r.label == q.correct_label
        if is_key != (r.trap == "correct"):
            # The key decides; a stray tag would corrupt users' trap statistics.
            log.warning("trap tag %r on option %s disagrees with key %s", r.trap, r.label, q.correct_label)
            r = r.model_copy(update={"trap": "correct" if is_key else "unsupported"})
        fixed.append(r)
    return q.model_copy(update={"type": qtype, "choices": choices, "choice_rationales": fixed})


def longest_copied_run(passage: str, article: str) -> tuple[int, str]:
    """Longest run of consecutive words (case-insensitive) the passage shares with the article."""
    p = _WORD.findall(passage.lower())
    a = _WORD.findall(article.lower())

    def first_shared(k: int) -> int | None:
        grams = {tuple(a[i : i + k]) for i in range(len(a) - k + 1)}
        return next((i for i in range(len(p) - k + 1) if tuple(p[i : i + k]) in grams), None)

    # A shared run of k words contains shared runs of every shorter length, so binary search works.
    lo, hi, at = 0, min(len(p), len(a)), None
    while lo < hi:
        mid = (lo + hi + 1) // 2
        i = first_shared(mid)
        if i is None:
            hi = mid - 1
        else:
            lo, at = mid, i
    return lo, " ".join(p[at : at + lo]) if at is not None else ""


def plan_slots(req: GenerateRequest, analysis: ArticleAnalysis, rng: random.Random) -> list[tuple[str, str]]:
    """Choose (family, sub-type) for each question, adapted to what the article supports."""
    slots: list[tuple[str, str]] = []
    for qtype in req.types:
        options = levels.subtypes(req.level, qtype) if qtype in ("CR", "RC") else list(SUBTYPES[qtype])
        if qtype == "CR" and not any(a.unstated_assumptions or a.potential_flaws for a in analysis.arguments):
            # Purely descriptive article: assumption/flaw items would be forced.
            options = [o for o in ["inference", "strengthen", "weaken"] if o in options] or options
        rng.shuffle(options)
        for i in range(req.count_per_type):
            slots.append((qtype, options[i % len(options)]))
    return slots


class QuestionPipeline:
    def __init__(
        self,
        primary: StructuredLLM,
        solver: StructuredLLM,
        max_revisions: int = 2,
        seed: int | None = None,
        max_copied_words: int = 12,
        judge: ArgumentJudge | None = None,
        integrity_checks: bool = True,
    ):
        self.primary = primary
        self.solver = solver
        self.max_revisions = max_revisions
        self.max_copied_words = max_copied_words
        self.judge = judge
        self.integrity_checks = integrity_checks
        self.rng = random.Random(seed)

    async def analyze(self, req: GenerateRequest) -> ArticleAnalysis:
        return await self.primary.complete(
            prompts.ANALYST_SYSTEM,
            prompts.analyst_user(req.title, req.text, req.selection),
            ArticleAnalysis,
            temperature=0.2,
        )

    async def _build_one(
        self,
        idx: int,
        req: GenerateRequest,
        analysis: ArticleAnalysis,
        qtype: str,
        subtype: str,
        emit: Emit,
    ) -> VerifiedQuestion:
        await emit({"stage": "write", "index": idx, "message": f"Writing {qtype} · {subtype.replace('_', ' ')}"})
        draft = normalize_question(
            await self.primary.complete(
                prompts.WRITER_SYSTEM,
                prompts.writer_user(req.title, req.text, req.selection, analysis, qtype, subtype, req.difficulty, [], levels.brief(req.level)),
                Question,
                temperature=0.7,
            ),
            qtype,
        )

        return await self.verify(idx, req.title, req.text, draft, qtype, emit, audience=levels.brief(req.level),
                                 capability_policy=req.capability_policy, level=req.level)

    async def verify(
        self,
        idx: int,
        title: str,
        text: str,
        draft: Question,
        qtype: str,
        emit: Emit,
        first_guidance: str = "",
        audience: str = "",
        capability_policy: CapabilityPolicy | None = None,
        level: str = "gmat",
    ) -> VerifiedQuestion:
        """Solve, critique and judge a draft, revising until it passes or revisions run out.

        `text` is the source the passage must not copy from (empty when there is none), and
        `first_guidance` is reviewer guidance to apply before the first check (re-reviews).
        """
        if first_guidance:
            await emit({"stage": "revise", "index": idx, "attempt": 0, "message": "Revising with reviewer findings"})
            draft = normalize_question(
                await self.primary.complete(
                    prompts.WRITER_SYSTEM,
                    prompts.reviser_user(title, text or draft.passage, draft, None, None, review_guidance=first_guidance, audience=audience),
                    Question,
                    temperature=0.5,
                ),
                qtype,
            )

        attempts = 1
        solver_result: SolverResult | None = None
        critic: CriticResult | None = None
        judged = None
        trace = policy_trace(capability_policy, subject=qtype, level=level, subtype=draft.subtype, operator=task_operator(draft.stem))
        defects = integrity_issues(draft) if self.integrity_checks else []
        if defects:
            return VerifiedQuestion(id=uuid.uuid4().hex[:12], question=draft, verification=Verification(
                verified=False, attempts=0, solver_model=self.solver.model, solver_answer="", solver_confidence=0,
                critic_verdict="integrity_rejected", distractor_quality=0, issues=defects,
                integrity_version=INTEGRITY_VERSION,
                capability_policy=trace if capability_policy else None))
        while True:
            trace = policy_trace(capability_policy, subject=qtype, level=level, subtype=draft.subtype, operator=task_operator(draft.stem))
            trace.update(judge_gate_reached=False, judge_called=False)
            copied, copied_text = longest_copied_run(draft.passage, text)
            if copied > self.max_copied_words:
                # Not worth a solver call: this passage can't ship either way.
                solver_result, critic, judged, passed = None, None, None, False
                await emit(
                    {
                        "stage": "verdict",
                        "index": idx,
                        "attempt": attempts,
                        "passed": False,
                        "message": f"Passage copies {copied} words from the article — rewriting in original words",
                    }
                )
                if attempts > self.max_revisions:
                    break
                await emit({"stage": "revise", "index": idx, "attempt": attempts, "message": "Rewriting the passage"})
                draft = normalize_question(
                    await self.primary.complete(
                        prompts.WRITER_SYSTEM,
                        prompts.reviser_user(title, text, draft, None, None, copied_text, audience=audience),
                        Question,
                        temperature=0.5,
                    ),
                    qtype,
                )
                attempts += 1
                continue

            await emit({"stage": "solve", "index": idx, "attempt": attempts, "message": "Blind solver attempting the item"})
            solver_result = await self.solver.complete(
                prompts.SOLVER_SYSTEM, prompts.solver_user(draft), SolverResult, temperature=0.0
            )
            agrees = solver_result.answer_label == draft.correct_label
            critic = None
            if agrees:
                await emit({"stage": "critic", "index": idx, "attempt": attempts, "message": "Critic checking uniqueness and distractors"})
                critic = await self.primary.complete(
                    prompts.CRITIC_SYSTEM,
                    prompts.critic_user(title, text, draft, solver_result, audience),
                    CriticResult,
                    temperature=0.0,
                )
            passed = agrees and critic is not None and _critic_passes(critic)
            judged = None
            trace["judge_gate_reached"] = bool(passed and self.judge is not None)
            if passed and self.judge is not None and not trace["judge_abstained"]:
                trace["judge_called"] = True
                await emit({"stage": "judge", "index": idx, "attempt": attempts, "message": "Argument Judge measuring every option"})
                judged = await self.judge.judge(draft)
                passed = judged.verdict in ("pass", "not_applicable")
            await emit(
                {
                    "stage": "verdict",
                    "index": idx,
                    "attempt": attempts,
                    "passed": passed,
                    "solver_answer": solver_result.answer_label,
                    "intended_answer": draft.correct_label,
                    "message": _verdict_message(passed, agrees, solver_result, draft, critic, judged),
                    **({"judge": _judge_summary(judged)} if judged else {}),
                    **({"capability_policy": trace} if capability_policy else {}),
                }
            )
            if passed or attempts > self.max_revisions:
                break
            await emit({"stage": "revise", "index": idx, "attempt": attempts, "message": "Revising with reviewer feedback"})
            draft = normalize_question(
                await self.primary.complete(
                    prompts.WRITER_SYSTEM,
                    prompts.reviser_user(
                        title, text, draft, solver_result, critic,
                        judge_guidance=judge_feedback(judged) if judged and not passed else "",
                        audience=audience,
                    ),
                    Question,
                    temperature=0.5,
                ),
                qtype,
            )
            attempts += 1

        if judged and not passed:
            issues = [judge_feedback(judged)]
        elif critic:
            issues = critic.issues
        elif solver_result:
            issues = [f"Blind solver chose {solver_result.answer_label}"]
        else:
            issues = [f"Passage copies {copied} consecutive words from the article"]
        return VerifiedQuestion(
            id=uuid.uuid4().hex[:12],
            question=draft,
            verification=Verification(
                verified=passed,
                attempts=attempts,
                solver_model=self.solver.model,
                solver_answer=solver_result.answer_label if solver_result else "",
                solver_confidence=solver_result.confidence if solver_result else 0.0,
                critic_verdict=critic.verdict if critic else "skipped",
                distractor_quality=critic.distractor_quality if critic else 0,
                issues=issues,
                copied_words=copied,
                capability_policy=trace if capability_policy else None,
                integrity_version=INTEGRITY_VERSION if self.integrity_checks else None,
            ),
            judge=judged,
        )

    async def run(self, req: GenerateRequest, emit: Emit = _noop) -> GenerateResponse:
        await emit({"stage": "analyze", "message": "Mapping the article's arguments"})
        analysis = await self.analyze(req)
        if analysis.suitability != "suitable":
            raise ArticleDeclined(analysis)
        await emit({"stage": "analyzed", "message": analysis.main_point, "analysis": analysis.model_dump()})

        slots = plan_slots(req, analysis, self.rng)
        await emit({"stage": "plan", "message": f"Generating {len(slots)} questions", "slots": slots})

        results = await asyncio.gather(
            *(self._build_one(i, req, analysis, t, s, emit) for i, (t, s) in enumerate(slots)),
            return_exceptions=True,
        )
        questions: list[VerifiedQuestion] = []
        for i, r in enumerate(results):
            if isinstance(r, BaseException):
                await emit({"stage": "error", "index": i, "message": f"Question {i + 1} failed: {r}"})
            else:
                questions.append(r)
                await emit({"stage": "question", "index": i, "question": r.model_dump()})
        if not questions:
            raise RuntimeError("No questions could be generated for this article")
        return GenerateResponse(analysis=analysis, questions=questions)


def _critic_passes(c: CriticResult) -> bool:
    return c.verdict == "pass" and c.unique_answer and c.faithful_to_source and c.distractor_quality >= 3


def _judge_summary(j) -> dict[str, Any]:
    return {"verdict": j.verdict, "measure": j.measure, "margin": j.margin, "key_first_rate": j.key_first_rate}


def _verdict_message(
    passed: bool, agrees: bool, s: SolverResult, q: Question, c: CriticResult | None, j=None
) -> str:
    if j is not None and j.verdict not in ("pass", "not_applicable"):
        return f"Argument Judge: key leads {j.runner_up} by only {j.margin:.2f} on {j.measure} — revising"
    if passed and j is not None and j.verdict == "pass":
        return f"Verified: solver chose {s.answer_label}; judge margin {j.margin:.2f} on {j.measure}"
    if passed:
        return f"Verified: solver independently chose {s.answer_label} ({s.confidence:.0%} confident)"
    if not agrees:
        return f"Solver chose {s.answer_label}, key says {q.correct_label} — ambiguity detected"
    issues = "; ".join(c.issues[:2]) if c else ""
    return f"Critic flagged: {issues or 'quality below bar'}"
