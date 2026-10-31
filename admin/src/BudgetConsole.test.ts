import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, it, vi } from "vitest";
import BudgetConsole from "./BudgetConsole.vue";
import type { BudgetCondition, BudgetStudy } from "./research";

afterEach(() => vi.unstubAllGlobals());
const condition: BudgetCondition = { n: 10, correct: 9, accuracy: .9, ci95: [.6, .98], errors: 0, calls: 10,
  normalised_usd: .1, estimated_billed_usd: .08, input_tokens: 1000, output_tokens: 2000, reasoning_tokens: 1500,
  cached_tokens: 100, mean_seconds: 3, usage_complete: true, budget_violations: 0 };
const study: BudgetStudy = { run_id: "e14-example", started_at: "2026-10-30T00:00:00Z", model: "muse-spark-1.3", reasoning_effort: "medium",
  envelope_usd: .03, decision: "held", candidate_deployed: false, cost_comparison_valid: true,
  split: { counts: { train: 70, development: 54, test: 10, held: 0 }, groups: { train: 70, development: 54, test: 10, held: 0 },
    membership_hashes: { train: "train-hash", development: "dev-hash", test: "test-hash", held: "held-hash" }, cross_partition_group_overlap: 0 },
  conditions: { A: condition, M: { ...condition, vs_baseline: { b: 1, c: 1, p: 1, difference: 0, diff_ci95: [-.2, .2] } }, MV: condition },
  diagnostics: { rescue: 1, harm: 2, both_wrong: 1, operational_error: 0 }, slices: { weaken: { n: 10, A: 9, M: 9, MV: 9 } },
  training_normalised_usd: .2, training_estimated_billed_usd: .1, training_calls: 8, training_failures: 0, procedure_count: 8,
  memory_hash: "memory-hash", manifest_hash: "manifest-hash", runner_hash: "runner-hash", client_hash: "client-hash",
  report_path: "research/results/E14.md", protocol_path: "research/protocols/E14-budget-matched-reasoning.md",
  rates: { input: 1.25, output: 4.25, cached_input: .15 }, price_url: "https://dev.meta.ai/docs/pricing-rate-limits", price_reviewed: "2026-10-30" };

it("does not present an unfinished study as a result", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
  const wrapper = mount(BudgetConsole);
  await flushPromises();
  expect(wrapper.text()).toContain("No completed budget comparison has been published");
  expect(wrapper.find("table").exists()).toBe(false);
  wrapper.unmount();
});

it("shows held evidence, verifier harm, separate live version and unequal actual expenditure", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ active_memory: { version: 1 }, runtime: "gmat-upload-learning-2" }) }));
  const wrapper = mount(BudgetConsole, { props: { studies: [study] } });
  await flushPromises();
  expect(wrapper.text()).toContain("Held — improvement not established");
  expect(wrapper.text()).toContain("actual expenditure can differ");
  expect(wrapper.text()).toContain("replaced it with a wrong answer");
  expect(wrapper.text()).toContain("Live service memory: v1");
  expect(wrapper.text()).toContain("Research candidate deployed: No");
  expect(wrapper.text()).toContain("not human-certified correctness");
  expect(wrapper.text()).toContain("test-hash");
  wrapper.unmount();
});

it("blocks a valid cost-match claim when usage is missing", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
  const wrapper = mount(BudgetConsole, { props: { studies: [{ ...study, cost_comparison_valid: false }] } });
  await flushPromises();
  expect(wrapper.get('[role="alert"]').text()).toContain("Do not interpret this run as a valid cost-matched comparison");
  expect(wrapper.text()).toContain("Live service version is not currently observed");
  wrapper.unmount();
});
