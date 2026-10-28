// Shapes of the Rails API (api/app/controllers/api/v1, api/app/serializers/item_payload.rb).
import type { Choice, Label, QuestionType, TrapType, Verification } from "./types";

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
}

export type Item = HiddenItem | RevealedItem;

export interface DeviceResponse {
  token: string;
  user: { handle: string; xp: number };
}

export type GenerationResponse =
  | { status: "cached"; items: Item[] }
  | { status: "queued"; run_id: number };

export interface AttemptResponse {
  correct: boolean;
  rated: boolean;
  rating_changes: Record<string, { before: number; after: number }>;
  xp_awarded: number;
  item: RevealedItem;
}

/** Broadcast on GenerationChannel; mirrors the AI stream with items stored and hidden. */
export type GenerationEvent =
  | { stage: "analyze" | "plan" | "write" | "solve" | "critic" | "revise" | "error"; message: string; index?: number; attempt?: number }
  | { stage: "verdict"; index: number; attempt: number; passed: boolean; message: string }
  | { stage: "analyzed"; message: string; content_flags: string[] }
  | { stage: "question"; index: number; item: HiddenItem }
  | { stage: "done"; count: number }
  | { stage: "declined"; reason: string; message: string }
  | { stage: "failed"; message: string };
