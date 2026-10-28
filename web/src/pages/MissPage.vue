<script setup lang="ts">
// One question the learner missed: the analysis, the question itself to solve again (from this
// device), and new practice on the same trap.
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { DiagnosisReport, QuestionCard, type ErrorLogEntry, type FlagReason, type Item, type Label, type SourceQuestion } from "@questionize/shared";
import SolveAgain from "../components/SolveAgain.vue";
import { withDevice } from "../api";
import { loadQuestion } from "../device";

const props = defineProps<{ id: number }>();
const route = useRoute();
const router = useRouter();
const view = computed(() => (["solve", "practice"].includes(route.query.view as string) ? (route.query.view as "solve" | "practice") : "analysis"));
const show = (v: "analysis" | "solve" | "practice") => router.replace({ query: v === "analysis" ? {} : { view: v } });

const entry = ref<ErrorLogEntry | null>(null);
const question = ref<SourceQuestion | null>(null);
const error = ref("");
const practice = reactive(new Map<string, { item: Item; chosen: Label | null; busy: boolean; shownAt: number; note: string }>());

onMounted(async () => {
  try {
    entry.value = await withDevice((c) => c.getErrorLogEntry(props.id));
    for (const item of entry.value.practice) practice.set(item.id, { item, chosen: null, busy: false, shownAt: Date.now(), note: "" });
    question.value = await loadQuestion(props.id);
  } catch {
    error.value = "This question isn't available.";
  }
});

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
  <section class="miss">
    <RouterLink to="/questions" class="back">← My misses</RouterLink>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <template v-if="entry">
      <div class="seg" role="tablist" aria-label="This question">
        <button role="tab" :aria-selected="view === 'analysis'" :class="{ on: view === 'analysis' }" @click="show('analysis')">Analysis</button>
        <button role="tab" :aria-selected="view === 'solve'" :class="{ on: view === 'solve' }" @click="show('solve')">Solve again</button>
        <button role="tab" :aria-selected="view === 'practice'" :class="{ on: view === 'practice' }" @click="show('practice')">Practice ({{ entry.practice.length }})</button>
      </div>

      <DiagnosisReport v-if="view === 'analysis'" :entry="entry" />

      <template v-else-if="view === 'solve'">
        <SolveAgain v-if="question" :question="question" :diagnosis="entry.diagnosis" />
        <p v-else class="muted box">This question is saved on the device you snapped it with. Open it there to solve it again.</p>
      </template>

      <template v-else>
        <p v-if="entry.practice.length" class="muted">New questions on different topics, built to catch the same mistake. Only your first answer counts.</p>
        <p v-else class="muted box">No practice questions passed verification for this one. Snap another question on the same skill to get more.</p>
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
    </template>
    <p v-else-if="!error" class="muted">Loading…</p>
  </section>
</template>

<style scoped>
.miss { display: flex; flex-direction: column; gap: 12px; }
.back { text-decoration: none; font-size: 14px; }
.muted { margin: 0; opacity: 0.75; font-size: 14px; }
.box { padding: 14px; border-radius: 12px; border: 1px dashed rgba(127, 127, 127, 0.4); }
.error { color: #d0563b; }
.seg { display: grid; grid-template-columns: repeat(3, 1fr); padding: 3px; border-radius: 10px; background: rgba(127, 127, 127, 0.14); }
.seg button { padding: 8px 4px; border: 0; border-radius: 8px; background: transparent; color: inherit; font: inherit; font-size: 14px; font-weight: 600; opacity: 0.65; cursor: pointer; }
.seg button.on { background: Canvas; opacity: 1; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12); }
</style>
