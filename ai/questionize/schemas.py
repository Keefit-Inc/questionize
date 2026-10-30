"""Data contracts for the API and for each agent's structured output."""

from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, Field, PrivateAttr, model_validator

QuestionType = Literal["RC", "CR", "SC"]
Difficulty = Literal["easy", "medium", "hard"]
Label = Literal["A", "B", "C", "D", "E"]
LABELS: tuple[str, ...] = ("A", "B", "C", "D", "E")


class CapabilityPolicyPayload(BaseModel):
    """The first bounded evolution experiment changes one verifier decision only."""

    model_config = {"extra": "forbid"}
    except_mode: Literal["legacy", "abstain"] = "legacy"


class CapabilityPolicy(BaseModel):
    model_config = {"extra": "forbid"}
    id: str = Field(..., min_length=1, max_length=120)
    hash: str = Field(..., pattern=r"^[0-9a-f]{16,64}$")
    payload: CapabilityPolicyPayload

    @model_validator(mode="after")
    def verify_hash(self) -> CapabilityPolicy:
        import hashlib
        import json

        expected = hashlib.sha256(json.dumps(self.payload.model_dump(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if not expected.startswith(self.hash):
            raise ValueError("capability policy hash does not match its payload")
        return self


class LearningMemoryPayload(BaseModel):
    model_config = {"extra": "forbid"}
    expert_rules: list[str] = Field(default_factory=list, max_length=4)
    experience_rules: list[str] = Field(default_factory=list, max_length=4)


class LearningMemory(BaseModel):
    model_config = {"extra": "forbid"}
    id: str
    version: int = Field(..., ge=1)
    hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    payload: LearningMemoryPayload

    @model_validator(mode="after")
    def check_hash(self):
        import hashlib
        import json
        value = json.dumps(self.payload.model_dump(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if hashlib.sha256(value.encode()).hexdigest() != self.hash:
            raise ValueError("Learning-memory hash mismatch")
        return self

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
    level: LevelId = Field("gmat", description="Who the questions are written for (questionize/levels.py)")
    capability_policy: CapabilityPolicy | None = None


class Choice(BaseModel):
    label: Label
    text: str


class ChoiceRationale(BaseModel):
    label: Label
    rationale: str = Field(..., description="Why this option is right or exactly why it fails")
    trap: TrapType = Field(..., description='"correct" for the keyed answer; otherwise the trap this distractor sets')


# The kind of situation a question is set in, for the illustration shown with it.
Scene = Literal[
    "everyday", "school", "science", "health", "nature", "animals", "city", "business",
    "technology", "sports", "arts", "history", "food", "law", "space", "transport",
]

LevelId = Literal["elementary", "middle", "high", "college", "gmat", "lsat", "gre"]


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
    scene: Scene = Field("everyday", description="The kind of situation the passage is set in")


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
    capability_policy: dict | None = None
    integrity_version: str | None = None


# ------------------------------------------------------------- Argument Judge


class JudgeRequest(BaseModel):
    """An argument and its options, for POST /v1/judge."""

    passage: str = Field(..., min_length=20)
    stem: str
    choices: list[Choice] = Field(..., min_length=5, max_length=5)
    correct_label: Label
    subtype: str


class OptionRating(BaseModel):
    """One judge sample's reading of one option (docs/ARCHITECTURE.md §4.5)."""

    option: str = Field(..., description="The option's letter as shown")
    support_delta: float = Field(
        ..., ge=-1, le=1, description="How far, and which way, the conclusion's likelihood moves if this option is true"
    )
    necessity: float = Field(..., ge=0, le=1, description="Probability the argument falls apart if this option is false")


class JudgeRatings(BaseModel):
    ratings: list[OptionRating] = Field(..., min_length=2, max_length=8)


class Measurement(BaseModel):
    value: float
    ci_low: float
    ci_high: float


class OptionJudgement(BaseModel):
    label: Label
    support_delta: Measurement
    necessity: Measurement


JudgeVerdict = Literal["pass", "ambiguous", "wrong_key", "not_applicable"]


class JudgeResult(BaseModel):
    judge_version: str
    # Which measure decides this sub-type ("support_delta" or "necessity"), or None when not covered yet.
    measure: str | None
    direction: Literal["max", "min"] | None
    options: list[OptionJudgement]
    key_first_rate: float = Field(..., description="Share of bootstrap resamples where the key ranks first")
    margin: float = Field(..., description="Median gap between the key and the best other option")
    runner_up: Label | None
    judges: list[str]
    samples: int
    verdict: JudgeVerdict


class VerifiedQuestion(BaseModel):
    id: str
    question: Question
    verification: Verification
    judge: JudgeResult | None = None


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


# ------------------------------------------------------------- Argument map (Map → Challenge)

ArgumentScheme = Literal[
    "causal", "generalization", "analogy", "expert_opinion", "consequences", "sign", "comparison", "definition", "other"
]
ChallengeKind = Literal["weaken", "assumption", "strengthen"]


class MapClaim(BaseModel):
    text: str = Field(..., description="The claim in your own words, faithful to the author")
    anchor: str = Field("", description="A short verbatim phrase (5-15 words) from the article where it appears")


class ChallengeDraft(BaseModel):
    kind: ChallengeKind
    question: str = Field(..., description="A critical question a careful reader should ask of this argument")
    options: list[str] = Field(
        ..., min_length=5, max_length=5,
        description='Five candidate answers, each a conditional ("If it turned out that ...") or a plain unstated premise',
    )


class MapDraft(BaseModel):
    scheme: ArgumentScheme
    conclusion: MapClaim
    premises: list[MapClaim] = Field(..., min_length=1, max_length=4)
    assumptions: list[str] = Field(..., min_length=1, max_length=3, description="Unstated assumptions, in your own words")
    challenges: list[ChallengeDraft] = Field(..., min_length=3, max_length=3)


class MapElement(BaseModel):
    id: str
    text: str
    anchor: str = ""
    support_delta: Measurement
    necessity: Measurement


class ChallengeOption(BaseModel):
    label: Label
    text: str
    support_delta: Measurement
    necessity: Measurement


class JudgedAnswer(BaseModel):
    label: Label
    measure: str
    first_rate: float
    margin: float
    runner_up: Label


class Challenge(BaseModel):
    index: int
    kind: ChallengeKind
    question: str
    options: list[ChallengeOption]
    judged: JudgedAnswer


class ArgumentMap(BaseModel):
    judge_version: str
    scheme: ArgumentScheme
    conclusion: MapClaim
    premises: list[MapElement]
    assumptions: list[MapElement]
    largest_gap: str = Field(..., description="Id of the unstated assumption the argument leans on most")
    challenges: list[Challenge]


class MapRequest(BaseModel):
    text: str = Field(..., min_length=200)
    title: str = ""
    url: str = ""
    selection: str = ""


# ------------------------------------------------------------- Re-review (quality loop)


class Flag(BaseModel):
    reason: Literal["wrong_key", "two_answers", "unclear", "typo", "offensive", "other"]
    comment: str = ""


class CrowdStats(BaseModel):
    attempts: int = 0
    tally: dict[str, int] = Field(default_factory=dict)
    # Among learners rated above the item: their most chosen option and its share.
    strong_top_choice: str | None = None
    strong_top_share: float | None = None


class ReviewRequest(BaseModel):
    question: Question
    flags: list[Flag] = Field(default_factory=list)
    crowd: CrowdStats = Field(default_factory=CrowdStats)
    level: LevelId = "gmat"
    capability_policy: CapabilityPolicy | None = None


class ReviewDecision(BaseModel):
    verdict: Literal["keep", "revise", "retire"]
    findings: list[str]
    revision_guidance: str


class ReviewResult(BaseModel):
    decision: ReviewDecision
    judge: JudgeResult | None = None
    revised: VerifiedQuestion | None = None
    capability_policy: dict | None = None


# ------------------------------------------------------------- Error log (photo → diagnosis)

MechanismFamily = Literal["knowledge", "generalization", "attention", "logic", "scope_language", "processing", "metacognitive"]


class PatternObservation(BaseModel):
    """Abstract design of a question. Must never contain the source's wording, names or numbers."""

    family: QuestionType
    subtype: str
    competency: str = Field(..., description="What the question measures, in general terms")
    stimulus_features: list[str] = Field(..., description="Structural features of the passage, not its content")
    key_rule: str = Field(..., description="What makes the correct answer correct, in general terms")
    distractor_traps: list[TrapType]
    difficulty_drivers: list[str]
    stated_level: str = Field("", description="Level the material targets, if evident (e.g. graduate admissions)")


class MisconceptionGuess(BaseModel):
    mechanism_family: MechanismFamily
    mechanism_type: str = Field(..., description="e.g. necessary_vs_sufficient, scope_shift, keyword_matching")
    statement: str = Field(..., description="What the learner likely believed or did, in one sentence")


class OptionReview(BaseModel):
    label: Label
    trap: TrapType = Field(..., description='"correct" for the key; otherwise the trap this option sets')
    reason: str = Field(..., description="Why this option is right or wrong, in your own words, under 30 words, no quotes")


DifficultyLevel = Literal[1, 2, 3, 4, 5]


class SourceQuestion(BaseModel):
    """The photographed question word for word. It goes back once to the learner who photographed it,
    so they can solve it again on their own device; Questionize never stores it."""

    passage: str = Field(..., description="The passage or argument exactly as printed; empty if there is none")
    stem: str = Field(..., description="The question being asked, exactly as printed")
    choices: list[Choice] = Field(..., min_length=2, max_length=5, description="Every answer option, exactly as printed")
    local_reference: dict | None = Field(None, description="Private reference material returned only to the owner's device; never included in blind solving")

    def text(self) -> str:
        return "\n".join([self.passage, self.stem, *(f"({c.label}) {c.text}" for c in self.choices)])


class PhotoReading(BaseModel):
    readable: bool
    kind: Literal["practice_question", "live_exam_suspected", "not_a_question"]
    personal_data_present: bool = Field(..., description="Names, handwriting identifying a person, school or ID details")
    question: "SourceQuestion" = Field(..., description="The question exactly as printed, for the learner's own device")
    key_guess: Label | None = Field(None, description="Your own answer to the question")
    pattern: PatternObservation
    chosen_trap: TrapType | None = Field(None, description="The trap the learner's chosen option sets, if they chose wrong")
    misconception: MisconceptionGuess | None = None
    explanation: str = Field(..., description="Why the key is right and the chosen option is not, in your own words, no quotes")
    difficulty: DifficultyLevel = Field(..., description="1 = easy warm-up, 3 = typical test item, 5 = among the hardest on the real test")
    intent: str = Field(..., description="What the question writer set out to test, in one sentence of general terms")
    learning_objectives: list[str] = Field(..., min_length=1, max_length=3, description="Skills to practice, each starting with a verb")
    option_reviews: list[OptionReview] = Field(default_factory=list, description="One review per option A-E")


class FlatPhotoReading(BaseModel):
    """What the reader model returns: PhotoReading with every nested object flattened into plain fields.
    Muse's structured output breaks on arrays of objects (and on nested objects in long replies), while
    flat string fields come back clean. Converted to PhotoReading on validation."""

    readable: bool
    kind: Literal["practice_question", "live_exam_suspected", "not_a_question"]
    personal_data_present: bool = Field(False, description="Names, handwriting identifying a person, school or ID details")
    passage: str = Field("", description="The passage or argument exactly as printed; empty if there is none")
    stem: str = Field("", description="The question being asked, exactly as printed")
    option_a: str = Field("", description="Option A exactly as printed")
    option_b: str = ""
    option_c: str = ""
    option_d: str = ""
    option_e: str = ""
    key_guess: Label | None = Field(None, description="Your own answer to the question")
    family: QuestionType = "CR"
    subtype: str = ""
    competency: str = Field("", description="What the question measures, in general terms")
    stimulus_features: list[str] = Field(default_factory=list, description="Structural features of the passage, not its content")
    key_rule: str = Field("", description="What makes the correct answer correct, in general terms")
    distractor_traps: list[str] = Field(default_factory=list)
    difficulty_drivers: list[str] = Field(default_factory=list)
    stated_level: str = ""
    chosen_trap: str = Field("", description="The trap the learner's chosen option sets, if they chose wrong")
    misconception_family: str = Field("", description="knowledge, generalization, attention, logic, scope_language, processing or metacognitive")
    misconception_type: str = Field("", description="e.g. necessary_vs_sufficient, scope_shift, keyword_matching")
    misconception_statement: str = Field("", description="What the learner likely believed or did, in one sentence")
    explanation: str = Field("", description="Why the key is right and the chosen option is not, in your own words, no quotes")
    difficulty: int = Field(3, ge=1, le=5, description="1 = easy warm-up, 3 = typical test item, 5 = among the hardest on the real test")
    intent: str = Field("", description="What the question writer set out to test, in one sentence of general terms")
    learning_objectives: list[str] = Field(default_factory=list, description="One to three skills to practice, each starting with a verb")
    trap_a: str = Field("", description='"correct" for the key; otherwise the trap option A sets')
    trap_b: str = ""
    trap_c: str = ""
    trap_d: str = ""
    trap_e: str = ""
    review_a: str = Field("", description="Why option A is right or wrong, in your own words, under 30 words, no quotes")
    review_b: str = ""
    review_c: str = ""
    review_d: str = ""
    review_e: str = ""
    model_failure_kind: str = ""
    model_failure_lesson: str = ""

    _reading: PhotoReading | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _convert(self) -> FlatPhotoReading:
        self._reading = self._to_reading()
        return self

    @property
    def reading(self) -> PhotoReading:
        assert self._reading is not None
        return self._reading

    def _to_reading(self) -> PhotoReading:
        traps = set(get_args(TrapType))
        options = [(label, getattr(self, f"option_{label.lower()}").strip()) for label in LABELS]
        usable = self.readable and self.kind == "practice_question"
        choices = [Choice(label=label, text=text) for label, text in options if text]
        if usable and len(choices) < 2:
            raise ValueError("a readable practice question needs option_a, option_b, … filled in")
        misconception = None
        if self.misconception_type.strip() and self.misconception_family in get_args(MechanismFamily):
            misconception = MisconceptionGuess(
                mechanism_family=self.misconception_family, mechanism_type=self.misconception_type, statement=self.misconception_statement
            )
        reviews = [
            OptionReview(label=label, trap=getattr(self, f"trap_{label.lower()}").strip().lower(), reason=getattr(self, f"review_{label.lower()}"))
            for label in LABELS
            if getattr(self, f"trap_{label.lower()}").strip().lower() in traps and getattr(self, f"review_{label.lower()}").strip()
        ]
        return PhotoReading(
            readable=self.readable,
            kind=self.kind,
            personal_data_present=self.personal_data_present,
            question=SourceQuestion(passage=self.passage, stem=self.stem, choices=choices or [Choice(label="A", text="-"), Choice(label="B", text="-")]),
            key_guess=self.key_guess,
            pattern=PatternObservation(
                family=self.family, subtype=self.subtype or "unknown", competency=self.competency, stimulus_features=self.stimulus_features,
                key_rule=self.key_rule, distractor_traps=[t for t in self.distractor_traps if t in traps],
                difficulty_drivers=self.difficulty_drivers, stated_level=self.stated_level,
            ),
            chosen_trap=self.chosen_trap.strip().lower() if self.chosen_trap.strip().lower() in traps else None,
            misconception=misconception,
            explanation=self.explanation,
            difficulty=self.difficulty,
            intent=self.intent,
            learning_objectives=[o for o in self.learning_objectives if o.strip()][:3] or ([self.intent] if usable and self.intent else ["Review this question type"]),
            option_reviews=reviews,
        )

    @classmethod
    def from_reading(cls, r: PhotoReading) -> FlatPhotoReading:
        """The flat form of a reading (tests and fixtures)."""
        data: dict = {
            "readable": r.readable, "kind": r.kind, "personal_data_present": r.personal_data_present,
            "passage": r.question.passage, "stem": r.question.stem, "key_guess": r.key_guess,
            "family": r.pattern.family, "subtype": r.pattern.subtype, "competency": r.pattern.competency,
            "stimulus_features": r.pattern.stimulus_features, "key_rule": r.pattern.key_rule,
            "distractor_traps": list(r.pattern.distractor_traps), "difficulty_drivers": r.pattern.difficulty_drivers,
            "stated_level": r.pattern.stated_level, "chosen_trap": r.chosen_trap or "", "explanation": r.explanation,
            "difficulty": r.difficulty, "intent": r.intent, "learning_objectives": r.learning_objectives,
        }
        for c in r.question.choices:
            data[f"option_{c.label.lower()}"] = c.text
        if r.misconception:
            data |= {"misconception_family": r.misconception.mechanism_family, "misconception_type": r.misconception.mechanism_type,
                     "misconception_statement": r.misconception.statement}
        for o in r.option_reviews:
            data[f"trap_{o.label.lower()}"], data[f"review_{o.label.lower()}"] = o.trap, o.reason
        return cls.model_validate(data)


class DiagnoseRequest(BaseModel):
    images: list[str] = Field(..., min_length=1, max_length=3, description="data: URLs of the parts of one question, in reading order")
    chosen_label: Label | None = None
    # The answer from the book's key, if the learner entered it. Checked, not trusted blindly: the
    # learner may have mistyped it, and our own reading may be wrong.
    answer_key: Label | None = None
    level: LevelId = "gmat"
    # 0 for curated items that are only learned from (docs/DECISIONS.md R3).
    practice_count: int = Field(2, ge=0, le=2)
    capability_policy: CapabilityPolicy | None = None
    upload_learning: bool = False
    learning_policy: LearningMemory | None = None
    control_policy: LearningMemory | None = None
    source_attested: bool = False


class KeyReview(BaseModel):
    """A second look when the book's key and our answer disagree."""

    book_key_defensible: bool = Field(..., description="The book's answer can be defended as the single best answer")
    reasoning: str = Field(..., description="Why, in under 80 words, without quoting the question")


class KeyCheck(BaseModel):
    provided: Label | None
    first_reading: Label | None
    solver_answer: Label | None = None
    verdict: Literal["unchecked", "agrees", "upheld", "disputed"]
    note: str = ""


class PracticeRequest(BaseModel):
    """New practice questions from an abstract design, for one level (a snapped question's design
    re-pitched for other levels, or a hand-written seed design)."""

    design: PatternObservation
    practice_trap: TrapType | None = None
    level: LevelId = "gmat"
    count: int = Field(1, ge=1, le=3)
    capability_policy: CapabilityPolicy | None = None


class Diagnosis(BaseModel):
    family: QuestionType
    subtype: str
    competency: str
    key_guess: Label | None
    chosen_label: Label | None
    chosen_correct: bool | None
    chosen_trap: TrapType | None
    misconception: MisconceptionGuess | None
    explanation: str
    difficulty: DifficultyLevel
    difficulty_drivers: list[str]
    intent: str
    learning_objectives: list[str]
    option_reviews: list[OptionReview]
    key_check: KeyCheck | None = None
