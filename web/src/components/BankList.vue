<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { FAMILY_LABELS, subtypeLabel, type Item } from "@questionize/shared";
import { withDevice } from "../api";

const items = ref<Item[]>([]);
const next = ref<string | null>(null);
const family = ref<"" | "CR" | "RC">("");
const loading = ref(false);
const error = ref("");

async function load(reset = false) {
  loading.value = true;
  error.value = "";
  try {
    const page = await withDevice((api) => api.listItems({ family: family.value, before: reset ? undefined : (next.value ?? undefined) }));
    items.value = reset ? page.items : [...items.value, ...page.items];
    next.value = page.next;
  } catch {
    error.value = "Couldn't load questions. Please try again.";
  } finally {
    loading.value = false;
  }
}

onMounted(() => load(true));
</script>

<template>
  <p class="intro">Questions written from real articles, checked by an independent solver and the Argument Judge. Answer first, then see how everyone answered.</p>
  <div class="filters" role="group" aria-label="Question type">
    <button v-for="f in ['', 'CR', 'RC'] as const" :key="f" :class="{ on: family === f }" @click="family = f; load(true)">
      {{ f ? FAMILY_LABELS[f] : "All" }}
    </button>
  </div>

  <p v-if="error" class="error">{{ error }}</p>
  <p v-else-if="!loading && !items.length" class="muted">No shared questions yet. They appear here as readers generate them.</p>

  <ul class="feed">
    <li v-for="item in items" :key="item.id">
      <RouterLink :to="`/q/${item.id}`" class="card">
        <span class="meta">
          {{ FAMILY_LABELS[item.family] }} · {{ subtypeLabel(item.subtype) }}
          <template v-if="item.source?.domain"> · {{ item.source.domain }}</template>
          <template v-if="item.revealed"> · answered</template>
        </span>
        <span class="stem">{{ item.stem }}</span>
        <span class="passage">{{ item.passage.replace(/\[\[|\]\]/g, "") }}</span>
        <span class="meta">{{ item.attempts_count }} {{ item.attempts_count === 1 ? "attempt" : "attempts" }}</span>
      </RouterLink>
    </li>
  </ul>

  <button v-if="next" class="more" :disabled="loading" @click="load()">{{ loading ? "Loading…" : "More questions" }}</button>
</template>

<style scoped>
.intro { margin: 0; font-size: 14px; opacity: 0.75; line-height: 1.5; }
.filters { display: flex; gap: 6px; margin: 12px 0; }
.filters button { padding: 7px 14px; border-radius: 999px; font-weight: 600; border: 1px solid var(--line); background: transparent; color: inherit; font: inherit; cursor: pointer; }
.filters button.on { border-color: var(--accent); background: rgba(59, 111, 208, 0.12); font-weight: 600; }
.feed { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.card { display: flex; flex-direction: column; gap: 8px; padding: 16px; border-radius: var(--radius); border: 1px solid var(--line); background: var(--surface); box-shadow: var(--shadow); color: inherit; text-decoration: none; }
.card:hover { border-color: var(--accent); }
.meta { font-size: 12px; opacity: 0.7; }
.stem { font-weight: 700; line-height: 1.4; }
.passage { font-family: var(--serif); font-size: 15px; line-height: 1.5; color: var(--muted); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.more { margin-top: 12px; padding: 10px 16px; border-radius: 8px; border: 1px solid var(--line); background: transparent; color: inherit; font: inherit; cursor: pointer; }
.muted { opacity: 0.7; }
.error { color: var(--bad); }
</style>
