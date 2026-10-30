import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, it, vi } from "vitest";
import EvidenceConsole from "./EvidenceConsole.vue";
import type { EvidenceRegistry } from "./research";

afterEach(() => vi.unstubAllGlobals());
it("keeps reference provenance separate and distinguishes planned research from measured runs", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ knowledge_evidence: { origins: { user_experience: 2 }, statuses: { ai_estimated: 2 } } }) }));
  const registry: EvidenceRegistry = { reviewed_at: "2026-10-30", review_scope: "Selected primary sources", capture_audits: [], evaluations: [],
    knowledge_policy: { expert_reference: "Private references", user_experience: "Separate usage", promotion: "AI agreement is not truth", rights: "Expert data cannot fan out" },
    papers: [{ id: "planned", title: "Learning study", url: "https://arxiv.org/abs/1506.05908", capabilities: ["C4", "C6"], claim: "Predict future responses", limitations: "Not implemented", implementation_status: "planned", review_status: "abstract_checked", implementation_paths: ["api/app/services/learning/recommend.rb"], protocols: ["E7"], runs: [] }] };
  const wrapper = mount(EvidenceConsole, { props: { registry } });
  await flushPromises();
  expect(wrapper.text()).toContain("Expert references ≠ usage-derived knowledge");
  expect(wrapper.text()).toContain("AI agreement is not truth");
  expect(wrapper.text()).toContain("No recorded results for this method. Related protocols: E7");
  expect(wrapper.text()).toContain("ai_estimated: 2");
  await wrapper.find('select[aria-label="Literature capability"]').setValue("C3");
  expect(wrapper.text()).not.toContain("Learning study");
  wrapper.unmount();
});
