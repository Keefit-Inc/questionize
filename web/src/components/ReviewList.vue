<script setup lang="ts">
// My misses or Archived: questions the learner snapped, and bank questions they missed or saved.
import { onMounted, reactive, ref } from "vue";
import { FAMILY_LABELS, subtypeLabel, type QuestionType, type ReviewCard } from "@questionize/shared";
import { cardKey, cardPath, loadReview, reviewList, type ListName } from "../review";
import { loadQuestion } from "../device";

const props = defineProps<{ list: ListName }>();
const cards = reviewList(props.list);
const stems = reactive(new Map<number, string>());
const error = ref("");

onMounted(async () => {
  try {
    for (const c of await loadReview(props.list)) {
      if (c.kind !== "snap") continue;
      const q = await loadQuestion(c.entry.id);
      if (q) stems.set(c.entry.id, q.stem);
    }
  } catch {
    error.value = "Couldn't load your questions.";
  }
});

function view(c: ReviewCard) {
  if (c.kind === "snap") {
    const d = c.entry.diagnosis;
    const where = [c.entry.book, c.entry.page && `p. ${c.entry.page}`, c.entry.number && `#${c.entry.number}`].filter(Boolean).join(" · ");
    return { family: d.family, skill: subtypeLabel(d.subtype), difficulty: d.difficulty ?? null, title: stems.get(c.entry.id) ?? d.competency, tag: "Snapped", where, trap: d.misconception?.statement ?? "" };
  }
  return { family: c.item.family, skill: subtypeLabel(c.item.subtype), difficulty: null, title: c.item.stem, tag: c.reason === "missed" ? "Missed" : "Saved", where: c.item.source?.domain ?? (c.item.origin === "pattern" ? "Practice" : ""), trap: "" };
}
</script>

<template>
  <p v-if="error" class="error" role="alert">{{ error }}</p>
  <div v-else-if="cards && !cards.length" class="empty">
    <template v-if="list === 'misses'">
      <p class="empty-title">Nothing to review yet</p>
      <p>Questions you snap, and bank questions you get wrong, collect here until you archive them.</p>
      <RouterLink to="/snap" class="go">Snap a question you missed</RouterLink>
    </template>
    <template v-else>
      <p class="empty-title">No archived questions</p>
      <p>When you've mastered a question, archive it from its page. It moves here.</p>
    </template>
  </div>
  <ul v-else-if="cards" class="cards">
    <li v-for="c in cards" :key="cardKey(c)">
      <RouterLink :to="cardPath(c, list)" class="card">
        <span class="badge" :data-family="view(c).family">
          {{ view(c).family }}
          <span v-if="view(c).difficulty" class="dots" :aria-label="`Difficulty ${view(c).difficulty} of 5`">
            <i v-for="n in 5" :key="n" :class="{ on: n <= (view(c).difficulty ?? 0) }" />
          </span>
        </span>
        <span class="body">
          <span class="meta">
            <span class="tag" :class="view(c).tag.toLowerCase()">{{ view(c).tag }}</span>
            {{ FAMILY_LABELS[view(c).family as QuestionType] ?? view(c).family }} · {{ view(c).skill }}
          </span>
          <span class="title">{{ view(c).title }}</span>
          <span v-if="view(c).where" class="where">{{ view(c).where }}</span>
        </span>
        <svg class="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7" /></svg>
      </RouterLink>
    </li>
  </ul>
  <div v-else class="skeleton" aria-hidden="true"><span /><span /><span /></div>
</template>

<style scoped>
.error { color: var(--bad); }
.empty { display: flex; flex-direction: column; gap: 8px; padding: 24px 20px; border-radius: var(--radius); background: var(--surface); border: 1px solid var(--line); text-align: center; }
.empty p { margin: 0; color: var(--muted); line-height: 1.5; }
.empty .empty-title { color: var(--fg); font-weight: 700; font-size: 17px; }
.go { margin-top: 8px; display: block; padding: 13px; border-radius: 12px; background: var(--accent); color: #fff !important; font-weight: 700; text-decoration: none; }
.cards { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.card { display: flex; align-items: center; gap: 14px; padding: 14px; border-radius: var(--radius); background: var(--surface); border: 1px solid var(--line); color: inherit; text-decoration: none; box-shadow: var(--shadow); transition: transform 0.12s; }
.card:active { transform: scale(0.99); }
.badge { width: 52px; height: 56px; flex: none; border-radius: 12px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; font-weight: 800; font-size: 15px; background: var(--accent-soft); color: var(--accent); }
.badge[data-family="RC"] { background: var(--violet-soft); color: var(--violet); }
.dots { display: flex; gap: 2px; }
.dots i { width: 5px; height: 5px; border-radius: 50%; background: currentColor; opacity: 0.25; }
.dots i.on { opacity: 1; }
.body { display: flex; flex-direction: column; gap: 4px; min-width: 0; flex: 1; }
.meta { font-size: 12px; color: var(--muted); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.tag { font-size: 11px; font-weight: 700; padding: 1px 7px; border-radius: 999px; background: var(--chip); color: var(--fg); }
.tag.missed { background: var(--bad-soft); color: var(--bad); }
.tag.snapped { background: var(--accent-soft); color: var(--accent); }
.title { font-weight: 600; line-height: 1.35; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.where { font-size: 12px; color: var(--muted); }
.chev { width: 18px; height: 18px; flex: none; fill: none; stroke: var(--muted); stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.skeleton { display: flex; flex-direction: column; gap: 10px; }
.skeleton span { height: 84px; border-radius: var(--radius); background: var(--chip); animation: pulse 1.2s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: 0.5; } }
</style>
