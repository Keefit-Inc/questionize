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
          <span class="lbl">{{ c.label }}</span><span>{{ c.text }}</span>
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
.solve { display: flex; flex-direction: column; gap: 10px; padding: 14px; border-radius: 12px; border: 1px solid rgba(127, 127, 127, 0.25); }
.passage { margin: 0; white-space: pre-wrap; line-height: 1.55; }
.stem { margin: 0; font-weight: 600; }
.choices { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px; }
.choices button { width: 100%; text-align: left; display: grid; grid-template-columns: 22px 1fr; gap: 6px; padding: 10px; border-radius: 8px; border: 1px solid rgba(127, 127, 127, 0.3); background: transparent; color: inherit; font: inherit; cursor: pointer; }
.choices button:disabled { cursor: default; }
.choices button.selected { border-color: #3b6fd0; box-shadow: 0 0 0 1px #3b6fd0; }
.choices button.correct { border-color: #2e9d5b; background: rgba(46, 157, 91, 0.1); }
.choices button.wrong { border-color: #d0563b; background: rgba(208, 86, 59, 0.1); }
.lbl { font-weight: 700; }
.why { margin: 4px 0 2px 28px; font-size: 13px; opacity: 0.85; }
.tag { font-style: normal; font-size: 11px; padding: 0 6px; margin-right: 4px; border-radius: 8px; border: 1px solid currentColor; }
.row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.primary { padding: 10px 16px; border-radius: 8px; border: 0; background: #3b6fd0; color: #fff; font: inherit; font-weight: 600; cursor: pointer; }
.primary:disabled { opacity: 0.45; cursor: default; }
.ghost { padding: 8px 12px; border-radius: 8px; border: 1px solid rgba(127, 127, 127, 0.4); background: transparent; color: inherit; font: inherit; cursor: pointer; }
.verdict { margin: 0; font-weight: 700; }
.verdict.good { color: #2e9d5b; }
.verdict.bad { color: #d0563b; }
.note { margin: 0; font-size: 12px; opacity: 0.65; }
</style>
