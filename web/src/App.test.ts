import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import App from "./App.vue";

describe("App", () => {
  it("renders the product name", () => {
    expect(mount(App).text()).toContain("Questionize");
  });
});
