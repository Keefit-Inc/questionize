// Shapes of the Rails API (api/app/controllers/api/v1, api/app/serializers/item_payload.rb).
import type { Choice, JudgeResult, Label, QuestionType, TrapType, Verification } from "./types";

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
  passage: string;
  stem: string;
  choices: Choice[];
  skill: string | null;
  attempts_count: number;
  source: ItemSource | null;
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
}

type Measurement = JudgeResult["options"][number]["support_delta"];

export type Item = HiddenItem | RevealedItem;

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
