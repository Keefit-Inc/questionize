import { describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";

vi.mock("../api", () => ({
  api: { getConfig: async () => ({ facebook_app_id: null }) },
  useToken: () => undefined,
  withDevice: async (call: (api: unknown) => unknown) =>
    call({
      getMe: async () => ({
        handle: "reader-x",
        level: "gmat",
        anonymous: true,
        xp: 25,
        ratings: [
          { skill: "CR:assumption", rating: 1520, attempts: 2, correct: 1, provisional: true },
          { skill: "overall", rating: 1510, attempts: 3, correct: 2, provisional: true },
        ],
      }),
      listErrorLog: async () => ({
        eligible: true,
        weaknesses: { traps: { irrelevant: 2, too_extreme: 1 }, misconceptions: { keyword_matching: 2 } },
        entries: [1, 2].map((id) => ({
          id,
          practice: [],
          diagnosis: { family: "CR", subtype: "weaken", difficulty: id + 2, learning_objectives: ["Separate a correlation from its cause"] },
        })),
      }),
    }),
}));

async function mountAt(path: string) {
  const { default: MePage } = await import("./MePage.vue");
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/me", component: MePage }, { path: "/snap", component: MePage }] });
  await router.push(path);
  const wrapper = mount(MePage, { global: { plugins: [router] } });
  await flushPromises();
  return wrapper;
}

describe("MePage", () => {
  it("Analysis shows recurring traps, misconceptions, missed types and what to practice", async () => {
    const text = (await mountAt("/me")).text();
    expect(text).toContain("Irrelevant");
    expect(text).toContain("keyword matching");
    expect(text).toContain("Critical Reasoning · weaken");
    expect(text).toContain("3.5");
    expect(text).toContain("Separate a correlation from its cause");
  });

  it("Stats lists overall first, labels skills and marks provisional ratings", async () => {
    const wrapper = await mountAt("/me?view=stats");
    const rows = wrapper.findAll("tbody tr").map((r) => r.text());
    expect(rows[0]).toContain("Overall");
    expect(rows[1]).toContain("Critical Reasoning · assumption");
    expect(rows[1]).toContain("(provisional)");
    expect(wrapper.text()).toContain("not official test scores");
  });
});
