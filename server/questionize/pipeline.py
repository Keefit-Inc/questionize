"""Multi-agent question pipeline.

    Analyst ──► Item Writer ──► Blind Solver ──► Critic ──► (pass) ──► question
                      ▲                │            │
                      └──── Reviser ◄──┴── fail ────┘   (up to MAX_REVISIONS)

The solver never sees the intended answer. A question ships as "verified"
only when the solver independently reaches the keyed answer and the critic
confirms a unique, source-faithful answer with good distractors.
"""

from __future__ import annotations

import asyncio
import random
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from . import prompts
from .llm import StructuredLLM
from .schemas import (
    LABELS,
    SUBTYPES,
    ArticleAnalysis,
    CriticResult,
    GenerateRequest,
    GenerateResponse,
    Question,
    SolverResult,
    Verification,
    VerifiedQuestion,
)

Emit = Callable[[dict[str, Any]], Awaitable[None]]


async def _noop(_: dict[str, Any]) -> None:
    return None


def normalize_question(q: Question, qtype: str) -> Question:
    """Enforce invariants the model may slip on: family, A-E order, rationale order."""
    choices = sorted(q.choices, key=lambda c: c.label)
    rationales = sorted(q.choice_rationales, key=lambda r: r.label)
    if [c.label for c in choices] != list(LABELS) or [r.label for r in rationales] != list(LABELS):
        raise ValueError("Question must have exactly one option and one rationale for each of A-E")
    return q.model_copy(update={"type": qtype, "choices": choices, "choice_rationales": rationales})


def plan_slots(req: GenerateRequest, analysis: ArticleAnalysis, rng: random.Random) -> list[tuple[str, str]]:
    """Choose (family, sub-type) for each question, adapted to what the article supports."""
    slots: list[tuple[str, str]] = []
    for qtype in req.types:
        options = list(SUBTYPES[qtype])
        if qtype == "CR" and not any(a.unstated_assumptions or a.potential_flaws for a in analysis.arguments):
            # Purely descriptive article: assumption/flaw items would be forced.
            options = ["inference", "strengthen", "weaken"]
        rng.shuffle(options)
        for i in range(req.count_per_type):
            slots.append((qtype, options[i % len(options)]))
    return slots


class QuestionPipeline:
    def __init__(self, primary: StructuredLLM, solver: StructuredLLM, max_revisions: int = 2, seed: int | None = None):
        self.primary = primary
        self.solver = solver
        self.max_revisions = max_revisions
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
                prompts.writer_user(req.title, req.text, req.selection, analysis, qtype, subtype, req.difficulty, []),
                Question,
                temperature=0.7,
            ),
            qtype,
        )

        attempts = 1
        solver_result: SolverResult | None = None
        critic: CriticResult | None = None
        while True:
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
                    prompts.critic_user(req.title, req.text, draft, solver_result),
                    CriticResult,
                    temperature=0.0,
                )
            passed = agrees and critic is not None and _critic_passes(critic)
            await emit(
                {
                    "stage": "verdict",
                    "index": idx,
                    "attempt": attempts,
                    "passed": passed,
                    "solver_answer": solver_result.answer_label,
                    "intended_answer": draft.correct_label,
                    "message": _verdict_message(passed, agrees, solver_result, draft, critic),
                }
            )
            if passed or attempts > self.max_revisions:
                break
            await emit({"stage": "revise", "index": idx, "attempt": attempts, "message": "Revising with reviewer feedback"})
            draft = normalize_question(
                await self.primary.complete(
                    prompts.WRITER_SYSTEM,
                    prompts.reviser_user(req.title, req.text, draft, solver_result, critic),
                    Question,
                    temperature=0.5,
                ),
                qtype,
            )
            attempts += 1

        return VerifiedQuestion(
            id=uuid.uuid4().hex[:12],
            question=draft,
            verification=Verification(
                verified=passed,
                attempts=attempts,
                solver_model=self.solver.model,
                solver_answer=solver_result.answer_label,
                solver_confidence=solver_result.confidence,
                critic_verdict=critic.verdict if critic else "skipped",
                distractor_quality=critic.distractor_quality if critic else 0,
                issues=critic.issues if critic else [f"Blind solver chose {solver_result.answer_label}"],
            ),
        )

    async def run(self, req: GenerateRequest, emit: Emit = _noop) -> GenerateResponse:
        await emit({"stage": "analyze", "message": "Mapping the article's arguments"})
        analysis = await self.analyze(req)
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


def _verdict_message(passed: bool, agrees: bool, s: SolverResult, q: Question, c: CriticResult | None) -> str:
    if passed:
        return f"Verified: solver independently chose {s.answer_label} ({s.confidence:.0%} confident)"
    if not agrees:
        return f"Solver chose {s.answer_label}, key says {q.correct_label} — ambiguity detected"
    issues = "; ".join(c.issues[:2]) if c else ""
    return f"Critic flagged: {issues or 'quality below bar'}"
