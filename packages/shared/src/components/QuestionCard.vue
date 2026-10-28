<script setup lang="ts">
import { computed, ref } from "vue";
import type { FlagReason, Item } from "../api";
import type { Label } from "../types";
import { FAMILY_LABELS, TRAP_LABELS, passageSegments, subtypeLabel } from "../labels";
import ChoiceDistribution from "./ChoiceDistribution.vue";
import JudgeMeter from "./JudgeMeter.vue";

// `locatable`: the card sits next to the source page (the extension), so "Show in article" can work.
const props = withDefaults(defineProps<{ item: Item; chosen?: Label | null; busy?: boolean; locatable?: boolean }>(), {
  chosen: null,
  busy: false,
  locatable: true,
});
const emit = defineEmits<{ answer: [label: Label]; locate: [anchor: string]; flag: [reason: FlagReason, comment: string] }>();

const FLAG_REASONS: { value: FlagReason; label: string }[] = [
  { value: "two_answers", label: "More than one answer is defensible" },
  { value: "wrong_key", label: "The keyed answer is wrong" },
  { value: "unclear", label: "The question is unclear" },
  { value: "typo", label: "Typo or wording error" },
  { value: "offensive", label: "Offensive or inappropriate" },
  { value: "other", label: "Something else" },
];
const reporting = ref(false);
const flagReason = ref<FlagReason>("two_answers");
const flagComment = ref("");
const flagged = ref(false);

function sendFlag() {
  emit("flag", flagReason.value, flagComment.value.trim());
  flagged.value = true;
  reporting.value = false;
}

const picked = ref<Label | null>(null);
const selected = computed(() => props.chosen ?? picked.value);
const revealed = computed(() => (props.item.revealed ? props.item : null));
const correct = computed(() => revealed.value !== null && selected.value === revealed.value.correct_label);
const chosenTrap = computed(() => {
  const r = revealed.value?.rationales.find((x) => x.label === selected.value);
  return r && r.trap !== "correct" ? TRAP_LABELS[r.trap] : null;
});

function choiceClass(label: Label) {
  if (!revealed.value) return { selected: picked.value === label };
  return { correct: label === revealed.value.correct_label, wrong: label === selected.value && !correct.value };
}

function check() {
  if (picked.value && !props.busy) emit("answer", picked.value);
}
</script>

<template>
  <article class="qz-card">
    <header class="qz-card-head">
      <span class="qz-tag">{{ FAMILY_LABELS[item.family] }}</span>
      <span class="qz-tag">{{ subtypeLabel(item.subtype) }}</span>
      <span v-if="item.version > 1" class="qz-tag revised" title="Replaced by a re-review after reader reports">v{{ item.version }} · revised</span>
      <span class="qz-badge" :class="item.verified ? 'verified' : 'unverified'">
        {{ item.status === "under_review" ? "⟳ Under review" : item.verified ? "✓ Verified" : "⚠ Unverified" }}
      </span>
    </header>

    <p class="qz-passage">
      <template v-for="(seg, i) in passageSegments(item.passage)" :key="i"><u v-if="seg.underlined">{{ seg.text }}</u><template v-else>{{ seg.text }}</template></template>
    </p>
    <p class="qz-stem">{{ item.stem }}</p>

    <ol class="qz-choices">
      <li v-for="choice in item.choices" :key="choice.label">
        <button type="button" :class="choiceClass(choice.label)" :disabled="!!revealed || busy" @click="picked = choice.label">
          <span class="qz-lbl">{{ choice.label }}</span><span>{{ choice.text }}</span>
        </button>
      </li>
    </ol>

    <div v-if="!revealed" class="qz-actions">
      <button type="button" class="qz-primary" :disabled="!picked || busy" @click="check">{{ busy ? "Checking…" : "Check answer" }}</button>
    </div>

    <div v-else class="qz-reveal">
      <p class="qz-verdict" :class="correct ? 'good' : 'bad'">
        <template v-if="correct">Correct — {{ revealed.correct_label }}</template>
        <template v-else>Not quite. You chose {{ selected }}<template v-if="chosenTrap"> (trap: {{ chosenTrap }})</template>; the answer is {{ revealed.correct_label }}.</template>
      </p>
      <p class="qz-explanation">{{ revealed.explanation }}</p>

      <JudgeMeter v-if="revealed.judge" :judge="revealed.judge" :correct-label="revealed.correct_label" :chosen="selected" />
      <ChoiceDistribution :tally="revealed.tally" :correct-label="revealed.correct_label" :chosen="selected" />

      <details class="qz-details" :open="!correct">
        <summary>Why each option is right or wrong</summary>
        <ol class="qz-rationales">
          <li v-for="r in revealed.rationales" :key="r.label" :class="{ key: r.label === revealed.correct_label }">
            <strong>{{ r.label }}</strong>
            <span><em v-if="r.trap !== 'correct'" class="qz-trap">{{ TRAP_LABELS[r.trap] }}</em> {{ r.rationale }}</span>
          </li>
        </ol>
      </details>

      <details class="qz-details">
        <summary>How this question was verified</summary>
        <p class="qz-small">
          Blind solver ({{ revealed.verification.solver_model }}) chose {{ revealed.verification.solver_answer || "–" }}
          · critic {{ revealed.verification.critic_verdict }} · {{ revealed.verification.attempts }} draft(s)
        </p>
        <ul v-if="revealed.verification.issues?.length" class="qz-small">
          <li v-for="(issue, i) in revealed.verification.issues" :key="i">{{ issue }}</li>
        </ul>
      </details>

      <div class="qz-row">
        <button v-if="locatable && revealed.source_anchor" type="button" class="qz-ghost" @click="emit('locate', revealed.source_anchor!)">Show in article</button>
        <button v-if="!flagged" type="button" class="qz-ghost" @click="reporting = !reporting">Report a problem</button>
        <span v-else class="qz-small">Thanks. Reports like yours trigger an automatic re-review.</span>
      </div>
      <form v-if="reporting" class="qz-report" @submit.prevent="sendFlag">
        <select v-model="flagReason" aria-label="What is wrong?">
          <option v-for="r in FLAG_REASONS" :key="r.value" :value="r.value">{{ r.label }}</option>
        </select>
        <textarea v-model="flagComment" maxlength="1000" rows="2" placeholder="Optional: what did you notice?"></textarea>
        <button type="submit" class="qz-primary">Send report</button>
      </form>
    </div>
  </article>
</template>

<style scoped>
.qz-card { border: 1px solid rgba(127, 127, 127, 0.25); border-radius: 12px; padding: 14px; margin: 12px 0; }
.qz-card-head { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-bottom: 8px; }
.qz-tag { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: rgba(127, 127, 127, 0.15); }
.qz-badge { font-size: 11px; margin-left: auto; }
.qz-badge.verified { color: #2e9d5b; }
.qz-badge.unverified { color: #b7791f; }
.qz-passage { white-space: pre-wrap; line-height: 1.5; font-size: 14px; }
.qz-stem { font-weight: 600; }
.qz-choices { list-style: none; padding: 0; margin: 8px 0; display: flex; flex-direction: column; gap: 6px; }
.qz-choices button { width: 100%; text-align: left; display: grid; grid-template-columns: 22px 1fr; gap: 6px; padding: 8px; border-radius: 8px; border: 1px solid rgba(127, 127, 127, 0.3); background: transparent; color: inherit; font: inherit; cursor: pointer; }
.qz-choices button.selected { border-color: #3b6fd0; box-shadow: 0 0 0 1px #3b6fd0; }
.qz-choices button.correct { border-color: #2e9d5b; background: rgba(46, 157, 91, 0.1); }
.qz-choices button.wrong { border-color: #d0563b; background: rgba(208, 86, 59, 0.1); }
.qz-lbl { font-weight: 700; }
.qz-primary { padding: 8px 14px; border-radius: 8px; border: 0; background: #3b6fd0; color: #fff; font: inherit; cursor: pointer; }
.qz-primary:disabled { opacity: 0.5; cursor: default; }
.qz-ghost { margin-top: 10px; padding: 6px 10px; border-radius: 8px; border: 1px solid rgba(127, 127, 127, 0.4); background: transparent; color: inherit; font: inherit; cursor: pointer; }
.qz-verdict { font-weight: 700; }
.qz-verdict.good { color: #2e9d5b; }
.qz-verdict.bad { color: #d0563b; }
.qz-details { margin-top: 10px; font-size: 13px; }
.qz-rationales { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.qz-rationales li { display: grid; grid-template-columns: 18px 1fr; gap: 6px; }
.qz-rationales li.key { color: #2e9d5b; }
.qz-trap { font-style: normal; font-size: 11px; padding: 0 6px; border-radius: 8px; border: 1px solid currentColor; opacity: 0.75; }
.qz-small { font-size: 12px; opacity: 0.85; }
.qz-tag.revised { background: rgba(59, 111, 208, 0.15); }
.qz-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 10px; }
.qz-row .qz-ghost { margin-top: 0; }
.qz-report { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
.qz-report select, .qz-report textarea { font: inherit; padding: 6px; border-radius: 6px; border: 1px solid rgba(127, 127, 127, 0.4); background: transparent; color: inherit; }
</style>
