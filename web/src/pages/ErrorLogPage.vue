<script setup lang="ts">
// The learner's error log: the traps that keep catching them, and every question they've analyzed.
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { FAMILY_LABELS, TRAP_LABELS, subtypeLabel, type ErrorLogPage, type QuestionType, type TrapType } from "@questionize/shared";
import { withDevice } from "../api";
import { photoUrl } from "../photos";

const page = ref<ErrorLogPage | null>(null);
const thumbs = reactive(new Map<number, string>());
const gate = reactive({ country: "US", age: false });
const error = ref("");

const traps = computed(() =>
  Object.entries(page.value?.weaknesses.traps ?? {}).slice(0, 4).map(([trap, count]) => ({ label: TRAP_LABELS[trap as Exclude<TrapType, "correct">] ?? trap, count })),
);
const maxTrap = computed(() => Math.max(1, ...traps.value.map((t) => t.count)));

async function load() {
  try {
    page.value = await withDevice((c) => c.listErrorLog());
    for (const e of page.value.entries) {
      const url = await photoUrl(e.id);
      if (url) thumbs.set(e.id, url);
    }
  } catch {
    error.value = "Couldn't load your error log.";
  }
}

async function confirm() {
  error.value = "";
  try {
    const res = await withDevice((c) => c.setEligibility(gate.country, gate.age));
    if (!res.error_log) error.value = "Photo analysis is open in the United States for ages 13 and up for now.";
    await load();
  } catch {
    error.value = "Couldn't save that. Please try again.";
  }
}

onMounted(load);
onBeforeUnmount(() => thumbs.forEach((url) => URL.revokeObjectURL(url)));
</script>

<template>
  <section class="log">
    <h1>Error log</h1>
    <p class="lede">Photograph a question you got wrong. You'll see what it tests, how hard it is, why your answer was tempting, and new questions that train the same skill.</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <form v-if="page && !page.eligible" class="gate" @submit.prevent="confirm">
      <label>Where do you live?
        <select v-model="gate.country">
          <option value="US">United States</option>
          <option value="ZZ">Somewhere else</option>
        </select>
      </label>
      <label class="check"><input v-model="gate.age" type="checkbox" /> I am 13 or older</label>
      <button type="submit" class="go" :disabled="!gate.age">Continue</button>
    </form>

    <template v-else-if="page">
      <RouterLink to="/error-log/new" class="go cta">Add a question I missed</RouterLink>

      <section v-if="traps.length" class="traps">
        <h2>Traps that keep catching you</h2>
        <ul>
          <li v-for="t in traps" :key="t.label">
            <span>{{ t.label }}</span>
            <span class="bar"><span :style="{ width: (t.count / maxTrap) * 100 + '%' }" /></span>
            <span class="count">{{ t.count }}</span>
          </li>
        </ul>
      </section>

      <ul class="entries">
        <li v-for="e in page.entries" :key="e.id">
          <RouterLink :to="`/error-log/${e.id}`" class="entry">
            <img v-if="thumbs.get(e.id)" :src="thumbs.get(e.id)" alt="" class="thumb" />
            <span v-else class="thumb blank" aria-hidden="true">{{ e.diagnosis.family }}</span>
            <span class="text">
              <strong>{{ [e.book, e.page && `p. ${e.page}`, e.number && `#${e.number}`].filter(Boolean).join(" · ") || "Photographed question" }}</strong>
              <span class="muted">{{ FAMILY_LABELS[e.diagnosis.family as QuestionType] ?? e.diagnosis.family }} · {{ subtypeLabel(e.diagnosis.subtype) }}<template v-if="e.diagnosis.difficulty"> · difficulty {{ e.diagnosis.difficulty }}/5</template></span>
              <span v-if="e.diagnosis.misconception" class="muted">{{ e.diagnosis.misconception.statement }}</span>
            </span>
          </RouterLink>
        </li>
      </ul>
      <p v-if="!page.entries.length" class="muted">Nothing here yet. Your first photo starts the log.</p>
    </template>
  </section>
</template>

<style scoped>
.log { display: flex; flex-direction: column; gap: 14px; }
h1 { margin: 0; font-size: 22px; }
h2 { margin: 0 0 8px; font-size: 14px; letter-spacing: 0.04em; text-transform: uppercase; opacity: 0.7; }
.lede, .muted { margin: 0; opacity: 0.75; }
.muted { font-size: 13px; }
.error { color: #d0563b; margin: 0; }
.gate { display: flex; flex-direction: column; gap: 10px; padding: 14px; border-radius: 12px; border: 1px solid rgba(127, 127, 127, 0.3); }
.gate label { display: flex; flex-direction: column; gap: 4px; }
.gate .check { flex-direction: row; align-items: center; gap: 8px; }
.gate select { font: inherit; padding: 8px; border-radius: 8px; }
.go { display: block; text-align: center; padding: 14px; border-radius: 12px; border: 0; background: #3b6fd0; color: #fff !important; font: inherit; font-weight: 700; text-decoration: none; cursor: pointer; }
.go:disabled { opacity: 0.45; }
.traps ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.traps li { display: grid; grid-template-columns: 9rem 1fr 2rem; align-items: center; gap: 8px; font-size: 14px; }
.bar { height: 8px; border-radius: 4px; background: rgba(127, 127, 127, 0.15); overflow: hidden; }
.bar span { display: block; height: 100%; background: #d0563b; }
.count { text-align: right; font-variant-numeric: tabular-nums; }
.entries { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.entry { display: flex; gap: 12px; padding: 10px; border-radius: 12px; border: 1px solid rgba(127, 127, 127, 0.25); color: inherit; text-decoration: none; }
.thumb { width: 56px; height: 56px; border-radius: 8px; object-fit: cover; flex: none; }
.thumb.blank { display: flex; align-items: center; justify-content: center; background: rgba(127, 127, 127, 0.12); font-weight: 700; font-size: 13px; }
.text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
</style>
