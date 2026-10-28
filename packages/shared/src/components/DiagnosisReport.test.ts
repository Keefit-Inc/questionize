import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import DiagnosisReport from "./DiagnosisReport.vue";
import type { ErrorLogEntry } from "../api";

const entry: ErrorLogEntry = {
  id: 7,
  book: "Workbook",
  page: "42",
  number: "7",
  chosen_label: "A",
  contributed: true,
  practice: [],
  created_at: "2026-10-28T00:00:00Z",
  diagnosis: {
    family: "CR",
    subtype: "weaken",
    competency: "Spot an alternative cause",
    key_guess: "C",
    chosen_label: "A",
    chosen_correct: false,
    chosen_trap: "irrelevant",
    misconception: { mechanism_family: "attention", mechanism_type: "keyword_matching", statement: "Picked the <b>on-topic</b> option" },
    explanation: "C names another cause.",
    difficulty: 4,
    difficulty_drivers: ["the rival cause is indirect"],
    intent: "Tests whether you look for a rival explanation",
    learning_objectives: ["Separate a correlation from its cause"],
    option_reviews: (["A", "B", "C", "D", "E"] as const).map((label) => ({ label, trap: label === "C" ? "correct" : "irrelevant", reason: `Reason ${label}` })),
  },
};

describe("DiagnosisReport", () => {
  it("shows the verdict, difficulty, intent, objectives and every option", () => {
    const text = mount(DiagnosisReport, { props: { entry } }).text();
    expect(text).toContain("Workbook · p. 42 · #7");
    expect(text).toContain("You chose A · the answer is most likely C");
    expect(text).toContain("4/5");
    expect(text).toContain("Harder than average");
    expect(text).toContain("Tests whether you look for a rival explanation");
    expect(text).toContain("Separate a correlation from its cause");
    expect(text).toContain("Why A was tempting");
    expect((text.match(/Reason [A-E]/g) ?? []).length).toBe(5);
  });

  it("renders model text as text, never HTML", () => {
    const wrapper = mount(DiagnosisReport, { props: { entry } });
    expect(wrapper.find("b").exists()).toBe(false);
    expect(wrapper.text()).toContain("<b>on-topic</b>");
  });

  it("copes with entries recorded before the extended analysis", () => {
    const { difficulty, intent, learning_objectives, option_reviews, ...older } = entry.diagnosis;
    void [difficulty, intent, learning_objectives, option_reviews];
    const text = mount(DiagnosisReport, { props: { entry: { ...entry, diagnosis: older } } }).text();
    expect(text).toContain("C names another cause.");
    expect(text).not.toContain("Difficulty");
  });
});
