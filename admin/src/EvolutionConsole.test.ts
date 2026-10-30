import { afterEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import EvolutionConsole from "./EvolutionConsole.vue";
import type { EvolutionCycle, EvolutionData, PolicyVersion } from "./evolution";

const policy = (version: number): PolicyVersion => ({ id: `policy-${version}`, version, content_hash: `hash-${version}`, payload: { except_mode: version === 1 ? "legacy" : "abstain" } });
const cycle = (patch: Partial<EvolutionCycle> = {}): EvolutionCycle => ({
  id: "cycle-1", status: "adopted", trigger: "research_replay", created_at: "2026-10-29T23:00:00Z", updated_at: "2026-10-29T23:02:00Z",
  baseline_policy: policy(1), candidate_policy: policy(2),
  benchmark: { id: "development-replay", hash: "benchmark-hash", n: 35, kind: "decision_replay", purpose: "development_regression", parent_dataset_hash: "parent-hash" },
  proposal: { reason: "The Judge ranking direction does not implement the EXCEPT task.", hypothesis: "Abstaining avoids an unsupported override.", model: "muse-spark-1.3", logical_calls: 1, duration_seconds: 2 },
  evaluation: { baseline: { n: 35, correct: 34, accuracy: 34 / 35 }, candidate: { n: 35, correct: 35, accuracy: 1 }, comparison: { gained: 1, lost: 0, delta: 1 / 35, mcnemar_p: 1, diff_ci95: [0, .0857], standard_regressions: 0, except_gained: 1 }, gate: { passed: true, reasons: ["one_case_improved", "no_standard_regressions"] } },
  decision_reasons: ["regression_gate_passed"],
  service_verification: { verified: true, policy_id: "policy-2", policy_hash: "hash-2", chosen_answer: "E", expected_answer: "E", checked_at: "2026-10-29T23:02:00Z" },
  events: [{ stage: "generating", message: "Candidate generated with Meta.", created_at: "2026-10-29T23:01:00Z" }, { stage: "adopted", message: "The release pointer changed after the gate passed.", created_at: "2026-10-29T23:02:00Z" }],
  ...patch,
});
const payload = (cycles: EvolutionCycle[] = [cycle()], curator = false): EvolutionData => ({
  schema_version: 1, scope: { subject: "CR", level: "gmat", capability: "C3.1", policy_kind: "judge_operator" }, active_policy: policy(2),
  automation: { enabled: true, min_trusted_sources: 3, min_rated_attempts: 20, cooldown_seconds: 86400, eligible_sources: 2, new_rated_attempts: 0, readiness: "waiting_for_evidence" },
  cycles, operator: { authenticated: curator, curator, ...(curator ? { handle: "test-curator" } : {}) },
});

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); localStorage.clear(); });

describe("EvolutionConsole", () => {
  it("shows actual decision, evaluation and service evidence while keeping the development scope explicit", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => payload() }));
    const wrapper = mount(EvolutionConsole); await flushPromises();
    expect(wrapper.text()).toContain("Development decision replay");
    expect(wrapper.text()).toContain("not a new blind model evaluation");
    expect(wrapper.text()).toContain("34 / 35"); expect(wrapper.text()).toContain("35 / 35");
    expect(wrapper.text()).toContain("+2.86 pp");
    expect(wrapper.text()).toContain("Service application verified");
    expect(wrapper.text()).toContain("hash-2");
    expect(wrapper.text()).toContain("Candidate generated with Meta.");
    expect(wrapper.find('button.primary').exists()).toBe(false);
    expect(wrapper.text()).toContain("Sign in with your curator account");
    wrapper.unmount();
  });

  it("shows a held candidate without claiming that it changed the active service", async () => {
    const held = cycle({ status: "held", evaluation: { ...cycle().evaluation!, gate: { passed: false, reasons: ["no_measured_gain"] } }, decision_reasons: ["no_measured_gain"], service_verification: null });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => payload([held]) }));
    const wrapper = mount(EvolutionConsole); await flushPromises();
    expect(wrapper.text()).toContain("Regression gate not passed");
    expect(wrapper.text()).toContain("Active service policy preserved");
    expect(wrapper.text()).not.toContain("Service application verified");
    expect(wrapper.text()).toContain("no measured gain"); wrapper.unmount();
  });

  it("never starts a paid operation on mount or refresh, and permits a single explicit curator start", async () => {
    const fetcher = vi.fn().mockImplementation(async (url: string, options?: RequestInit) => options?.method === "POST"
      ? { ok: true, json: async () => ({ id: "cycle-2" }) }
      : { ok: true, json: async () => payload([], true) });
    vi.stubGlobal("fetch", fetcher);
    const wrapper = mount(EvolutionConsole); await flushPromises();
    expect(fetcher.mock.calls.every(([, options]) => options.method !== "POST")).toBe(true);
    await wrapper.get('.page-heading button').trigger('click'); await flushPromises();
    expect(fetcher.mock.calls.every(([, options]) => options.method !== "POST")).toBe(true);
    await wrapper.get('button.primary').trigger('click'); await flushPromises();
    expect(fetcher.mock.calls.filter(([, options]) => options.method === "POST")).toHaveLength(1);
    wrapper.unmount();
  });

  it("polls while active, emits completion, and stops polling at a terminal state or unmount", async () => {
    vi.useFakeTimers();
    const queued = cycle({ status: "queued", candidate_policy: null, proposal: null, evaluation: null, service_verification: null, events: [] });
    const fetcher = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => payload([queued], true) }).mockResolvedValue({ ok: true, json: async () => payload() });
    vi.stubGlobal("fetch", fetcher);
    const wrapper = mount(EvolutionConsole); await flushPromises();
    expect(wrapper.text()).toContain("Cycle in progress");
    expect(wrapper.get('button.primary').attributes('disabled')).toBeDefined();
    await vi.advanceTimersByTimeAsync(4000); await flushPromises();
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(wrapper.emitted("completed")).toHaveLength(1);
    await vi.advanceTimersByTimeAsync(12000); expect(fetcher).toHaveBeenCalledTimes(2);
    wrapper.unmount(); expect(vi.getTimerCount()).toBe(0);
  });

  it("shows readiness without fabricating a policy or experiment before setup", async () => {
    const blank = payload([]); blank.active_policy = null;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => blank }));
    const wrapper = mount(EvolutionConsole); await flushPromises();
    expect(wrapper.text()).toContain("No active policy");
    expect(wrapper.text()).toContain("No cycles yet");
    expect(wrapper.find('.evaluation-values').exists()).toBe(false);
    wrapper.unmount();
  });

  it("keeps polling an adopted version until the service proof is recorded", async () => {
    vi.useFakeTimers();
    const awaitingProof = cycle({ service_verification: null });
    const fetcher = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => payload([awaitingProof], true) }).mockResolvedValue({ ok: true, json: async () => payload() });
    vi.stubGlobal("fetch", fetcher);
    const wrapper = mount(EvolutionConsole); await flushPromises();
    expect(wrapper.text()).toContain("Service application not yet verified");
    expect(wrapper.get('button.primary').attributes('disabled')).toBeDefined();
    await vi.advanceTimersByTimeAsync(4000); await flushPromises();
    expect(wrapper.text()).toContain("Service application verified");
    expect(wrapper.emitted("completed")).toHaveLength(1);
    expect(vi.getTimerCount()).toBe(0); wrapper.unmount();
  });

  it("renders the activating stage and code_revision without claiming adoption or exposing private event data", async () => {
    const pending = cycle({ status: "activating", service_verification: null, code_revision: "local-development",
      criteria: { min_cases: 35, min_improvements: 1, max_regressions: 0 },
      events: [{ stage: "gate_passed", message: "The regression gate passed.", created_at: "2026-10-29T23:01:00Z", data: { private_marker: "do-not-render-internal-payload" } }] });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => payload([pending], true) }));
    const wrapper = mount(EvolutionConsole); await flushPromises();
    expect(wrapper.text()).toContain("Verifying service application");
    expect(wrapper.text()).toContain("Frozen gate: at least 35 cases");
    expect(wrapper.text()).toContain("local-development");
    expect(wrapper.text()).not.toContain("Service application verified");
    expect(wrapper.text()).not.toContain("do-not-render-internal-payload");
    expect(wrapper.get('button.primary').attributes('disabled')).toBeDefined();
    wrapper.unmount();
  });
});
