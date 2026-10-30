import { afterEach, describe, expect, it, vi } from "vitest";
import { commitUrl, isInFlight, loadEvolution, requestHeaders, stageState, startEvolution, validateEvolution, type EvolutionCycle } from "./evolution";

afterEach(() => { vi.unstubAllGlobals(); localStorage.clear(); });

describe("evolution API and state", () => {
  it("rejects unsupported data rather than implying an empty successful registry", () => {
    expect(() => validateEvolution({ schema_version: 2 })).toThrow("Unsupported evolution data");
    expect(() => validateEvolution(null)).toThrow("Evolution data is unavailable");
  });

  it("uses the existing account token only in the request header", async () => {
    localStorage.setItem("questionize.token", "test-account-token");
    expect(requestHeaders()).toEqual({ Authorization: "Bearer test-account-token" });
    const fetcher = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: "cycle-1" }) });
    vi.stubGlobal("fetch", fetcher);
    expect(await startEvolution()).toBe("cycle-1");
    expect(fetcher).toHaveBeenCalledWith("/api/v1/research/cycles", {
      method: "POST", headers: { Authorization: "Bearer test-account-token", "Content-Type": "application/json" }, body: "{}",
    });
  });

  it("makes refresh a GET and reports operator authorization failures without retrying a paid action", async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: false, status: 403, json: async () => ({ error: "forbidden" }) });
    vi.stubGlobal("fetch", fetcher);
    await expect(startEvolution()).rejects.toThrow("Only a curator");
    expect(fetcher).toHaveBeenCalledTimes(1);
    fetcher.mockResolvedValue({ ok: false, status: 503 });
    await expect(loadEvolution()).rejects.toThrow("Evolution data is unavailable (503)");
    expect(fetcher.mock.calls[1]).toEqual(["/admin/cycles", { cache: "no-store", headers: {} }]);
  });

  it("never marks service application complete just because a candidate was adopted", () => {
    const cycle = { status: "adopted", proposal: {}, candidate_policy: {}, evaluation: {}, service_verification: null } as EvolutionCycle;
    expect(stageState(cycle, "decision")).toBe("complete");
    expect(stageState(cycle, "service")).toBe("current");
    cycle.service_verification = { verified: true, policy_id: "p1", policy_hash: "h1" };
    expect(stageState(cycle, "service")).toBe("complete");
    cycle.status = "held"; cycle.service_verification = null;
    expect(stageState(cycle, "decision")).toBe("held");
    expect(stageState(cycle, "service")).toBe("pending");
  });

  it("keeps activation in progress until the service proof succeeds", () => {
    const cycle = { status: "activating", proposal: {}, candidate_policy: {}, evaluation: {}, service_verification: null } as EvolutionCycle;
    expect(isInFlight(cycle)).toBe(true);
    expect(stageState(cycle, "decision")).toBe("complete");
    expect(stageState(cycle, "service")).toBe("current");
    expect(commitUrl("local-development")).toBeNull();
    expect(commitUrl("68525c3a6c865ea25648425eae1891520392d5fd")).toContain("/commit/68525c3");
  });
});
