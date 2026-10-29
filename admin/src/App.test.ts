import { afterEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import App from "./App.vue";
import type { ResearchData } from "./research";

const data: ResearchData = {
  schema_version: 1, updated_at: "2026-10-29T19:17:08Z", subjects: ["CR"],
  capabilities: [
    { id: "C3.1", name: "Solve", bar: "accuracy ≥ 95%", metric: "accuracy", unit: "ratio", direction: "higher" },
    { id: "C3.2", name: "Explain", bar: "correct explanations ≥ 90%", metric: "explanation_correctness", unit: "ratio", direction: "higher" },
    { id: "C5", name: "Write practice", bar: "verification pass rate", metric: "first_draft_pass_rate", unit: "ratio", direction: "higher" },
  ],
  runs: [{ run_id: "test-baseline", protocol: "E1", protocol_version: 2, started_at: "2026-10-29T19:17:08Z", subject: "CR", scope: "full", n_items: 39, dataset_id: "d", dataset_hash: "d", split: "test", prompts_hash: "p", git_sha: "abc", models: { primary: "m" }, judge: {}, memory: null, baseline_run: null, note: "baseline", capabilities: ["C3.1", "C3.2"], measured_capabilities: ["C3.1"] }],
  records: [{ run_id: "test-baseline", capability: "C3.1", subject: "CR", condition: "B0", scope: "full", metric: "accuracy", value: .9487, n: 39, expected_n: 39, complete: true, ci95: [.8311, .9858], calls: 39, ece: .0364 }],
};

describe("Research console", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows the measured solve score and an unmeasured state for explanations and generation", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => data }));
    const wrapper = mount(App);
    await flushPromises();
    expect(wrapper.text()).toContain("94.9%");
    expect(wrapper.text()).toContain("n = 39");
    await wrapper.find('select[aria-label="Measure"]').setValue("C3.2");
    expect(wrapper.text()).toContain("No measurements yet");
    expect(wrapper.text()).not.toContain("94.9%");
    await wrapper.findAll(".nav-item")[4].trigger("click");
    expect(wrapper.text()).toContain("Write practice has no full results");
    expect(wrapper.find(".provenance .run-id").exists()).toBe(false);
    expect(wrapper.find('select[aria-label="Before run"]').findAll("option")).toHaveLength(0);
    expect(wrapper.find(".tabs").exists()).toBe(false);
    expect(wrapper.findAll("select").map((select) => select.attributes("aria-label"))).toEqual([
      "Subject", "Measure", "Evaluation scope", "Result condition", "Before run", "After run", "Comparison condition",
    ]);
    wrapper.unmount();
  });

  it("clears another subject's run provenance when the selected scope has no runs", async () => {
    const payload = structuredClone(data);
    payload.subjects.push("RC");
    payload.runs.push({ ...payload.runs[0], run_id: "rc-trial", subject: "RC", scope: "trial", n_items: 5, note: "RC trial" });
    payload.records.push({ ...payload.records[0], run_id: "rc-trial", subject: "RC", scope: "trial", n: 5, expected_n: 5 });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => payload }));
    const wrapper = mount(App);
    await flushPromises();
    expect(wrapper.find(".provenance .run-id").text()).toBe("test-baseline");
    await wrapper.find('select[aria-label="Subject"]').setValue("RC");
    expect(wrapper.find(".provenance .run-id").exists()).toBe(false);
    expect(wrapper.find('select[aria-label="Before run"]').findAll("option")).toHaveLength(0);
    expect(wrapper.find('select[aria-label="After run"]').findAll("option")).toHaveLength(0);
    await wrapper.find('select[aria-label="Evaluation scope"]').setValue("trial");
    expect(wrapper.find(".provenance .run-id").text()).toBe("rc-trial");
    wrapper.unmount();
  });

  it("shows protocol changes as a comparison caution rather than matching controls", async () => {
    const payload = structuredClone(data);
    payload.runs.push({ ...payload.runs[0], run_id: "new-memory", protocol_version: 3, started_at: "2026-10-29T20:00:00Z", baseline_run: "test-baseline", memory: { hash: "memory", lessons: 48 } });
    payload.records.push({ ...payload.records[0], run_id: "new-memory", condition: "B0+M", value: 1 });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => payload }));
    const wrapper = mount(App);
    await flushPromises();
    expect(wrapper.find(".comparison-note").text()).toContain("Review comparison conditions");
    expect(wrapper.find(".comparison-note").text()).toContain("Protocol versions differ between runs.");
    expect(wrapper.find(".comparison-note").text()).not.toContain("Recorded settings match");
    wrapper.unmount();
  });

  it("compares the same five items when a memory trial is paired with the 39-item baseline", async () => {
    const payload = structuredClone(data);
    payload.runs.push({ ...payload.runs[0], run_id: "memory-trial", scope: "trial", n_items: 5,
      started_at: "2026-10-29T20:01:38Z", baseline_run: "test-baseline", memory: { hash: "memory", lessons: 48 } });
    payload.records.push({ ...payload.records[0], run_id: "memory-trial", scope: "trial", condition: "B0+M",
      n: 5, expected_n: 5, value: 1, ci95: [.5655, 1], vs_baseline: { baseline_accuracy: 1, b: 0, c: 0, p: 1, diff_ci95: [0, 0] } });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => payload }));
    const wrapper = mount(App);
    await flushPromises();
    await wrapper.find('select[aria-label="Evaluation scope"]').setValue("all");
    await wrapper.find('select[aria-label="After run"]').setValue("memory-trial");
    await wrapper.find('select[aria-label="Before run"]').setValue("test-baseline");
    const panel = wrapper.find(".comparison");
    expect(panel.find(".matched-subset").text()).toContain("Matched subset of baseline run (5 of 39)");
    expect(panel.find(".compare-values").text()).not.toContain("94.9%");
    expect(panel.findAll(".compare-values > div > strong").slice(0, 2).map((value) => value.text())).toEqual(["100.0%", "100.0%"]);
    expect(panel.findAll(".compare-values > div > span").map((value) => value.text())).toEqual(["n = 5", "n = 5"]);
    expect(panel.find(".delta").text()).toContain("0.00 pp");
    expect(panel.text()).not.toContain("5.13");
    expect(panel.text()).toContain("Recorded paired 95% CI: 0.00 to 0.00 pp");
    expect(panel.text()).toContain("This comparison includes a trial run.");
    wrapper.unmount();
  });
});
