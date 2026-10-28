<script setup lang="ts">
// The learner's own question, from this device, to solve again. The key and the option reviews
// stay hidden until they answer.
import { computed, ref } from "vue";
import { TRAP_LABELS, passageSegments, type Diagnosis, type Label, type SourceQuestion, type TrapType } from "@questionize/shared";

const props = defineProps<{ question: SourceQuestion; diagnosis: Diagnosis }>();
const picked = ref<Label | null>(null);
const checked = ref(false);
const key = computed(() => props.diagnosis.key_guess);
const reviews = computed(() => new Map((props.diagnosis.option_reviews ?? []).map((r) => [r.label, r])));
const trap = (t: TrapType) => (t === "correct" ? "Answer" : (TRAP_LABELS[t as Exclude<TrapType, "correct">] ?? t));

function reset() {
  picked.value = null;
  checked.value = false;
}
</script>

<template>
  <article class="solve">
    <p v-if="question.passage" class="passage">
      <template v-for="(seg, i) in passageSegments(question.passage)" :key="i">
        <u v-if="seg.underlined">{{ seg.text }}</u><template v-else>{{ seg.text }}</template>
      </template>
    </p>
    <p class="stem">{{ question.stem }}</p>
    <ul class="choices">
      <li v-for="c in question.choices" :key="c.label">
        <button
          type="button"
          :disabled="checked"
          :class="{ selected: picked === c.label, correct: checked && c.label === key, wrong: checked && picked === c.label && c.label !== key }"
          @click="picked = c.label"
        >
          <span class="lbl" :class="{ right: checked && c.label === key, wrong: checked && picked === c.label && c.label !== key }">
            <template v-if="checked && c.label === key">✓</template>
            <template v-else-if="checked && picked === c.label">✕</template>
            <template v-else>{{ c.label }}</template>
          </span>
          <span>{{ c.text }}</span>
        </button>
        <p v-if="checked && reviews.get(c.label)?.reason" class="why">
          <em class="tag">{{ trap(reviews.get(c.label)!.trap) }}</em> {{ reviews.get(c.label)!.reason }}
        </p>
      </li>
    </ul>
    <div class="row">
      <button v-if="!checked" type="button" class="primary" :disabled="!picked" @click="checked = true">Check answer</button>
      <template v-else>
        <p class="verdict" :class="picked === key ? 'good' : 'bad'">
          {{ picked === key ? `Right: ${key}` : key ? `Not quite. The answer is most likely ${key}.` : "We couldn't determine the answer to this one." }}
        </p>
        <button type="button" class="ghost" @click="reset">Try again</button>
      </template>
    </div>
    <p class="note">Saved only on this device, from your own book.</p>
  </article>
</template>

<style scoped>
.solve { display: flex; flex-direction: column; gap: 12px; padding: 18px; border-radius: var(--radius); border: 1px solid var(--line); background: var(--surface); box-shadow: var(--shadow); }
.passage { margin: 0; white-space: pre-wrap; font-family: var(--serif); font-size: 16.5px; line-height: 1.6; }
.stem { margin: 0; font-weight: 700; line-height: 1.45; }
.choices { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px; }
.choices button { width: 100%; text-align: left; display: grid; grid-template-columns: 26px 1fr; align-items: start; gap: 10px; padding: 12px; border-radius: 12px; border: 1px solid var(--line); background: transparent; line-height: 1.4; color: inherit; font: inherit; cursor: pointer; }
.choices button:disabled { cursor: default; }
.choices button.selected { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); background: var(--accent-soft); }
.choices button.correct { border-color: var(--good); background: var(--good-soft); }
.choices button.wrong { border-color: var(--bad); background: var(--bad-soft); }
.lbl { width: 26px; height: 26px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-weight: 800; font-size: 13px; background: var(--chip); }
.choices button.selected .lbl { background: var(--accent); color: #fff; }
.lbl.right { background: var(--good); color: #fff; }
.lbl.wrong { background: var(--bad); color: #fff; }
.why { margin: 4px 0 2px 28px; font-size: 13px; opacity: 0.85; }
.tag { font-style: normal; font-size: 11px; padding: 0 6px; margin-right: 4px; border-radius: 8px; border: 1px solid currentColor; }
.row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.primary { padding: 11px 18px; border-radius: 10px; border: 0; background: var(--accent); color: #fff; font: inherit; font-weight: 600; cursor: pointer; }
.primary:disabled { opacity: 0.45; cursor: default; }
.ghost { padding: 8px 12px; border-radius: 8px; border: 1px solid var(--line); background: transparent; color: inherit; font: inherit; cursor: pointer; }
.verdict { margin: 0; font-weight: 800; font-size: 17px; }
.verdict.good { color: var(--good); }
.verdict.bad { color: var(--bad); }
.note { margin: 0; font-size: 12px; opacity: 0.65; }
</style>
