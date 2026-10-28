// Shapes of the Rails API (api/app/controllers/api/v1, api/app/serializers/item_payload.rb).
import type { Choice, JudgeResult, Label, LevelId, QuestionType, Scene, TrapType, Verification } from "./types";

export interface ItemSource {
  title: string | null;
  domain: string | null;
  url: string;
}

interface ItemBase {
  id: string;
  family: QuestionType;
  subtype: string;
  verified: boolean;
  status: "verified" | "unverified" | "flagged" | "under_review" | "retired";
  /** Increases when a re-review replaces the item with a revised version. */
  version: number;
  passage: string;
  stem: string;
  choices: Choice[];
  skill: string | null;
  attempts_count: number;
  source: ItemSource | null;
  /** "generated" from an article; "pattern" from the abstract design of a question someone snapped. */
  origin?: "generated" | "pattern";
  level?: LevelId;
  scene?: Scene | null;
  /** On this learner's review list (My misses), and why. */
  saved?: { reason: "missed" | "saved"; archived: boolean } | null;
}

export interface Votes {
  up: number;
  down: number;
  mine: "up" | "down" | null;
}

/** Before the user has attempted the item: no key, explanations or tallies. */
export interface HiddenItem extends ItemBase {
  revealed: false;
}

export interface RevealedItem extends ItemBase {
  revealed: true;
  correct_label: Label;
  explanation: string;
  rationales: { label: Label; rationale: string; trap: TrapType }[];
  source_anchor: string | null;
  tally: Record<Label, number>;
  correct_rate: number | null;
  verification: Verification;
  /** Per-option Argument Judge measurements; null for items generated without the judge. */
  judge: (Omit<JudgeResult, "options"> & { options: { label: Label; support_delta?: Measurement; necessity?: Measurement }[] }) | null;
  votes?: Votes;
}

type Measurement = JudgeResult["options"][number]["support_delta"];

export type Item = HiddenItem | RevealedItem;

export type FlagReason = "wrong_key" | "two_answers" | "unclear" | "typo" | "offensive" | "other";

export interface FeedbackResponse {
  recorded: "up" | "down" | "flag";
  review_started: boolean;
  votes?: Votes;
}

/** One card on the review list: a question the learner snapped, or a bank item they missed or saved. */
export type ReviewCard =
  | { kind: "snap"; at: string; entry: ErrorLogEntry }
  | { kind: "item"; at: string; reason: "missed" | "saved"; item: Item };

export interface FeedPage {
  items: Item[];
  /** Pass as `before` for the next page; null on the last page. */
  next: string | null;
}

export interface Me {
  handle: string;
  anonymous: boolean;
  xp: number;
  /** The sign-in account linked to this learner, if any. */
  account?: { provider: "facebook"; name: string | null } | null;
  /** Who the learner studies as; null until they choose. */
  level?: LevelId | null;
  ratings: { skill: string; rating: number; attempts: number; correct: number; provisional: boolean }[];
}

export interface TallyUpdate {
  item_id: string;
  tally: Record<Label, number>;
  attempts_count: number;
}

export interface DeviceResponse {
  token: string;
  user: { handle: string; xp: number };
}

export type GenerationResponse =
  | { status: "cached"; items: Item[] }
  | { status: "queued"; run_id: number };

/** GET /api/v1/generations/:id — what a run has produced so far, for catching up after (re)connecting. */
export interface GenerationRunState {
  run_id: number;
  status: "queued" | "running" | "completed" | "declined" | "failed";
  /** Stored copies of the broadcast events; "question" events carry item_id instead of the item. */
  events: (Exclude<GenerationEvent, { stage: "question" }> | { stage: "question"; index: number; item_id: string })[];
  items: Item[];
}

export interface AttemptResponse {
  correct: boolean;
  rated: boolean;
  rating_changes: Record<string, { before: number; after: number }>;
  xp_awarded: number;
  item: RevealedItem;
}

/** Broadcast on GenerationChannel; mirrors the AI stream with items stored and hidden. */
export type GenerationEvent =
  | { stage: "analyze" | "mapping" | "plan" | "write" | "solve" | "critic" | "judge" | "revise" | "error"; message: string; index?: number; attempt?: number }
  | { stage: "verdict"; index: number; attempt: number; passed: boolean; message: string; judge?: { verdict: string; measure: string | null; margin: number; key_first_rate: number } }
  | { stage: "analyzed"; message: string; content_flags: string[] }
  | { stage: "question"; index: number; item: HiddenItem }
  | { stage: "map"; map: ArgumentMapPayload }
  | { stage: "reading" | "practice"; message: string }
  | { stage: "diagnosed"; message: string; competency?: string; family?: string; subtype?: string; difficulty?: number; key_guess?: Label | null; chosen_correct?: boolean | null }
  | { stage: "diagnosis"; entry: ErrorLogEntry; question_ready?: boolean }
  | { stage: "done"; count: number }
  | { stage: "declined"; reason: string; message: string }
  | { stage: "failed"; message: string };

// ------------------------------------------------------------------ Map → Challenge

export interface MapMeasurement {
  value: number;
  ci_low: number;
  ci_high: number;
}

export interface MapElement {
  id: string;
  text: string;
  anchor: string;
  support_delta: MapMeasurement;
  necessity: MapMeasurement;
}

export type ChallengeKind = "weaken" | "assumption" | "strengthen";

export interface ChallengeOption {
  label: Label;
  text: string;
  support_delta?: MapMeasurement;
  necessity?: MapMeasurement;
}

export interface MapChallenge {
  index: number;
  kind: ChallengeKind;
  question: string;
  options: ChallengeOption[];
  chosen: Label | null;
  revealed: boolean;
  judged?: { label: Label; measure: "support_delta" | "necessity"; first_rate: number; margin: number; runner_up: Label };
  crowd?: Record<Label, number>;
}

/** GET /api/v1/maps/:id. Judged answers stay hidden per challenge until the reader answers it. */
export interface ArgumentMapPayload {
  run_id: number;
  reconstruction: true;
  judge_version: string;
  scheme: string;
  conclusion: { text: string; anchor: string };
  premises: MapElement[];
  assumptions: MapElement[];
  largest_gap: string;
  challenges: MapChallenge[];
}

export type MapResponse = { status: "cached"; map: ArgumentMapPayload } | { status: "queued"; run_id: number };

// ------------------------------------------------------------------ Error log

export interface OptionReview {
  label: Label;
  trap: TrapType;
  reason: string;
}

export interface Diagnosis {
  family: string;
  subtype: string;
  competency: string;
  key_guess: Label | null;
  chosen_label: Label | null;
  chosen_correct: boolean | null;
  chosen_trap: string | null;
  misconception: { mechanism_family: string; mechanism_type: string; statement: string } | null;
  explanation: string;
  /** 1 = easy warm-up, 3 = typical, 5 = among the hardest on the real test. Older entries lack these fields. */
  difficulty?: number;
  difficulty_drivers?: string[];
  /** What the question writer set out to test. */
  intent?: string;
  learning_objectives?: string[];
  option_reviews?: OptionReview[];
}

/** One photographed question: where it lives in the learner's own book, our diagnosis, and new practice. */
export interface ErrorLogEntry {
  id: number;
  book: string | null;
  page: string | null;
  number: string | null;
  chosen_label: Label | null;
  diagnosis: Diagnosis;
  /** True when the abstract pattern passed the leak checks and joined the shared knowledge model. */
  contributed: boolean;
  archived?: boolean;
  practice: Item[];
  created_at: string;
}

export interface ErrorLogPage {
  eligible: boolean;
  entries: ErrorLogEntry[];
  weaknesses: { traps: Record<string, number>; misconceptions: Record<string, number> };
}

/** The photographed question word for word. The server hands it to the learner's device once and keeps no copy. */
export interface SourceQuestion {
  passage: string;
  stem: string;
  choices: Choice[];
}

export interface ErrorLogCapture {
  /** One to three parts of one question (e.g. passage and question on different pages), as data: URLs.
   *  The server keeps them only until the question is read. */
  images: string[];
  book?: string;
  page?: string;
  number?: string;
  chosen_label?: Label;
}

export interface Recommendations {
  level: LevelId;
  items: { reason: string; item: Item }[];
}
