import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { LEVELS } from "@questionize/shared";
import LevelPicker from "./LevelPicker.vue";

describe("LevelPicker", () => {
  it("offers only the three test-prep levels while preserving the full catalog", async () => {
    const wrapper = mount(LevelPicker, { props: { current: "gmat" } });
    const buttons = wrapper.findAll("button");
    expect(buttons).toHaveLength(3);
    expect(buttons.map((button) => button.find("strong").text())).toEqual(["GMAT", "LSAT", "GRE"]);
    expect(wrapper.text()).not.toContain("School");
    expect(LEVELS).toHaveLength(7);
    expect(buttons[0].attributes("aria-pressed")).toBe("true");
    await buttons[1].trigger("click");
    expect(wrapper.emitted("pick")).toEqual([["lsat"]]);
  });
});
