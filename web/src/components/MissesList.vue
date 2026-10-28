<script setup lang="ts">
// Questions the learner snapped, newest first; the question's opening words when this device has it.
import { onMounted, reactive, ref } from "vue";
import { FAMILY_LABELS, subtypeLabel, type ErrorLogEntry, type QuestionType } from "@questionize/shared";
import { withDevice } from "../api";
import { loadQuestion } from "../device";

const entries = ref<ErrorLogEntry[] | null>(null);
const stems = reactive(new Map<number, string>());
const error = ref("");

onMounted(async () => {
  try {
    entries.value = (await withDevice((c) => c.listErrorLog())).entries;
    for (const e of entries.value) {
      const q = await loadQuestion(e.id);
      if (q) stems.set(e.id, q.stem);
    }
  } catch {
    error.value = "Couldn't load your questions.";
  }
});

const where = (e: ErrorLogEntry) => [e.book, e.page && `p. ${e.page}`, e.number && `#${e.number}`].filter(Boolean).join(" · ") || "Photographed question";
</script>

<template>
  <p v-if="error" class="error" role="alert">{{ error }}</p>
  <div v-else-if="entries && !entries.length" class="empty">
    <p>Questions you snap show up here with their analysis and practice.</p>
    <RouterLink to="/snap" class="go">Snap a question you missed</RouterLink>
  </div>
  <ul v-else-if="entries" class="entries">
    <li v-for="e in entries" :key="e.id">
      <RouterLink :to="`/misses/${e.id}`" class="entry">
        <span class="badge" aria-hidden="true">{{ e.diagnosis.family }}<small v-if="e.diagnosis.difficulty">{{ e.diagnosis.difficulty }}/5</small></span>
        <span class="text">
          <strong>{{ where(e) }}</strong>
          <span class="muted">{{ FAMILY_LABELS[e.diagnosis.family as QuestionType] ?? e.diagnosis.family }} · {{ subtypeLabel(e.diagnosis.subtype) }}<template v-if="e.diagnosis.difficulty"> · difficulty {{ e.diagnosis.difficulty }}/5</template></span>
          <span v-if="stems.get(e.id)" class="clamp">{{ stems.get(e.id) }}</span>
          <span v-else-if="e.diagnosis.misconception" class="muted clamp">{{ e.diagnosis.misconception.statement }}</span>
        </span>
      </RouterLink>
    </li>
  </ul>
  <p v-else class="muted">Loading…</p>
</template>

<style scoped>
.error { color: #d0563b; }
.muted { opacity: 0.7; font-size: 13px; }
.empty { display: flex; flex-direction: column; gap: 12px; padding: 18px; border-radius: 12px; border: 1px dashed rgba(127, 127, 127, 0.4); }
.empty p { margin: 0; }
.go { display: block; text-align: center; padding: 12px; border-radius: 12px; background: #3b6fd0; color: #fff !important; font-weight: 700; text-decoration: none; }
.entries { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.entry { display: flex; gap: 12px; padding: 10px; border-radius: 12px; border: 1px solid rgba(127, 127, 127, 0.25); color: inherit; text-decoration: none; }
.badge { width: 52px; height: 52px; border-radius: 10px; flex: none; display: flex; flex-direction: column; align-items: center; justify-content: center; background: rgba(59, 111, 208, 0.12); color: #3b6fd0; font-weight: 800; font-size: 15px; }
.badge small { font-size: 11px; font-weight: 600; opacity: 0.8; }
.text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.clamp { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>
