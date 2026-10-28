<script setup lang="ts">
// One error-log entry: the analysis, then fresh practice on the same trap.
import { onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { DiagnosisReport, QuestionCard, type ErrorLogEntry, type FlagReason, type Item, type Label } from "@questionize/shared";
import { withDevice } from "../api";
import { photoUrl } from "../photos";

const props = defineProps<{ id: number }>();
const entry = ref<ErrorLogEntry | null>(null);
const photo = ref<string | null>(null);
const error = ref("");
const practice = reactive(new Map<string, { item: Item; chosen: Label | null; busy: boolean; shownAt: number; note: string }>());

onMounted(async () => {
  try {
    entry.value = await withDevice((c) => c.getErrorLogEntry(props.id));
    for (const item of entry.value.practice) practice.set(item.id, { item, chosen: null, busy: false, shownAt: Date.now(), note: "" });
    photo.value = await photoUrl(props.id);
  } catch {
    error.value = "This entry isn't available.";
  }
});
onBeforeUnmount(() => photo.value && URL.revokeObjectURL(photo.value));

async function answer(id: string, label: Label) {
  const p = practice.get(id)!;
  p.busy = true;
  try {
    const res = await withDevice((c) => c.attempt(id, label, Date.now() - p.shownAt));
    p.item = res.item;
    p.chosen = label;
    const change = res.rating_changes[`${res.item.family}:${res.item.subtype}`];
    p.note = change ? `Your ${res.item.subtype.replace(/_/g, " ")} rating: ${Math.round(change.before)} → ${Math.round(change.after)}` : "";
  } catch {
    error.value = "Couldn't submit your answer. Please try again.";
  } finally {
    p.busy = false;
  }
}

async function flag(id: string, reason: FlagReason, comment: string) {
  await withDevice((c) => c.feedback(id, { kind: "flag", reason, comment })).catch(() => (error.value = "Couldn't send your report."));
}
</script>

<template>
  <section class="entry">
    <RouterLink to="/questions" class="back">← My misses</RouterLink>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <template v-if="entry">
      <DiagnosisReport :entry="entry" :photo-url="photo" />
      <h2 v-if="entry.practice.length">Practice the same trap</h2>
      <p v-if="entry.practice.length" class="muted">New questions on different topics, built to catch the same mistake. Only your first answer counts.</p>
      <div v-for="item in entry.practice" :key="item.id">
        <template v-if="practice.get(item.id)">
          <QuestionCard
            :item="practice.get(item.id)!.item"
            :chosen="practice.get(item.id)!.chosen"
            :busy="practice.get(item.id)!.busy"
            :locatable="false"
            @answer="(l) => answer(item.id, l)"
            @flag="(r, c) => flag(item.id, r, c)"
          />
          <p v-if="practice.get(item.id)!.note" class="muted">{{ practice.get(item.id)!.note }}</p>
        </template>
      </div>
    </template>
    <p v-else-if="!error" class="muted">Loading…</p>
  </section>
</template>

<style scoped>
.entry { display: flex; flex-direction: column; gap: 12px; }
.back { text-decoration: none; font-size: 14px; }
h2 { margin: 12px 0 0; font-size: 18px; }
.muted { margin: 0; opacity: 0.75; font-size: 14px; }
.error { color: #d0563b; }
</style>
