<script setup lang="ts">
// One question the learner snapped: the question itself to solve again (from this device), the
// analysis, and new practice on the same trap. Swipe left and right between the three.
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { DiagnosisReport, QuestionCard, type ErrorLogEntry, type FlagReason, type Item, type Label, type SourceQuestion } from "@questionize/shared";
import SolveAgain from "../components/SolveAgain.vue";
import DetailBar from "../components/DetailBar.vue";
import { withDevice } from "../api";
import { loadQuestion } from "../device";
import { loadReview, type ListName } from "../review";
import { useSwipe } from "../swipe";

const props = defineProps<{ id: number }>();
const route = useRoute();
const router = useRouter();
const TABS = ["question", "analysis", "practice"] as const;
type Tab = (typeof TABS)[number];
const view = computed<Tab>(() => (TABS.includes(route.query.view as Tab) ? (route.query.view as Tab) : "question"));
const list = computed<ListName>(() => (route.query.list === "archived" ? "archived" : "misses"));
const show = (v: Tab) => router.replace({ query: { ...route.query, view: v === "question" ? undefined : v } });

const entry = ref<ErrorLogEntry | null>(null);
const question = ref<SourceQuestion | null>(null);
const error = ref("");
const busy = ref(false);
const practice = reactive(new Map<string, { item: Item; chosen: Label | null; busy: boolean; shownAt: number; note: string }>());

const pane = ref<HTMLElement | null>(null);
useSwipe(pane, {
  left: () => show(TABS[Math.min(TABS.indexOf(view.value) + 1, TABS.length - 1)]),
  right: () => show(TABS[Math.max(TABS.indexOf(view.value) - 1, 0)]),
});

async function load() {
  error.value = "";
  entry.value = null;
  question.value = null;
  practice.clear();
  try {
    entry.value = await withDevice((c) => c.getErrorLogEntry(props.id));
    for (const item of entry.value.practice) practice.set(item.id, { item, chosen: null, busy: false, shownAt: Date.now(), note: "" });
    question.value = await loadQuestion(props.id);
  } catch {
    error.value = "This question isn't available.";
  }
}
watch(() => props.id, load);
onMounted(load);

async function archive(archived: boolean) {
  if (!entry.value) return;
  busy.value = true;
  try {
    entry.value = { ...entry.value, ...(await withDevice((c) => c.archiveEntry(props.id, archived))) };
    await loadReview(list.value);
    if (archived) router.replace(list.value === "archived" ? "/questions?view=archived" : "/questions");
  } catch {
    error.value = "Couldn't update this question. Please try again.";
  } finally {
    busy.value = false;
  }
}

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

async function vote(id: string, kind: "up" | "down") {
  const p = practice.get(id)!;
  const res = await withDevice((c) => c.feedback(id, { kind })).catch(() => null);
  if (res?.votes && p.item.revealed) p.item = { ...p.item, votes: res.votes };
}

async function flag(id: string, reason: FlagReason, comment: string) {
  await withDevice((c) => c.feedback(id, { kind: "flag", reason, comment })).catch(() => (error.value = "Couldn't send your report."));
}
</script>

<template>
  <section class="miss">
    <DetailBar v-if="entry" :list="list" :card-key="`snap:${id}`" :archived="!!entry.archived" :busy="busy" @archive="archive" />
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <template v-if="entry">
      <p v-if="entry.diagnosis.learning_trace" class="hint">
        Answer evidence: {{ entry.diagnosis.learning_trace.reference_status.replaceAll('_', ' ') }} · independent analysis uses memory v{{ entry.diagnosis.learning_trace.policy_version ?? 'baseline' }}.
        <span v-if="['ai_estimated','unconfirmed'].includes(entry.diagnosis.learning_trace.reference_status)">AI agreement is an estimate, not a verified answer key.</span>
      </p>
      <div class="seg" role="tablist" aria-label="This question">
        <button role="tab" :aria-selected="view === 'question'" :class="{ on: view === 'question' }" @click="show('question')">Question</button>
        <button role="tab" :aria-selected="view === 'analysis'" :class="{ on: view === 'analysis' }" @click="show('analysis')">Analysis</button>
        <button role="tab" :aria-selected="view === 'practice'" :class="{ on: view === 'practice' }" @click="show('practice')">Practice · {{ entry.practice.length }}</button>
      </div>

      <div ref="pane" class="pane">
        <template v-if="view === 'question'">
          <SolveAgain v-if="question" :question="question" :diagnosis="entry.diagnosis" />
          <div v-else class="box">
            <p>This question is saved on the device you snapped it with. Open it there to solve it again.</p>
            <button type="button" class="link" @click="show('analysis')">See the analysis</button>
          </div>
        </template>

        <template v-else-if="view === 'analysis'">
          <div v-if="entry.diagnosis.learning_trace?.detailed_explanation_available === false" class="box"><p>{{ entry.diagnosis.explanation }}</p><p>Check your reference before using this as a learning diagnosis. Your captured question is still saved.</p></div>
          <DiagnosisReport v-else :entry="entry" />
          <details v-if="question?.local_reference?.explanation" class="box"><summary>Reference explanation extracted from your photo · saved on this device</summary><p style="white-space:pre-wrap">{{ question.local_reference.explanation }}</p></details>
        </template>

        <template v-else>
          <p v-if="entry.practice.length" class="hint">New questions on different topics, built to practise the same skill. Rate them after you answer.</p>
          <div v-else-if="entry.diagnosis.learning_trace?.detailed_explanation_available === false" class="box"><p>Practice is waiting until the answer and explanation can be checked. No learning diagnosis has been assumed from an unresolved answer.</p></div>
          <div v-else class="box"><p>No practice questions passed verification for this one. Snap another question on the same skill to get more.</p></div>
          <div v-for="item in entry.practice" :key="item.id">
            <template v-if="practice.get(item.id)">
              <QuestionCard
                :item="practice.get(item.id)!.item"
                :chosen="practice.get(item.id)!.chosen"
                :busy="practice.get(item.id)!.busy"
                :locatable="false"
                @answer="(l) => answer(item.id, l)"
                @flag="(r, c) => flag(item.id, r, c)"
                @vote="(k) => vote(item.id, k)"
              />
              <p v-if="practice.get(item.id)!.note" class="hint">{{ practice.get(item.id)!.note }}</p>
            </template>
          </div>
        </template>
      </div>
      <p class="swipe-hint">Swipe left or right to switch between Question, Analysis and Practice</p>
    </template>
    <div v-else-if="!error" class="skeleton" aria-hidden="true"><span /><span /></div>
  </section>
</template>

<style scoped>
.miss { display: flex; flex-direction: column; gap: 12px; }
.pane { min-height: 50vh; }
.hint { margin: 0 0 4px; font-size: 14px; color: var(--muted); line-height: 1.5; }
.box { padding: 16px; border-radius: var(--radius); border: 1px dashed var(--line); color: var(--muted); }
.box p { margin: 0 0 6px; }
.link { background: none; border: 0; padding: 0; color: var(--accent); font: inherit; font-weight: 600; cursor: pointer; }
.error { color: var(--bad); }
.swipe-hint { margin: 8px 0 0; text-align: center; font-size: 12px; color: var(--muted); }
@media (hover: hover) { .swipe-hint { display: none; } }
.skeleton { display: flex; flex-direction: column; gap: 10px; }
.skeleton span { height: 160px; border-radius: var(--radius); background: var(--chip); }
</style>
