"""Data contracts for the API and for each agent's structured output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

QuestionType = Literal["RC", "CR", "SC"]
Difficulty = Literal["easy", "medium", "hard"]
Label = Literal["A", "B", "C", "D", "E"]
LABELS: tuple[str, ...] = ("A", "B", "C", "D", "E")

# Sub-types the writer agent may target, per question family.
SUBTYPES: dict[str, list[str]] = {
    "RC": ["main_idea", "detail", "inference", "author_purpose", "structure"],
    "CR": ["weaken", "strengthen", "assumption", "flaw", "evaluate", "inference"],
    "SC": ["grammar_meaning"],
}


# ---------------------------------------------------------------- API models


class GenerateRequest(BaseModel):
    text: str = Field(..., min_length=200, description="Article body extracted from the page")
    title: str = ""
    url: str = ""
    selection: str = Field("", description="Text the reader highlighted, if any; questions focus on it")
    types: list[QuestionType] = Field(default_factory=lambda: ["RC", "CR"])
    count_per_type: int = Field(1, ge=1, le=3)
    difficulty: Difficulty = "medium"


class Choice(BaseModel):
    label: Label
    text: str


class ChoiceRationale(BaseModel):
    label: Label
    rationale: str = Field(..., description="Why this option is right or exactly why it fails")


class Question(BaseModel):
    type: QuestionType
    subtype: str
    passage: str = Field(..., description="RC excerpt, CR argument stimulus, or SC sentence")
    stem: str
    choices: list[Choice] = Field(..., min_length=5, max_length=5)
    correct_label: Label
    explanation: str
    choice_rationales: list[ChoiceRationale] = Field(..., min_length=5, max_length=5)
    skill: str = Field(..., description="The reasoning skill this question trains, in a few words")
    source_anchor: str = Field(
        "", description="A short verbatim phrase from the article the question is grounded in"
    )


class Verification(BaseModel):
    verified: bool
    attempts: int
    solver_model: str
    solver_answer: str
    solver_confidence: float
    critic_verdict: str
    distractor_quality: int
    issues: list[str] = Field(default_factory=list)


class VerifiedQuestion(BaseModel):
    id: str
    question: Question
    verification: Verification


class GenerateResponse(BaseModel):
    analysis: "ArticleAnalysis"
    questions: list[VerifiedQuestion]


# --------------------------------------------------------- agent outputs


class Argument(BaseModel):
    conclusion: str
    premises: list[str]
    unstated_assumptions: list[str]
    potential_flaws: list[str]


class ArticleAnalysis(BaseModel):
    main_point: str
    author_purpose: str
    reading_level: Difficulty
    arguments: list[Argument]
    rc_focus_points: list[str] = Field(..., description="Details/inferences worth testing for RC")
    sc_candidate_sentences: list[str] = Field(
        ..., description="Structurally rich sentences from the article suitable for SC items"
    )


class SolverResult(BaseModel):
    answer_label: Label
    confidence: float = Field(..., ge=0, le=1)
    reasoning: str


class CriticResult(BaseModel):
    verdict: Literal["pass", "revise"]
    unique_answer: bool = Field(..., description="Exactly one option is defensibly correct")
    faithful_to_source: bool = Field(..., description="Nothing contradicts or invents article facts")
    distractor_quality: int = Field(..., ge=1, le=5)
    issues: list[str]
    revision_guidance: str


GenerateResponse.model_rebuild()
