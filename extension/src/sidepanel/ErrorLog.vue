<script setup lang="ts">
// The error log (docs/KNOWLEDGE_MODEL.md §9): photograph one question you missed, get a diagnosis
// and fresh practice on the same trap. The photo is read once and deleted on the server.
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import {
  ApiClient,
  QuestionCard,
  TRAP_LABELS,
  eventKey,
  replayRunState,
  subscribeToGeneration,
  type ErrorLogEntry,
  type ErrorLogPage,
  type FlagReason,
  type GenerationEvent,
  type Item,
  type Label,
  type TrapType,
} from "@questionize/shared";
import { errorMessage, eventLine } from "./messages";
import { photoDataUrl } from "./photo";

const props = defineProps<{ connect: () => Promise<ApiClient>; server: string }>();

interface Practice {
  item: Item;
  chosen: Label | null;
  busy: boolean;
  shownAt: number;
}

const LABELS: Label[] = ["A", "B", "C", "D", "E"];
const page = ref<ErrorLogPage | null>(null);
const practice = reactive(new Map<string, Practice>());
const gate = reactive({ country: "US", age: false });
const form = reactive({ book: "", page: "", number: "", chosen: "" as Label | "" });
const file = ref<File | null>(null);
const running = ref(false);
const log = ref<{ who: string; text: string; ok?: boolean }[]>([]);
const error = ref("");
const seen = new Set<string>();
let closeStream: (() => void) | null = null;

const topTraps = computed(() =>
  Object.entries(page.value?.weaknesses.traps ?? {})
    .slice(0, 3)
    .map(([trap, count]) => ({ label: TRAP_LABELS[trap as Exclude<TrapType, "correct">] ?? trap, count })),
);

function track(entries: ErrorLogEntry[]) {
  for (const item of entries.flatMap((e) => e.practice)) {
    const existing = practice.get(item.id);
    if (!existing) practice.set(item.id, { item, chosen: null, busy: false, shownAt: Date.now() });
    else if (item.revealed) existing.item = item;
  }
}

async function load() {
  try {
    page.value = await (await props.connect()).listErrorLog();
    track(page.value.entries);
  } catch (e) {
    error.value = errorMessage(e, props.server);
  }
}

async function confirmEligibility() {
  error.value = "";
  try {
    const res = await (await props.connect()).setEligibility(gate.country, gate.age);
    if (!res.error_log) error.value = "Photo capture is available in the United States for ages 13 and up.";
    await load();
  } catch (e) {
    error.value = errorMessage(e, props.server);
  }
}

function onEvent(event: GenerationEvent) {
  const key = event.stage === "diagnosis" ? `diagnosis|${event.entry.id}` : eventKey(event);
  if (seen.has(key)) return;
  seen.add(key);
  if (event.stage === "diagnosis" && page.value) {
    page.value.entries = [event.entry, ...page.value.entries.filter((e) => e.id !== event.entry.id)];
    track([event.entry]);
  }
  const line = eventLine(event);
  if (line) log.value.push(line);
  if (event.stage === "failed" || event.stage === "declined") error.value = event.message;
  if (event.stage === "done" || event.stage === "failed" || event.stage === "declined") {
    running.value = false;
    if (event.stage === "done" && ![...seen].some((k) => k.startsWith("diagnosis|"))) error.value = "Couldn't read a question in that photo. Try a sharper, closer shot.";
    // Weaknesses are recounted on the server.
    if (event.stage === "done") load();
  }
}

async function capture() {
  if (running.value || !file.value) return;
  error.value = "";
  log.value = [{ who: "Reader", text: "Preparing the photo" }];
  running.value = true;
  try {
    const api = await props.connect();
    const image = await photoDataUrl(file.value);
    const res = await api.captureErrorLog({
      image,
      book: form.book || undefined,
      page: form.page || undefined,
      number: form.number || undefined,
      chosen_label: form.chosen || undefined,
    });
    file.value = null;
    closeStream?.();
    seen.clear();
    closeStream = subscribeToGeneration(api.cableUrl(), res.run_id, onEvent, {
      onConnected: async () => {
        for (const e of replayRunState(await api.getRun(res.run_id))) onEvent(e);
      },
      onRejected: () => {
        error.value = "Couldn't follow the diagnosis. Reopen the panel and try again.";
        running.value = false;
      },
    });
  } catch (e) {
    error.value = errorMessage(e, props.server);
    running.value = false;
  }
}

async function answer(p: Practice, label: Label) {
  p.busy = true;
  try {
    const res = await (await props.connect()).attempt(p.item.id, label, Date.now() - p.shownAt);
    p.item = res.item;
    p.chosen = label;
  } catch (e) {
    error.value = errorMessage(e, props.server);
  } finally {
    p.busy = false;
  }
}

async function flag(p: Practice, reason: FlagReason, comment: string) {
  try {
    await (await props.connect()).feedback(p.item.id, { kind: "flag", reason, comment });
  } catch (e) {
    error.value = errorMessage(e, props.server);
  }
}

function where(entry: ErrorLogEntry): string {
  const parts = [entry.book, entry.page && `p. ${entry.page}`, entry.number && `#${entry.number}`].filter(Boolean);
  return parts.length ? parts.join(" · ") : "Photographed question";
}

onMounted(load);
onBeforeUnmount(() => closeStream?.());
</script>

<template>
  <section v-if="page && !page.eligible" class="card">
    <p class="head">Photograph a question you missed</p>
    <p class="small">We read the photo once, then delete it. We keep where the question is in your book, your answer, and our diagnosis. Photo capture is open in the United States for ages 13 and up.</p>
    <label class="field">Country
      <select v-model="gate.country">
        <option value="US">United States</option>
        <option value="ZZ">Somewhere else</option>
      </select>
    </label>
    <label class="check"><input v-model="gate.age" type="checkbox" /> I am 13 or older</label>
    <button class="primary" :disabled="!gate.age" @click="confirmEligibility">Continue</button>
  </section>

  <section v-else-if="page" class="card">
    <p class="head">Add a missed question</p>
    <input type="file" accept="image/*" aria-label="Photo of the question" @change="file = ($event.target as HTMLInputElement).files?.[0] ?? null" />
    <div class="grid">
      <input v-model.trim="form.book" placeholder="Book (optional)" maxlength="200" />
      <input v-model.trim="form.page" placeholder="Page" maxlength="20" />
      <input v-model.trim="form.number" placeholder="Question #" maxlength="20" />
      <select v-model="form.chosen" aria-label="Your answer">
        <option value="">My answer</option>
        <option v-for="l in LABELS" :key="l" :value="l">{{ l }}</option>
      </select>
    </div>
    <p class="small">Only one question per photo. The photo is deleted as soon as it's read; nothing from it is published.</p>
    <button class="primary" :disabled="running || !file" @click="capture">{{ running ? "Diagnosing…" : "Diagnose" }}</button>
  </section>

  <ol v-if="log.length" class="log" aria-live="polite">
    <li v-for="(line, i) in log" :key="i" :class="{ fail: line.ok === false }"><span class="who">{{ line.who }}</span> {{ line.text }}</li>
  </ol>
  <p v-if="error" class="error" role="alert">{{ error }}</p>

  <section v-if="topTraps.length" class="card">
    <p class="head">Traps that keep catching you</p>
    <ul class="traps">
      <li v-for="t in topTraps" :key="t.label">{{ t.label }} <span class="small">×{{ t.count }}</span></li>
    </ul>
  </section>

  <article v-for="entry in page?.entries ?? []" :key="entry.id" class="card">
    <p class="head">{{ where(entry) }}</p>
    <p class="small">
      {{ entry.diagnosis.competency }}
      <template v-if="entry.chosen_label"> · you chose {{ entry.chosen_label }}</template>
      <template v-if="entry.diagnosis.key_guess"> · likely answer {{ entry.diagnosis.key_guess }}</template>
    </p>
    <p v-if="entry.diagnosis.misconception" class="why">{{ entry.diagnosis.misconception.statement }}</p>
    <p>{{ entry.diagnosis.explanation }}</p>
    <p v-if="entry.contributed" class="small">This pattern (no wording from your book) now helps improve questions for everyone.</p>
    <p v-if="entry.practice.length" class="sub">Practice the same trap</p>
    <template v-for="item in entry.practice" :key="item.id">
      <QuestionCard
        v-if="practice.get(item.id)"
        :item="practice.get(item.id)!.item"
        :chosen="practice.get(item.id)!.chosen"
        :busy="practice.get(item.id)!.busy"
        :locatable="false"
        @answer="(l) => answer(practice.get(item.id)!, l)"
        @flag="(r, c) => flag(practice.get(item.id)!, r, c)"
      />
    </template>
  </article>
  <p v-if="page?.eligible && !page.entries.length && !running" class="small">Your error log is empty. Photograph a question you got wrong to start it.</p>
</template>

<style scoped>
.card { margin: 10px 0; padding: 10px; border-radius: 10px; background: rgba(127, 127, 127, 0.08); display: flex; flex-direction: column; gap: 8px; }
.card p { margin: 0; }
.head { font-weight: 700; }
.sub { font-weight: 600; margin-top: 6px !important; }
.small { font-size: 12px; opacity: 0.75; }
.why { font-style: italic; }
.field { display: flex; flex-direction: column; gap: 4px; font-size: 13px; }
.check { font-size: 13px; display: flex; gap: 6px; align-items: center; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.grid input, .grid select, .field select { padding: 6px; border-radius: 6px; border: 1px solid rgba(127, 127, 127, 0.4); font: inherit; }
.primary { padding: 10px; border-radius: 8px; border: 0; background: #3b6fd0; color: #fff; cursor: pointer; }
.primary:disabled { opacity: 0.6; }
.log { margin: 8px 0; padding-left: 18px; font-size: 12px; }
.log .who { font-weight: 600; }
.log .fail { color: #d0563b; }
.error { color: #d0563b; font-size: 13px; }
.traps { margin: 0; padding-left: 18px; }
</style>
