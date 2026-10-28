import type { QuestionType, TrapType } from "./types";

export const FAMILY_LABELS: Record<QuestionType, string> = {
  CR: "Critical Reasoning",
  RC: "Reading Comprehension",
  SC: "Sentence Correction",
};

export const TRAP_LABELS: Record<Exclude<TrapType, "correct">, string> = {
  out_of_scope: "Out of scope",
  too_extreme: "Too extreme",
  reversal: "Reversal",
  half_right: "Half right",
  unsupported: "Unsupported",
  irrelevant: "Irrelevant",
  distortion: "Distortion",
  grammar_error: "Grammar error",
  changes_meaning: "Changes meaning",
};

export const MEASURE_LABELS: Record<string, string> = {
  support_delta: "Effect on the conclusion if true",
  necessity: "Argument falls apart without it",
};

export function subtypeLabel(subtype: string): string {
  return subtype.replace(/_/g, " ");
}

/** Splits a passage into plain and [[underlined]] segments, for rendering without HTML. */
export function passageSegments(passage: string): { text: string; underlined: boolean }[] {
  return passage
    .split(/\[\[|\]\]/)
    .map((text, i) => ({ text, underlined: i % 2 === 1 }))
    .filter((s) => s.text);
}
