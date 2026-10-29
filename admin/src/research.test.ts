import { describe, expect, it } from "vitest";
import { comparisonIssues, comparisonView, measurements, validateData, type Measurement, type ResearchData, type Run } from "./research";

const run = (id: string, patch: Partial<Run> = {}): Run => ({ run_id: id, protocol: "E1", protocol_version: 2, started_at: "2026-10-29T19:00:00Z", subject: "CR", scope: "full", n_items: 39, dataset_id: "d", dataset_hash: "data", split: "test", prompts_hash: "prompts", git_sha: "abc", models: { primary: "model" }, judge: { samples: 3 }, memory: null, baseline_run: null, note: "", capabilities: ["C3.1"], measured_capabilities: ["C3.1"], ...patch });
const record = (patch: Partial<Measurement> = {}): Measurement => ({ run_id: "a", capability: "C3.1", subject: "CR", condition: "B0", scope: "full", metric: "accuracy", value: 37 / 39, n: 39, expected_n: 39, complete: true, ci95: [.83, .99], ...patch });

describe("research comparisons", () => {
  it("does not label qualified benchmark evidence as ready for adoption", () => {
    const qualified = run("b", { qualifications: [{ id: "capture", summary: "Required emphasis spans are missing." }] });
    expect(comparisonIssues(run("a"), qualified, record(), record())).toContain("These runs have unresolved data or method qualifications; review the evaluation notes.");
  });
  it("keeps trial, subject and capability measurements separate", () => {
    const data = { records: [record(), record({ scope: "trial", n: 5, value: 1 }), record({ subject: "RC" })] } as ResearchData;
    expect(measurements(data, "CR", "C3.1", "full")).toHaveLength(1);
    expect(measurements(data, "CR", "C3.1", "all")).toHaveLength(2);
    expect(measurements(data, "CR", "C3.2", "all")).toEqual([]);
  });

  it("requires review when a higher score also changes the dataset, code, model or sample", () => {
    const issues = comparisonIssues(run("a"), run("b", { dataset_hash: "other", prompts_hash: "new", models: { primary: "other" }, scope: "trial" }), record(), record({ n: 5, value: 1, complete: false }));
    expect(issues).toContain("Dataset differs between runs.");
    expect(issues).toContain("Prompt/code hash differs between runs.");
    expect(issues).toContain("Models differ between runs.");
    expect(issues).toContain("This comparison includes a trial run.");
    expect(issues).toContain("The evaluated sample sizes differ.");
    expect(issues).toContain("A condition has missing results.");
  });

  it("permits a paired baseline-to-memory comparison with matching recorded controls", () => {
    expect(comparisonIssues(run("a"), run("b", { memory: { hash: "memory", lessons: 48 }, baseline_run: "a" }), record(), record({ run_id: "b", condition: "B0+M" }))).toEqual([]);
  });

  it("requires review across protocols, versions, subjects and measured quantities", () => {
    const issues = comparisonIssues(run("a"), run("b", { protocol: "E2", protocol_version: 3, subject: "RC" }), record(), record({ run_id: "b", subject: "RC", capability: "C3.2", metric: "explanation_correctness" }));
    expect(issues).toContain("Protocol differs between runs.");
    expect(issues).toContain("Protocol versions differ between runs.");
    expect(issues).toContain("Subject differs between runs.");
    expect(issues).toContain("The measured capabilities differ.");
    expect(issues).toContain("The measured metrics differ.");
  });

  it("treats absent comparison controls and denominators as unknown, not matching", () => {
    const unknown = { protocol: "", protocol_version: 0, subject: "", models: {}, judge: {}, n_items: 0 };
    const missing = { metric: "", n: null, expected_n: null, complete: null };
    const issues = comparisonIssues(run("a", unknown), run("b", unknown), record(missing), record({ ...missing, run_id: "b" }));
    expect(issues).toContain("Protocol was not recorded for both runs.");
    expect(issues).toContain("Protocol versions were not recorded for both runs.");
    expect(issues).toContain("Subject was not recorded for both runs.");
    expect(issues).toContain("Models were not recorded for both runs.");
    expect(issues).toContain("Judge settings were not recorded for both runs.");
    expect(issues).toContain("Expected run sample sizes were not recorded for both runs.");
    expect(issues).toContain("The metric was not recorded for both conditions.");
    expect(issues).toContain("Evaluated sample sizes were not recorded for both conditions.");
    expect(issues).toContain("Expected condition sample sizes were not recorded for both conditions.");
    expect(issues).toContain("Condition completeness was not recorded for both conditions.");
  });

  it("does not trust a complete flag when actual and expected denominators disagree", () => {
    const issues = comparisonIssues(run("a"), run("b"), record(), record({ run_id: "b", n: 38, complete: true }));
    expect(issues).toContain("A condition has missing results.");
    expect(comparisonIssues(run("a"), run("b"), record())).toContain("A condition measurement was not recorded for both runs.");
  });

  it("keeps measurement provenance attached to its selected run", () => {
    const issues = comparisonIssues(run("a"), run("b"), record(), record());
    expect(issues).toContain("A measurement's run ID does not match the selected run.");
  });

  it("uses the recorded five-item baseline subset rather than subtracting the 39-item baseline", () => {
    const before = run("a");
    const after = run("b", { scope: "trial", n_items: 5, baseline_run: "a", memory: { hash: "memory", lessons: 48 } });
    const right = record({ run_id: "b", scope: "trial", condition: "B0+M", n: 5, expected_n: 5, value: 1,
      vs_baseline: { baseline_accuracy: 1, b: 0, c: 0, p: 1, diff_ci95: [0, 0] } });
    const view = comparisonView(before, after, record(), right);
    expect(view.leftValue).toBe(1);
    expect(view.leftN).toBe(5);
    expect(view.rightN).toBe(5);
    expect(view.baselineTotal).toBe(39);
    expect(view.matchedSubset).toBe(true);
    expect(view.difference).toBe(0);
    expect(view.paired?.diff_ci95).toEqual([0, 0]);
  });

  it("hides aggregate deltas for different sample sizes when a matched baseline is unavailable", () => {
    const after = run("b", { scope: "trial", n_items: 5, baseline_run: "a" });
    const right = record({ run_id: "b", scope: "trial", n: 5, expected_n: 5, value: 1, vs_baseline: { diff_ci95: [0, 0] } });
    const view = comparisonView(run("a"), after, record(), right);
    expect(view.matchedSubset).toBe(false);
    expect(view.difference).toBeNull();
    expect(view.leftValue).toBe(37 / 39);
  });

  it("never substitutes solving baseline accuracy for explanation quality", () => {
    const left = record({ capability: "C3.2", metric: "explanation_correctness", n: 39, value: .8 });
    const right = record({ run_id: "b", capability: "C3.2", metric: "explanation_correctness", condition: "B0+M", n: 5, expected_n: 5, value: 1,
      vs_baseline: { baseline_accuracy: 1, diff_ci95: [0, 0] } });
    const view = comparisonView(run("a"), run("b", { baseline_run: "a" }), left, right);
    expect(view.paired).toBeUndefined();
    expect(view.matchedSubset).toBe(false);
    expect(view.leftValue).toBe(.8);
    expect(view.difference).toBeNull();
  });

  it("rejects unrecognized exports instead of showing empty evidence", () => {
    expect(() => validateData({ schema_version: 99 })).toThrow("Unsupported research data");
    expect(() => validateData(null)).toThrow("Unsupported research data");
  });
});
