import { describe, expect, it, vi } from "vitest";
import { ApiClient, ApiError } from "./client";

function fakeFetch(status: number, body: unknown) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}

describe("ApiClient", () => {
  it("sends the bearer token and JSON body", async () => {
    const f = fakeFetch(202, { status: "queued", run_id: 7 });
    const client = new ApiClient("https://questionize.org/", "tok", f as unknown as typeof fetch);
    const res = await client.generate({ url: "https://x.test/a", title: "A", text: "t", types: ["CR"], difficulty: "medium", count_per_type: 1 });

    expect(res).toEqual({ status: "queued", run_id: 7 });
    const [url, init] = f.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("https://questionize.org/api/v1/generations");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer tok");
    expect(JSON.parse(init.body as string).types).toEqual(["CR"]);
  });

  it("raises ApiError with the server's error code", async () => {
    const client = new ApiClient("http://localhost:3000", "tok", fakeFetch(429, { error: "daily_limit_reached" }) as unknown as typeof fetch);
    await expect(client.getItem("abc")).rejects.toMatchObject({ status: 429, code: "daily_limit_reached" });
    await expect(client.getItem("abc")).rejects.toBeInstanceOf(ApiError);
  });

  it("builds an authenticated cable URL", () => {
    expect(new ApiClient("https://questionize.org", "a b").cableUrl()).toBe("wss://questionize.org/cable?token=a%20b");
    expect(new ApiClient("http://localhost:3000/").cableUrl()).toBe("ws://localhost:3000/cable?token=");
  });
});

describe("replayRunState", async () => {
  const { eventKey, replayRunState } = await import("./cable");
  it("turns stored events back into live events and dedupes by key", () => {
    const item = { id: "i1", revealed: false } as never;
    const replay = replayRunState({
      run_id: 1,
      status: "running",
      events: [
        { stage: "analyze", message: "Mapping" },
        { stage: "question", index: 0, item_id: "i1" },
        { stage: "question", index: 1, item_id: "missing" },
      ],
      items: [item],
    });
    expect(replay.map((e) => e.stage)).toEqual(["analyze", "question"]);
    expect(eventKey(replay[1])).toBe(eventKey({ stage: "question", index: 0, item_id: "i1" }));
    expect(eventKey({ stage: "analyze", message: "Mapping" })).toBe("analyze|||Mapping");
  });
});
