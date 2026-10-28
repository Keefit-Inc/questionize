"""Error log: one photographed question → a private diagnosis, new practice, abstract knowledge.

(docs/KNOWLEDGE_MODEL.md §6, §9.) The image and its transcript exist only for the length of the
request. What leaves this service is the learner's diagnosis (in our own words), new original
practice items built from the question's abstract design, and that design as an observation for
the knowledge model, after checks that none of it copies the photographed question.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Any

from . import prompts
from .pipeline import Declined, QuestionPipeline, longest_copied_run, normalize_question
from .schemas import Diagnosis, DiagnoseRequest, PhotoReading, Question

Emit = Callable[[dict[str, Any]], Awaitable[None]]

# Longest run of words any stored field may share with the photographed question.
MAX_FIELD_COPIED_WORDS = 8
PRACTICE_ITEMS = 2
TOPICS = ["city services", "small business", "ecology", "sports science", "museums", "public health", "farming", "transport", "astronomy", "music education"]


async def diagnose(pipeline: QuestionPipeline, req: DiagnoseRequest, emit: Emit, seed: int | None = None) -> dict[str, Any]:
    rng = random.Random(seed)
    await emit({"stage": "reading", "message": "Reading the photographed question"})
    reading = await pipeline.primary.complete(
        prompts.READER_SYSTEM, prompts.reader_user(req.chosen_label), PhotoReading, temperature=0.0, images=[req.image]
    )
    if not reading.readable or reading.kind == "not_a_question":
        raise Declined("not_a_question", "We couldn't find one readable practice question in that photo.")
    if reading.kind == "live_exam_suspected":
        raise Declined("live_exam", "This looks like a question from a live exam. We don't work with recalled or leaked exam content.")

    transcript = reading.transcript
    pattern, field_copied = _scrub(reading.pattern, transcript)
    explanation = reading.explanation
    explanation_copied, _ = longest_copied_run(explanation, transcript)
    if explanation_copied > MAX_FIELD_COPIED_WORDS:
        explanation = "We couldn't explain this one without quoting it; open your book alongside the practice questions below."

    chosen_correct = None if req.chosen_label is None or reading.key_guess is None else req.chosen_label == reading.key_guess
    diagnosis = Diagnosis(
        family=pattern.family, subtype=pattern.subtype, competency=pattern.competency, key_guess=reading.key_guess,
        chosen_label=req.chosen_label, chosen_correct=chosen_correct,
        chosen_trap=None if chosen_correct else reading.chosen_trap,
        misconception=None if chosen_correct else reading.misconception, explanation=explanation,
    )
    await emit({"stage": "diagnosed", "message": f"Measures: {pattern.competency}"})

    await emit({"stage": "practice", "message": "Writing new practice on the same trap"})
    topics = rng.sample(TOPICS, PRACTICE_ITEMS)
    results = await asyncio.gather(
        *(_practice(pipeline, i, pattern, diagnosis, transcript, topic, emit) for i, topic in enumerate(topics)),
        return_exceptions=True,
    )
    practice = [r for r in results if not isinstance(r, BaseException) and r.verification.copied_words <= pipeline.max_copied_words]

    # The commons only gets the design if it passed the field checks and could be rebuilt as
    # something new: practice items that copy the photo would mean the design leaks the source.
    practice_copied = max((r.verification.copied_words for r in results if not isinstance(r, BaseException)), default=0)
    leak_checks = {
        "max_field_copied_words": max(field_copied, explanation_copied),
        "max_practice_copied_words": practice_copied,
        "personal_data_present": reading.personal_data_present,
        "passed": field_copied <= MAX_FIELD_COPIED_WORDS and practice_copied <= pipeline.max_copied_words,
    }
    return {
        "stage": "diagnosis",
        "diagnosis": diagnosis.model_dump(),
        "observation": pattern.model_dump() if leak_checks["passed"] else None,
        "leak_checks": leak_checks,
        "practice": [p.model_dump() for p in practice],
    }


async def _practice(pipeline, index, pattern, diagnosis, transcript, topic, emit):
    draft = normalize_question(
        await pipeline.primary.complete(
            prompts.PATTERN_WRITER_SYSTEM,
            prompts.pattern_writer_user(pattern.model_dump_json(indent=1), diagnosis.chosen_trap, "medium", topic),
            Question,
            temperature=0.8,
        ),
        pattern.family,
    )
    # The photographed question is the "source" no practice passage may copy from.
    return await pipeline.verify(index, "", transcript, draft, pattern.family, emit)


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
