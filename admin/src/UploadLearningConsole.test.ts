import { mount, flushPromises } from "@vue/test-utils";
import { afterEach, expect, it, vi } from "vitest";
import UploadLearningConsole from "./UploadLearningConsole.vue";
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });
it("shows local-only provenance, actual memory and worker status without inventing improvement", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ storage: "Originals remain local.",
    active_memory: { id: "base", version: 1, content_hash: "hash", expert_rules: 0, experience_rules: 0 }, worker: { online: false, last_seen_at: null, mode: "local" },
    totals: { uploads: 0, operator_checks: 1, reference_statuses: {}, outcomes: {} }, observations: [], cycles: [], budget: {} }) }));
  const wrapper = mount(UploadLearningConsole);
  await flushPromises();
  expect(wrapper.text()).toContain("Originals remain local");
  expect(wrapper.text()).toContain("The learner app continues normally");
  expect(wrapper.text()).toContain("v1");
  expect(wrapper.text()).toContain("1 separately labeled operator checks");
  expect(wrapper.text()).toContain("No GMAT CR uploads have been observed");
  wrapper.unmount();
  expect(vi.getTimerCount()).toBe(0);
});
