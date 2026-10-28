import { describe, expect, it } from "vitest";
import { ApiError } from "@questionize/shared";
import { errorMessage, eventLine } from "./messages";

describe("errorMessage", () => {
  it("maps API error codes to reader-facing copy", () => {
    expect(errorMessage(new ApiError(429, "daily_limit_reached"), "s")).toMatch(/today's generation limit/);
    expect(errorMessage(new ApiError(429, "Too Many Requests"), "s")).toMatch(/Slow down/);
    expect(errorMessage(new ApiError(422, "article_too_short"), "s")).toMatch(/enough article text/);
  });

  it("explains network failures with the server name", () => {
    expect(errorMessage(new TypeError("Failed to fetch"), "https://questionize.org")).toContain("https://questionize.org");
  });
});

describe("eventLine", () => {
  it("labels agents per question and marks verdicts", () => {
    expect(eventLine({ stage: "judge", index: 1, message: "Measuring" })).toEqual({ who: "Judge Q2", text: "Measuring", ok: undefined });
    expect(eventLine({ stage: "verdict", index: 0, attempt: 1, passed: false, message: "Close call" })?.ok).toBe(false);
    expect(eventLine({ stage: "done", count: 2 })).toBeNull();
  });
});
