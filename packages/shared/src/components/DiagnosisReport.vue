<script setup lang="ts">
// The analysis of one photographed question: what it tests, how hard it is, why the learner's
// choice was tempting, and every option explained. All text is ours; nothing quotes their book.
import { computed } from "vue";
import type { ErrorLogEntry } from "../api";
import { FAMILY_LABELS, TRAP_LABELS, subtypeLabel } from "../labels";
import type { QuestionType, TrapType } from "../types";

const props = defineProps<{ entry: ErrorLogEntry; photoUrl?: string | null }>();

const LEVELS = ["", "Warm-up", "Easier than average", "Typical test item", "Harder than average", "Among the hardest"];
const d = computed(() => props.entry.diagnosis);
const family = computed(() => FAMILY_LABELS[d.value.family as QuestionType] ?? d.value.family);
const chosen = computed(() => props.entry.chosen_label ?? d.value.chosen_label);
const trapLabel = (trap: TrapType | string | null | undefined) => (trap && trap !== "correct" ? (TRAP_LABELS[trap as Exclude<TrapType, "correct">] ?? trap) : "");
const where = computed(() => {
  const e = props.entry;
  const parts = [e.book, e.page && `p. ${e.page}`, e.number && `#${e.number}`].filter(Boolean);
  return parts.length ? parts.join(" · ") : "Photographed question";
});
const verdict = computed(() => {
  if (!chosen.value) return d.value.key_guess ? `Likely answer ${d.value.key_guess}` : "";
  if (d.value.chosen_correct) return `You chose ${chosen.value}: that's the answer we reach too`;
  return d.value.key_guess ? `You chose ${chosen.value} · the answer is most likely ${d.value.key_guess}` : `You chose ${chosen.value}`;
});
</script>

<template>
  <article class="qz-report-card">
    <header class="qz-dx-head">
      <img v-if="photoUrl" :src="photoUrl" alt="Your photo of the question" class="qz-dx-photo" />
      <div class="qz-dx-title">
        <p class="qz-dx-where">{{ where }}</p>
        <div class="qz-dx-tags">
          <span class="qz-tag">{{ family }}</span>
          <span class="qz-tag">{{ subtypeLabel(d.subtype) }}</span>
        </div>
        <p v-if="verdict" class="qz-dx-verdict" :class="d.chosen_correct ? 'good' : chosen ? 'bad' : ''">{{ verdict }}</p>
      </div>
    </header>

    <section v-if="d.difficulty" class="qz-dx-section">
      <h3>Difficulty</h3>
      <div class="qz-dx-meter" role="img" :aria-label="`Difficulty ${d.difficulty} of 5`">
        <span v-for="n in 5" :key="n" :class="{ on: n <= (d.difficulty ?? 0) }" />
        <strong>{{ d.difficulty }}/5</strong>
        <span class="qz-dx-muted">{{ LEVELS[d.difficulty] }}</span>
      </div>
      <ul v-if="d.difficulty_drivers?.length" class="qz-dx-list qz-dx-muted">
        <li v-for="driver in d.difficulty_drivers" :key="driver">{{ driver }}</li>
      </ul>
    </section>

    <section v-if="d.intent || d.competency" class="qz-dx-section">
      <h3>What the question tests</h3>
      <p v-if="d.intent">{{ d.intent }}</p>
      <p v-if="d.competency" class="qz-dx-muted">Skill: {{ d.competency }}</p>
    </section>

    <section v-if="d.chosen_trap || d.misconception" class="qz-dx-section qz-dx-why">
      <h3>Why {{ chosen ?? "the wrong answer" }} was tempting</h3>
      <p v-if="d.chosen_trap"><span class="qz-trap">{{ trapLabel(d.chosen_trap) }}</span></p>
      <p v-if="d.misconception">{{ d.misconception.statement }}</p>
    </section>

    <section v-if="d.learning_objectives?.length" class="qz-dx-section">
      <h3>What to practice</h3>
      <ul class="qz-dx-list">
        <li v-for="goal in d.learning_objectives" :key="goal">{{ goal }}</li>
      </ul>
    </section>

    <section class="qz-dx-section">
      <h3>Explanation</h3>
      <p>{{ d.explanation }}</p>
      <ul v-if="d.option_reviews?.length" class="qz-dx-options">
        <li
          v-for="review in d.option_reviews"
          :key="review.label"
          :class="{ key: review.trap === 'correct', chosen: review.label === chosen && review.trap !== 'correct' }"
        >
          <span class="qz-lbl">{{ review.label }}</span>
          <span>
            <em v-if="review.trap === 'correct'" class="qz-trap">Answer</em>
            <em v-else class="qz-trap">{{ trapLabel(review.trap) }}</em>
            <em v-if="review.label === chosen" class="qz-trap">Your choice</em>
            {{ review.reason || "We couldn't explain this option without quoting it." }}
          </span>
        </li>
      </ul>
    </section>

    <p class="qz-dx-muted qz-dx-foot">
      Our analysis, in our own words. We read your photo once and delete it; it stays only on this device.
      <template v-if="entry.contributed"> The question's abstract design, with nothing from your book, now helps improve questions for everyone.</template>
    </p>
  </article>
</template>

<style scoped>
.qz-report-card { display: flex; flex-direction: column; gap: 12px; }
.qz-dx-head { display: flex; gap: 12px; align-items: flex-start; padding: 16px; border-radius: var(--radius, 12px); background: var(--surface, transparent); border: 1px solid var(--line, rgba(127, 127, 127, 0.25)); }
.qz-dx-photo { width: 84px; height: 84px; object-fit: cover; border-radius: 8px; border: 1px solid rgba(127, 127, 127, 0.3); flex: none; }
.qz-dx-title { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.qz-dx-where { margin: 0; font-weight: 700; }
.qz-dx-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.qz-tag { font-size: 11px; font-weight: 600; padding: 3px 9px; border-radius: 999px; background: var(--chip, rgba(127, 127, 127, 0.15)); }
.qz-dx-verdict { margin: 0; font-weight: 800; font-size: 18px; line-height: 1.3; }
.qz-dx-verdict.good { color: var(--good, #2e9d5b); }
.qz-dx-verdict.bad { color: var(--bad, #d0563b); }
.qz-dx-section { display: flex; flex-direction: column; gap: 8px; padding: 16px; border-radius: var(--radius, 12px); background: var(--surface, transparent); border: 1px solid var(--line, rgba(127, 127, 127, 0.25)); }
.qz-dx-section h3 { margin: 0; font-size: 11px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted, inherit); opacity: 0.9; }
.qz-dx-section p { margin: 0; line-height: 1.55; }
.qz-dx-why { background: var(--bad-soft, rgba(208, 86, 59, 0.08)); border-color: transparent; }
.qz-dx-why p:last-child { font-size: 16px; font-weight: 600; }
.qz-dx-meter { display: flex; align-items: center; gap: 5px; }
.qz-dx-meter > span:not(.qz-dx-muted) { width: 28px; height: 10px; border-radius: 5px; background: var(--chip, rgba(127, 127, 127, 0.2)); }
.qz-dx-meter > span.on { background: var(--warn, #b7791f); }
.qz-dx-meter strong { margin-left: 8px; font-size: 18px; font-variant-numeric: tabular-nums; }
.qz-dx-meter .qz-dx-muted { margin-left: 4px; }
.qz-dx-list { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 6px; }
.qz-dx-list li { position: relative; padding-left: 22px; line-height: 1.45; }
.qz-dx-list li::before { content: ""; position: absolute; left: 4px; top: 0.55em; width: 8px; height: 8px; border-radius: 50%; background: var(--accent, #3b6fd0); }
.qz-dx-list.qz-dx-muted li::before { background: var(--warn, #b7791f); }
.qz-dx-options { list-style: none; padding: 0; margin: 4px 0 0; display: flex; flex-direction: column; gap: 6px; font-size: 14px; }
.qz-dx-options li { display: grid; grid-template-columns: 22px 1fr; gap: 8px; padding: 10px 12px; border-radius: 10px; background: var(--chip, rgba(127, 127, 127, 0.08)); line-height: 1.45; }
.qz-dx-options li.key { background: var(--good-soft, rgba(46, 157, 91, 0.1)); }
.qz-dx-options li.chosen { background: var(--bad-soft, rgba(208, 86, 59, 0.08)); }
.qz-lbl { font-weight: 800; }
.qz-trap { font-style: normal; font-size: 11px; font-weight: 600; padding: 1px 7px; margin-right: 4px; border-radius: 999px; border: 1px solid currentColor; opacity: 0.85; }
.qz-dx-muted { color: var(--muted, inherit); font-size: 13px; }
.qz-dx-foot { font-size: 12px; padding: 0 4px; }
</style>
