"""Data contracts for the API and for each agent's structured output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

QuestionType = Literal["RC", "CR", "SC"]
Difficulty = Literal["easy", "medium", "hard"]
Label = Literal["A", "B", "C", "D", "E"]
LABELS: tuple[str, ...] = ("A", "B", "C", "D", "E")

# Why an option is right or wrong. Tagging every distractor lets the app show a user which
# traps they fall for, not just which items they miss.
TrapType = Literal[
    "correct",
    "out_of_scope",  # brings in something the passage doesn't address
    "too_extreme",  # language stronger than the passage supports (always, never, all)
    "reversal",  # flips cause and effect, direction, or the relationship
    "half_right",  # starts right, then adds an unsupported or wrong part
    "unsupported",  # plausible, but the passage gives no basis for it
    "irrelevant",  # true or reasonable, but doesn't bear on the question asked
    "distortion",  # misstates or twists what the passage says
    "grammar_error",  # SC: ungrammatical or unidiomatic
    "changes_meaning",  # SC: grammatical but alters the intended meaning
]

# Whether a page should become questions at all. Anything but "suitable" stops the run after analysis.
Suitability = Literal[
    "suitable",
    "too_thin",  # not enough claims, reasoning or detail for a fair question
    "not_an_article",  # shop, search results, feed, login or error page, navigation
    "exam_material",  # the page itself is test-prep or exam questions
    "harmful",  # mainly hate or extremist propaganda, explicit sexual content, or instructions to cause harm
    "private",  # personal messages, documents or records about private people
]

# Sensitive subject matter. Flagged items stay out of the public feed until a person reviews them.
ContentFlag = Literal[
    "sexual_violence",
    "self_harm",
    "graphic_violence",
    "harm_to_minors",
    "hate_or_harassment",
    "explicit_sexual_content",
]

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
    # Critical Reasoning is the core family; SC stays available but is not requested by default.
    types: list[QuestionType] = Field(default_factory=lambda: ["CR", "RC"])
    count_per_type: int = Field(1, ge=1, le=3)
    difficulty: Difficulty = "medium"


class Choice(BaseModel):
    label: Label
    text: str


class ChoiceRationale(BaseModel):
    label: Label
    rationale: str = Field(..., description="Why this option is right or exactly why it fails")
    trap: TrapType = Field(..., description='"correct" for the keyed answer; otherwise the trap this distractor sets')


class Question(BaseModel):
    type: QuestionType
    subtype: str
    passage: str = Field(
        ..., description="RC passage, CR argument stimulus, or SC sentence, written in original words (not copied)"
    )
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
    copied_words: int = Field(0, description="Longest run of consecutive words the passage shares with the article")


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
    suitability: Suitability = Field(..., description='Decide first; "suitable" unless a decline reason clearly applies')
    suitability_reason: str = Field(..., description="One sentence a reader can see explaining the decision")
    main_point: str
    author_purpose: str
    reading_level: Difficulty
    arguments: list[Argument]
    rc_focus_points: list[str] = Field(..., description="Details/inferences worth testing for RC")
    sc_candidate_sentences: list[str] = Field(
        ..., description="Structurally rich sentences from the article suitable for SC items"
    )
    content_flags: list[ContentFlag] = Field(
        ..., description="Sensitive subject matter the article centrally involves; empty when none applies"
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
