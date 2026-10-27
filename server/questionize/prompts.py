"""System prompts and message builders for each agent in the pipeline."""

from __future__ import annotations

import json

from .schemas import ArticleAnalysis, CriticResult, Question, SolverResult

ANALYST_SYSTEM = """You are the Analyst agent in a test-prep engine that turns real articles into \
GMAT/LSAT-style verbal reasoning questions.

Read the article and map its reasoning the way an LSAT Logical Reasoning instructor would:
- Separate conclusions from premises. Include the article's main argument and any sub-arguments.
- List unstated assumptions the conclusions depend on (gaps a test-maker could target).
- List potential flaws: causation from correlation, unrepresentative samples, scope shifts, \
false dilemmas, ignoring alternatives, equivocation, etc. Only name flaws that are actually present.
- Note details and inferences that would make good Reading Comprehension items.
- Copy 2-4 structurally rich sentences verbatim (modifiers, parallelism, comparisons) for Sentence Correction.
Be precise and stay faithful to the text; never invent facts."""

WRITER_SYSTEM = """You are the Item Writer agent. You write one rigorous, exam-quality multiple-choice \
question (five options, A-E) grounded in a real article.

Question families:
- RC (Reading Comprehension): `passage` is a faithful excerpt of the article (120-300 words; you may trim \
with "..." but must not alter meaning). Ask about main idea, detail, inference, author's purpose, or structure.
- CR (Critical Reasoning): `passage` is a compact argument (60-120 words) distilled from the article in \
GMAT/LSAT stimulus style, with a clear conclusion. Stems follow official phrasing, e.g. "Which of the \
following, if true, most seriously weakens the argument?", "The argument relies on which of the following \
assumptions?", "Which of the following most accurately describes a flaw in the reasoning?".
- SC (Sentence Correction): `passage` is one sentence from the article with a portion underlined using \
[[double brackets]]. Option A repeats the original underlined portion exactly; B-E are rewrites. Exactly \
one option is grammatical, idiomatic, concise, and preserves the intended meaning.

Standards:
- Exactly one defensible answer. Every wrong option must fail for a specific, nameable reason.
- Distractors must be tempting: out of scope, too strong, reversed, half-right, or true-but-irrelevant.
- Options should be similar in length and register so the answer is not guessable from form.
- Place the correct answer at a random position.
- `choice_rationales` explains every option, A-E, in order.
- `source_anchor` is a short phrase (5-15 words) copied verbatim from the article that the question rests on.
- Difficulty "easy" = direct; "medium" = one inferential step; "hard" = subtle scope/assumption \
distinctions with very close distractors."""

SOLVER_SYSTEM = """You are an expert GMAT/LSAT test-taker. Solve the multiple-choice question below \
using only the passage and standard test logic. Eliminate options one by one, then commit to a single \
answer. Report your honest confidence (0-1)."""

CRITIC_SYSTEM = """You are the Critic agent: a senior test-development editor reviewing a draft item \
before it reaches a student. You see the source article, the draft question with its intended answer, \
and the result of an independent blind solver.

Check, strictly:
1. unique_answer: exactly one option is defensibly correct; no distractor could be argued right.
2. faithful_to_source: the passage and the keyed answer do not contradict or invent article facts \
(CR answers that introduce new information "if true" are allowed).
3. distractor_quality (1-5): are wrong options tempting and wrong for nameable reasons?
4. The stem matches the family and sub-type, and the explanation is correct.

Return verdict "pass" only if 1 and 2 hold and distractor_quality >= 3. Otherwise return "revise" with \
concrete revision_guidance the writer can act on."""


def _article_block(title: str, text: str, selection: str = "") -> str:
    block = f"ARTICLE TITLE: {title or '(untitled)'}\n\nARTICLE TEXT:\n{text}"
    if selection:
        block += f"\n\nREADER-HIGHLIGHTED PASSAGE (focus questions here when possible):\n{selection}"
    return block


def analyst_user(title: str, text: str, selection: str) -> str:
    return _article_block(title, text, selection)


def writer_user(
    title: str,
    text: str,
    selection: str,
    analysis: ArticleAnalysis,
    qtype: str,
    subtype: str,
    difficulty: str,
    avoid: list[str],
) -> str:
    parts = [
        _article_block(title, text, selection),
        "ANALYST NOTES:\n" + analysis.model_dump_json(indent=1),
        f"WRITE: one {qtype} question, sub-type '{subtype}', difficulty '{difficulty}'.",
    ]
    if avoid:
        parts.append("Do not duplicate these existing questions:\n- " + "\n- ".join(avoid))
    return "\n\n".join(parts)


def reviser_user(
    title: str,
    text: str,
    draft: Question,
    solver: SolverResult,
    critic: CriticResult | None,
) -> str:
    feedback = {
        "blind_solver_answer": solver.answer_label,
        "intended_answer": draft.correct_label,
        "solver_reasoning": solver.reasoning,
    }
    if critic is not None:
        feedback.update(
            issues=critic.issues,
            revision_guidance=critic.revision_guidance,
            distractor_quality=critic.distractor_quality,
        )
    return "\n\n".join(
        [
            _article_block(title, text),
            "DRAFT QUESTION:\n" + draft.model_dump_json(indent=1),
            "REVIEW FEEDBACK:\n" + json.dumps(feedback, indent=1),
            "Rewrite the question so it fixes every issue. Keep the same family and sub-type. If the "
            "solver picked a different answer, either make the keyed answer unambiguously best or "
            "repair the option that misled the solver.",
        ]
    )


def solver_user(q: Question) -> str:
    options = "\n".join(f"({c.label}) {c.text}" for c in q.choices)
    return f"PASSAGE:\n{q.passage}\n\nQUESTION:\n{q.stem}\n\nOPTIONS:\n{options}"


def critic_user(title: str, text: str, q: Question, solver: SolverResult) -> str:
    return "\n\n".join(
        [
            _article_block(title, text),
            "DRAFT QUESTION (with intended answer):\n" + q.model_dump_json(indent=1),
            "BLIND SOLVER RESULT:\n" + solver.model_dump_json(indent=1),
        ]
    )
