import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ getMe: vi.fn(), setLevel: vi.fn() }));
vi.mock("./api", () => ({ withDevice: (call: (client: typeof mocks) => unknown) => call(mocks) }));
import { loadMe, me } from "./profile";

beforeEach(() => { me.value = null; mocks.getMe.mockReset(); mocks.setLevel.mockReset().mockResolvedValue({ level: "gmat" }); });

describe("profile level defaults", () => {
  it("persists GMAT for a new profile before returning it to the app", async () => {
    mocks.getMe.mockResolvedValue({ handle: "new-reader", level: null });
    expect((await loadMe())?.level).toBe("gmat");
    expect(mocks.setLevel).toHaveBeenCalledWith("gmat");
    expect(me.value?.level).toBe("gmat");
  });

  it("preserves an existing school-level profile when the catalog is hidden", async () => {
    mocks.getMe.mockResolvedValue({ handle: "returning-reader", level: "middle" });
    expect((await loadMe())?.level).toBe("middle");
    expect(mocks.setLevel).not.toHaveBeenCalled();
  });
});
