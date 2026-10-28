import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import QuestionCard from "./QuestionCard.vue";
import type { HiddenItem, RevealedItem } from "../api";

const labels = ["A", "B", "C", "D", "E"] as const;

const hidden: HiddenItem = {
  id: "abc123",
  family: "CR",
  subtype: "weaken",
  verified: true,
  status: "verified",
  version: 1,
  passage: "Accidents fell after bike lanes, so <b>lanes</b> make streets [[safer]].",
  stem: "Which most weakens the argument?",
  choices: labels.map((label) => ({ label, text: `Option ${label}` })),
  skill: "Alternative causes",
  attempts_count: 3,
  source: { title: "Story", domain: "example.com", url: "https://example.com/story" },
  revealed: false,
};

const revealed: RevealedItem = {
  ...hidden,
  revealed: true,
  correct_label: "B",
  explanation: "B names an alternative cause.",
  rationales: labels.map((label) => ({ label, rationale: `Why ${label}`, trap: label === "B" ? "correct" : "too_extreme" })),
  source_anchor: "accidents fell",
  tally: { A: 1, B: 2, C: 0, D: 1, E: 0 },
  correct_rate: 0.5,
  verification: { verified: true, attempts: 1, solver_model: "solver", solver_answer: "B", solver_confidence: 0.9, critic_verdict: "pass", distractor_quality: 4, issues: [], copied_words: 2 },
  judge: {
    judge_version: "aj-0.1:m",
    measure: "support_delta",
    direction: "min",
    verdict: "pass",
    margin: 0.42,
    key_first_rate: 1,
    runner_up: "D",
    judges: ["m"],
    samples: 6,
    options: labels.map((label) => ({
      label,
      support_delta: { value: label === "B" ? -0.6 : -0.1, ci_low: -0.7, ci_high: 0 },
      necessity: { value: 0.2, ci_low: 0.1, ci_high: 0.3 },
    })),
  },
};

describe("QuestionCard", () => {
  it("renders model text as text, never as HTML", () => {
    const wrapper = mount(QuestionCard, { props: { item: hidden } });
    expect(wrapper.find(".qz-passage b").exists()).toBe(false);
    expect(wrapper.find(".qz-passage").text()).toContain("<b>lanes</b>");
    expect(wrapper.find(".qz-passage u").text()).toBe("safer");
  });

  it("emits the picked label and shows no key before an answer", async () => {
    const wrapper = mount(QuestionCard, { props: { item: hidden } });
    expect(wrapper.find(".qz-reveal").exists()).toBe(false);
    await wrapper.findAll(".qz-choices button")[3].trigger("click");
    await wrapper.find(".qz-primary").trigger("click");
    expect(wrapper.emitted("answer")).toEqual([["D"]]);
  });

  it("after an answer shows the verdict with the trap, the judge meter and the crowd", () => {
    const wrapper = mount(QuestionCard, { props: { item: revealed, chosen: "D" } });
    expect(wrapper.find(".qz-verdict").text()).toContain("You chose D (trap: Too extreme); the answer is B");
    expect(wrapper.find(".qz-judge").text()).toContain("Key leads D by 0.42");
    expect(wrapper.findAll(".qz-judge-row")).toHaveLength(5);
    expect(wrapper.find(".qz-dist").text()).toContain("50%");
    expect(wrapper.find("button.correct").text()).toContain("Option B");
    expect(wrapper.find("button.wrong").text()).toContain("Option D");
  });

  it("asks the page to highlight the source anchor", async () => {
    const wrapper = mount(QuestionCard, { props: { item: revealed, chosen: "B" } });
    await wrapper.find(".qz-ghost").trigger("click");
    expect(wrapper.emitted("locate")).toEqual([["accidents fell"]]);
  });

  it("lets a reader report a problem after answering", async () => {
    const wrapper = mount(QuestionCard, { props: { item: { ...revealed, version: 2 }, chosen: "B" } });
    expect(wrapper.find(".qz-tag.revised").text()).toBe("v2 · revised");
    const report = wrapper.findAll("button").find((b) => b.text() === "Report a problem")!;
    await report.trigger("click");
    await wrapper.find(".qz-report select").setValue("wrong_key");
    await wrapper.find(".qz-report textarea").setValue("  D is right  ");
    await wrapper.find(".qz-report").trigger("submit");
    expect(wrapper.emitted("flag")).toEqual([["wrong_key", "D is right"]]);
    expect(wrapper.text()).toContain("automatic re-review");
  });
});
