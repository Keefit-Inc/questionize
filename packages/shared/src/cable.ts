// Live generation progress over Action Cable (GenerationChannel).
import { createConsumer } from "@rails/actioncable";
import type { GenerationEvent, GenerationRunState, Item, TallyUpdate } from "./api";

export const TERMINAL_STAGES = new Set(["done", "declined", "failed"]);

/**
 * Subscribes to one run; returns a function that closes the connection.
 * Events broadcast before the subscription is confirmed are not replayed, so `onConnected`
 * is the moment to fetch the run's stored progress and merge it (see mergeRunState).
 */
export function subscribeToGeneration(
  cableUrl: string,
  runId: number,
  onEvent: (event: GenerationEvent) => void,
  { onConnected = () => {}, onRejected = () => {} }: { onConnected?: () => void; onRejected?: () => void } = {},
): () => void {
  const consumer = createConsumer(cableUrl);
  const subscription = consumer.subscriptions.create(
    { channel: "GenerationChannel", run_id: runId },
    {
      received(event: GenerationEvent) {
        onEvent(event);
        if (TERMINAL_STAGES.has(event.stage)) close();
      },
      connected: onConnected,
      rejected: onRejected,
    },
  );
  function close() {
    subscription.unsubscribe();
    consumer.disconnect();
  }
  return close;
}

/** Stable identity for an event, so the same event from the live stream and the stored run is handled once. */
export function eventKey(event: GenerationEvent | GenerationRunState["events"][number]): string {
  if (event.stage === "question") return `question|${event.index}`;
  const index = "index" in event ? event.index : "";
  const attempt = "attempt" in event ? event.attempt : "";
  const message = "message" in event ? event.message : "";
  return `${event.stage}|${index}|${attempt}|${message}`;
}

/** Rebuilds the live events a run has already broadcast from its stored state. */
export function replayRunState(state: GenerationRunState): GenerationEvent[] {
  const items = new Map<string, Item>(state.items.map((item) => [item.id, item]));
  return state.events.flatMap((event): GenerationEvent[] => {
    if (event.stage !== "question") return [event];
    const item = items.get(event.item_id);
    return item && !item.revealed ? [{ stage: "question", index: event.index, item }] : [];
  });
}

/** Live answer tallies for an item the user has already answered (ItemChannel). */
export function subscribeToItem(cableUrl: string, itemId: string, onTally: (update: TallyUpdate) => void): () => void {
  const consumer = createConsumer(cableUrl);
  const subscription = consumer.subscriptions.create({ channel: "ItemChannel", item_id: itemId }, { received: onTally });
  return () => {
    subscription.unsubscribe();
    consumer.disconnect();
  };
}
