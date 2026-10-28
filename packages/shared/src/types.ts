// Mirrors ai/questionize/schemas.py. Keep the two in sync.

export type QuestionType = "RC" | "CR" | "SC";
export type Difficulty = "easy" | "medium" | "hard";
export type Label = "A" | "B" | "C" | "D" | "E";
export const LABELS: readonly Label[] = ["A", "B", "C", "D", "E"];

export type TrapType =
  | "correct"
  | "out_of_scope"
  | "too_extreme"
  | "reversal"
  | "half_right"
  | "unsupported"
  | "irrelevant"
  | "distortion"
  | "grammar_error"
  | "changes_meaning";

export type Suitability =
  | "suitable"
  | "too_thin"
  | "not_an_article"
  | "exam_material"
  | "harmful"
  | "private";

export type ContentFlag =
  | "sexual_violence"
  | "self_harm"
  | "graphic_violence"
  | "harm_to_minors"
  | "hate_or_harassment"
  | "explicit_sexual_content";

export interface Choice {
  label: Label;
  text: string;
}

export interface ChoiceRationale {
  label: Label;
  rationale: string;
  trap: TrapType;
}

export interface Question {
  type: QuestionType;
  subtype: string;
  passage: string;
  stem: string;
  choices: Choice[];
  correct_label: Label;
  explanation: string;
  choice_rationales: ChoiceRationale[];
  skill: string;
  source_anchor: string;
}

export interface Verification {
  verified: boolean;
  attempts: number;
  solver_model: string;
  solver_answer: string;
  solver_confidence: number;
  critic_verdict: string;
  distractor_quality: number;
  issues: string[];
  copied_words: number;
}

export interface VerifiedQuestion {
  id: string;
  question: Question;
  verification: Verification;
}

export interface Argument {
  conclusion: string;
  premises: string[];
  unstated_assumptions: string[];
  potential_flaws: string[];
}

export interface ArticleAnalysis {
  suitability: Suitability;
  suitability_reason: string;
  main_point: string;
  author_purpose: string;
  reading_level: Difficulty;
  arguments: Argument[];
  rc_focus_points: string[];
  sc_candidate_sentences: string[];
  content_flags: ContentFlag[];
}

export interface GenerateResult {
  analysis: ArticleAnalysis;
  questions: VerifiedQuestion[];
}

/** One line of the /v1/generate NDJSON stream. */
export type AgentEvent =
  | { stage: "analyze"; message: string }
  | { stage: "analyzed"; message: string; analysis: ArticleAnalysis }
  | { stage: "plan"; message: string; slots: [QuestionType, string][] }
  | { stage: "write" | "solve" | "critic" | "revise"; index: number; attempt?: number; message: string }
  | {
      stage: "verdict";
      index: number;
      attempt: number;
      passed: boolean;
      // Absent when the passage was sent back for copying article text before the solver ran.
      solver_answer?: Label;
      intended_answer?: Label;
      message: string;
    }
  | { stage: "question"; index: number; question: VerifiedQuestion }
  | { stage: "error"; index: number; message: string }
  | { stage: "done"; result: GenerateResult }
  | { stage: "declined"; reason: Exclude<Suitability, "suitable">; message: string }
  | { stage: "failed"; message: string };
