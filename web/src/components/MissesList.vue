<script setup lang="ts">
// Questions the learner photographed: newest first, with their own photo when this device has it.
import { onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { FAMILY_LABELS, subtypeLabel, type ErrorLogEntry, type QuestionType } from "@questionize/shared";
import { withDevice } from "../api";
import { photoUrl } from "../photos";

const entries = ref<ErrorLogEntry[] | null>(null);
const thumbs = reactive(new Map<number, string>());
const error = ref("");

onMounted(async () => {
  try {
    entries.value = (await withDevice((c) => c.listErrorLog())).entries;
    for (const e of entries.value) {
      const url = await photoUrl(e.id);
      if (url) thumbs.set(e.id, url);
    }
  } catch {
    error.value = "Couldn't load your questions.";
  }
});
onBeforeUnmount(() => thumbs.forEach((url) => URL.revokeObjectURL(url)));

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
        <img v-if="thumbs.get(e.id)" :src="thumbs.get(e.id)" alt="" class="thumb" />
        <span v-else class="thumb blank" aria-hidden="true">{{ e.diagnosis.family }}</span>
        <span class="text">
          <strong>{{ where(e) }}</strong>
          <span class="muted">{{ FAMILY_LABELS[e.diagnosis.family as QuestionType] ?? e.diagnosis.family }} · {{ subtypeLabel(e.diagnosis.subtype) }}<template v-if="e.diagnosis.difficulty"> · difficulty {{ e.diagnosis.difficulty }}/5</template></span>
          <span v-if="e.diagnosis.misconception" class="muted clamp">{{ e.diagnosis.misconception.statement }}</span>
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
.thumb { width: 56px; height: 56px; border-radius: 8px; object-fit: cover; flex: none; }
.thumb.blank { display: flex; align-items: center; justify-content: center; background: rgba(127, 127, 127, 0.12); font-weight: 700; font-size: 13px; }
.text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.clamp { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>
