import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import ChallengeCard from "./ChallengeCard.vue";
import ArgumentMap from "./ArgumentMap.vue";
import type { ArgumentMapPayload, MapChallenge } from "../api";

const labels = ["A", "B", "C", "D", "E"] as const;
const m = (value: number) => ({ value, ci_low: value - 0.1, ci_high: value + 0.1 });

const hidden: MapChallenge = {
  index: 0,
  kind: "weaken",
  question: "What would most weaken this?",
  options: labels.map((label) => ({ label, text: `If ${label}` })),
  chosen: null,
  revealed: false,
};

describe("ChallengeCard", () => {
  it("asks for the reader's answer before revealing anything", async () => {
    const wrapper = mount(ChallengeCard, { props: { challenge: hidden } });
    expect(wrapper.find(".qz-result").exists()).toBe(false);
    expect(wrapper.find(".qz-meter").exists()).toBe(false);
    await wrapper.findAll(".qz-opts button")[2].trigger("click");
    await wrapper.find(".qz-primary").trigger("click");
    expect(wrapper.emitted("answer")).toEqual([["C"]]);
  });

  it("shows the judged answer, each option's measurement and the crowd after answering", () => {
    const revealed: MapChallenge = {
      ...hidden,
      chosen: "C",
      revealed: true,
      options: labels.map((label) => ({ label, text: `If ${label}`, support_delta: m(label === "B" ? -0.7 : 0), necessity: m(0.2) })),
      judged: { label: "B", measure: "support_delta", first_rate: 0.95, margin: 0.5, runner_up: "C" },
      crowd: { A: 0, B: 3, C: 1, D: 0, E: 0 },
    };
    const wrapper = mount(ChallengeCard, { props: { challenge: revealed } });
    expect(wrapper.find(".qz-result").text()).toContain("B moves the argument most");
    expect(wrapper.find("button.best").text()).toContain("-0.70 · 75% chose");
    expect(wrapper.find("button.mine").text()).toContain("If C");
  });
});

describe("ArgumentMap", () => {
  it("labels the reconstruction and marks the largest gap", async () => {
    const map: ArgumentMapPayload = {
      run_id: 1,
      reconstruction: true,
      judge_version: "aj-0.1:m",
      scheme: "causal",
      conclusion: { text: "Lanes make streets safer", anchor: "make streets safer" },
      premises: [{ id: "P1", text: "Accidents fell", anchor: "accidents fell", support_delta: m(0.6), necessity: m(0.8) }],
      assumptions: [{ id: "A1", text: "Nothing else changed", anchor: "", support_delta: m(0.5), necessity: m(0.9) }],
      largest_gap: "A1",
      challenges: [],
    };
    const wrapper = mount(ArgumentMap, { props: { map } });
    expect(wrapper.find(".qz-map-note").text()).toContain("AI reconstruction");
    expect(wrapper.find(".qz-node.gap").text()).toContain("largest gap");
    await wrapper.find(".qz-link").trigger("click");
    expect(wrapper.emitted("locate")).toEqual([["make streets safer"]]);
  });
});
