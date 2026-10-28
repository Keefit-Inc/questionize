import { describe, expect, it } from "vitest";
import { readNdjson } from "./ndjson";
import type { AgentEvent } from "./types";

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const c of chunks) controller.enqueue(enc.encode(c));
      controller.close();
    },
  });
}

async function collect<T>(it: AsyncIterable<T>): Promise<T[]> {
  const out: T[] = [];
  for await (const x of it) out.push(x);
  return out;
}

describe("readNdjson", () => {
  it("reassembles lines split across chunks and skips blanks", async () => {
    const events = await collect(
      readNdjson<AgentEvent>(streamOf(['{"stage":"analyze","mes', 'sage":"a"}\n\n{"stage":"fai', 'led","message":"x"}\n'])),
    );
    expect(events.map((e) => e.stage)).toEqual(["analyze", "failed"]);
  });

  it("keeps a final line without a trailing newline", async () => {
    expect(await collect(readNdjson(streamOf(['{"n":1}\n{"n":2}'])))).toEqual([{ n: 1 }, { n: 2 }]);
  });

  it("decodes multi-byte characters split between chunks", async () => {
    const bytes = new TextEncoder().encode('{"m":"검증"}\n');
    const body = new ReadableStream<Uint8Array>({
      start(c) {
        c.enqueue(bytes.slice(0, 8));
        c.enqueue(bytes.slice(8));
        c.close();
      },
    });
    expect(await collect(readNdjson(body))).toEqual([{ m: "검증" }]);
  });
});
