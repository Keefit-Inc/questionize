import { describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";

vi.mock("../api", () => ({
  withDevice: async (call: (api: unknown) => unknown) =>
    call({
      getMe: async () => ({
        handle: "reader-x",
        anonymous: true,
        xp: 25,
        ratings: [
          { skill: "CR:assumption", rating: 1520, attempts: 2, correct: 1, provisional: true },
          { skill: "overall", rating: 1510, attempts: 3, correct: 2, provisional: true },
        ],
      }),
    }),
}));

describe("MePage", () => {
  it("lists overall first, labels skills and marks provisional ratings", async () => {
    const { default: MePage } = await import("./MePage.vue");
    const wrapper = mount(MePage);
    await flushPromises();
    const rows = wrapper.findAll("tbody tr").map((r) => r.text());
    expect(rows[0]).toContain("Overall");
    expect(rows[1]).toContain("Critical Reasoning · assumption");
    expect(rows[1]).toContain("(provisional)");
    expect(wrapper.text()).toContain("not official test scores");
  });
});
