// The learner's review lists (My misses and Archived), remembered between the list and the
// detail pages so a question page can step to the previous and next one.
import { ref } from "vue";
import type { ReviewCard } from "@questionize/shared";
import { withDevice } from "./api";

export type ListName = "misses" | "archived";

const lists = { misses: ref<ReviewCard[] | null>(null), archived: ref<ReviewCard[] | null>(null) };

export function reviewList(name: ListName) {
  return lists[name];
}

export async function loadReview(name: ListName): Promise<ReviewCard[]> {
  const { cards } = await withDevice((c) => c.listReview(name === "archived"));
  lists[name].value = cards;
  return cards;
}

export function cardKey(card: ReviewCard): string {
  return card.kind === "snap" ? `snap:${card.entry.id}` : `item:${card.item.id}`;
}

export function cardPath(card: ReviewCard, list: ListName): string {
  return card.kind === "snap" ? `/misses/${card.entry.id}?list=${list}` : `/q/${card.item.id}?list=${list}`;
}

/** Where this question sits in its list, and the cards on either side. */
export async function neighbors(name: ListName, key: string) {
  const cards = lists[name].value ?? (await loadReview(name).catch(() => []));
  const index = cards.findIndex((c) => cardKey(c) === key);
  return {
    index,
    total: cards.length,
    prev: index > 0 ? cards[index - 1] : null,
    next: index >= 0 && index < cards.length - 1 ? cards[index + 1] : null,
  };
}
