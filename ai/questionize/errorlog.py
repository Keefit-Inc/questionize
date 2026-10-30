"""Error log: one photographed question → a private diagnosis, new practice, abstract knowledge.

(docs/KNOWLEDGE_MODEL.md §6, §9.) The image and its transcript exist only for the length of the
request. What leaves this service is the learner's diagnosis (in our own words), new original
practice items built from the question's abstract design, and that design as an observation for
the knowledge model, after checks that none of it copies the photographed question. The question
itself goes back once as `source_question`, for the learner's own device only; Rails hands it over
and does not keep it.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Any

from . import levels, prompts
from .pipeline import Declined, QuestionPipeline, longest_copied_run, normalize_question
from .schemas import Diagnosis, DiagnoseRequest, FlatPhotoReading, KeyCheck, KeyReview, PatternObservation, PhotoReading, PracticeRequest, Question, SolverResult, SourceQuestion

Emit = Callable[[dict[str, Any]], Awaitable[None]]

# Longest run of words any stored field may share with the photographed question.
MAX_FIELD_COPIED_WORDS = 8
TOPICS = ["city services", "small business", "ecology", "sports science", "museums", "public health", "farming", "transport", "astronomy", "music education"]


async def diagnose(pipeline: QuestionPipeline, req: DiagnoseRequest, emit: Emit, seed: int | None = None) -> dict[str, Any]:
    rng = random.Random(seed)
    await emit({"stage": "reading", "message": "Reading the photographed question"})
    reading = (
        await pipeline.primary.complete(
            prompts.READER_SYSTEM, prompts.reader_user(req.chosen_label, levels.brief(req.level)), FlatPhotoReading, temperature=0.0, images=req.images,
        )
    ).reading
    if not reading.readable or reading.kind == "not_a_question":
        raise Declined("not_a_question", "We couldn't find one readable practice question in that photo.")
    if reading.kind == "live_exam_suspected":
        raise Declined("live_exam", "This looks like a question from a live exam. We don't work with recalled or leaked exam content.")

    key_check, key = await _check_key(pipeline, reading, req, emit)
    if key is not None and key != reading.key_guess:
        # Our first reading explained a different answer; explain the checked one instead.
        reread = (
            await pipeline.primary.complete(
                prompts.READER_SYSTEM, prompts.reader_user(req.chosen_label, levels.brief(req.level), key), FlatPhotoReading,
                temperature=0.0, images=req.images,
            )
        ).reading
        reading = reread.model_copy(update={"key_guess": key, "question": reading.question})

    transcript = reading.question.text()
    pattern, field_copied = _scrub(reading.pattern, transcript)
    explanation = reading.explanation
    explanation_copied, _ = longest_copied_run(explanation, transcript)
    if explanation_copied > MAX_FIELD_COPIED_WORDS:
        explanation = "We couldn't explain this one without quoting it; open your book alongside the practice questions below."
    # The learner reads these next to their own book, so they may be specific, but never quote it.
    private_copied = 0

    def own_words(text: str) -> str:
        nonlocal private_copied
        copied, _ = longest_copied_run(text, transcript)
        private_copied = max(private_copied, copied)
        return "" if copied > MAX_FIELD_COPIED_WORDS else text

    intent = own_words(reading.intent)
    objectives = [o for o in (own_words(o) for o in reading.learning_objectives) if o]
    reviews = sorted(
        (r.model_copy(update={"reason": own_words(r.reason)}) for r in {r.label: r for r in reading.option_reviews}.values()),
        key=lambda r: r.label,
    )

    chosen_correct = None if req.chosen_label is None or reading.key_guess is None else req.chosen_label == reading.key_guess
    diagnosis = Diagnosis(
        family=pattern.family, subtype=pattern.subtype, competency=pattern.competency, key_guess=reading.key_guess,
        chosen_label=req.chosen_label, chosen_correct=chosen_correct,
        chosen_trap=None if chosen_correct else reading.chosen_trap,
        misconception=None if chosen_correct else reading.misconception, explanation=explanation,
        difficulty=reading.difficulty, difficulty_drivers=[d for d in pattern.difficulty_drivers if d],
        intent=intent, learning_objectives=objectives, option_reviews=reviews, key_check=key_check,
    )
    # The analysis screen animates from these: what the question measures, how hard it is, the verdict.
    await emit({"stage": "diagnosed", "message": f"Measures: {pattern.competency}", "competency": pattern.competency,
                "family": pattern.family, "subtype": pattern.subtype, "difficulty": reading.difficulty,
                "key_guess": reading.key_guess, "chosen_correct": chosen_correct})

    if req.practice_count:
        await emit({"stage": "practice", "message": "Writing new practice on the same trap"})
    topics = rng.sample(TOPICS, req.practice_count)
    results = await asyncio.gather(
        *(_practice(pipeline, i, pattern, diagnosis.chosen_trap, transcript, topic, emit, req.level, req.capability_policy) for i, topic in enumerate(topics)),
        return_exceptions=True,
    )
    practice = [r for r in results if not isinstance(r, BaseException) and r.verification.copied_words <= pipeline.max_copied_words]

    # The commons only gets the design if it passed the field checks and could be rebuilt as
    # something new: practice items that copy the photo would mean the design leaks the source.
    practice_copied = max((r.verification.copied_words for r in results if not isinstance(r, BaseException)), default=0)
    leak_checks = {
        "max_field_copied_words": max(field_copied, explanation_copied, private_copied),
        "max_practice_copied_words": practice_copied,
        "personal_data_present": reading.personal_data_present,
        "passed": max(field_copied, private_copied) <= MAX_FIELD_COPIED_WORDS and practice_copied <= pipeline.max_copied_words,
    }
    return {
        "stage": "diagnosis",
        "diagnosis": diagnosis.model_dump(),
        "observation": pattern.model_dump() if leak_checks["passed"] else None,
        "leak_checks": leak_checks,
        "practice": [p.model_dump() for p in practice],
        "source_question": reading.question.model_dump(),
    }


async def _check_key(pipeline: QuestionPipeline, reading: PhotoReading, req: DiagnoseRequest, emit: Emit) -> tuple[KeyCheck, Any]:
    """Decide which answer to explain. With no key entered, our reading stands. When the learner's key
    and our reading disagree, a second, blind solver and an editor's review decide: the book is
    usually right, but a mistyped letter should not become the 'correct' answer."""
    provided, first = req.answer_key, reading.key_guess
    if provided is None:
        return KeyCheck(provided=None, first_reading=first, verdict="unchecked"), first
    if provided == first:
        return KeyCheck(provided=provided, first_reading=first, verdict="agrees"), provided

    await emit({"stage": "checking", "message": f"Checking the key: you entered {provided}, our reading chose {first or 'none'}"})
    solved = await pipeline.solver.complete(prompts.SOLVER_SYSTEM, _solver_text(reading.question), SolverResult, temperature=0.0)
    if solved.answer_label == provided:
        note = f"Our first reading chose {first}; an independent solver agreed with your key, {provided}."
        return KeyCheck(provided=provided, first_reading=first, solver_answer=solved.answer_label, verdict="upheld", note=note), provided

    review = await pipeline.primary.complete(
        prompts.KEY_REVIEW_SYSTEM,
        prompts.key_review_user(reading.question.text(), provided, [x for x in (first, solved.answer_label) if x]),
        KeyReview,
        temperature=0.0,
    )
    if review.book_key_defensible or solved.answer_label != first:
        note = f"Two readings disagreed with {provided}, but a review found it defensible, so we kept your key."
        return KeyCheck(provided=provided, first_reading=first, solver_answer=solved.answer_label, verdict="upheld", note=note), provided
    note = (f"Two independent readings chose {first}, and a review could not defend {provided}. "
            f"Please check the letter you entered; this analysis explains {first}.")
    return KeyCheck(provided=provided, first_reading=first, solver_answer=solved.answer_label, verdict="disputed", note=note), first


def _solver_text(q: SourceQuestion) -> str:
    options = "\n".join(f"({c.label}) {c.text}" for c in q.choices)
    return f"PASSAGE:\n{q.passage}\n\nQUESTION:\n{q.stem}\n\nOPTIONS:\n{options}"


async def practice_for_level(pipeline: QuestionPipeline, req: PracticeRequest, seed: int | None = None) -> dict[str, Any]:
    """Verified practice from an abstract design at one level. A design whose skill is out of scope
    for the level (an LSAT flaw question for Grades 3-5) is skipped rather than forced."""
    if req.design.subtype not in levels.subtypes(req.level, req.design.family):
        return {"level": req.level, "skipped": "subtype_out_of_scope", "practice": []}

    async def quiet(_event):
        return None

    rng = random.Random(seed)
    topics = rng.sample(TOPICS, req.count)
    results = await asyncio.gather(
        *(_practice(pipeline, i, req.design, req.practice_trap, "", topic, quiet, req.level, req.capability_policy) for i, topic in enumerate(topics)),
        return_exceptions=True,
    )
    practice = [r for r in results if not isinstance(r, BaseException) and r.verification.verified]
    return {"level": req.level, "skipped": None, "practice": [p.model_dump() for p in practice]}


async def _practice(pipeline, index, pattern: PatternObservation, practice_trap, transcript, topic, emit, level=None, capability_policy=None):
    audience = levels.brief(level)
    draft = normalize_question(
        await pipeline.primary.complete(
            prompts.PATTERN_WRITER_SYSTEM,
            prompts.pattern_writer_user(pattern.model_dump_json(indent=1), practice_trap, "medium", topic, audience),
            Question,
            temperature=0.8,
        ),
        pattern.family,
    )
    # The photographed question is the "source" no practice passage may copy from.
    return await pipeline.verify(index, "", transcript, draft, pattern.family, emit, audience=audience,
                                 capability_policy=capability_policy, level=level or "gmat")


def _scrub(pattern, transcript: str):
    """Blank any free-text field that shares too long a run of words with the photographed question."""
    worst = 0

    def clean(text: str) -> str:
        nonlocal worst
        copied, _ = longest_copied_run(text, transcript)
        worst = max(worst, copied)
        return "" if copied > MAX_FIELD_COPIED_WORDS else text

    scrubbed = pattern.model_copy(
        update={
            "competency": clean(pattern.competency),
            "key_rule": clean(pattern.key_rule),
            "stimulus_features": [clean(f) for f in pattern.stimulus_features],
            "difficulty_drivers": [clean(d) for d in pattern.difficulty_drivers],
        }
    )
    return scrubbed, worst
