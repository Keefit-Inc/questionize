<script setup lang="ts">
import { computed, ref } from "vue";
import type { FlagReason, Item, Votes } from "../api";
import type { Label } from "../types";
import { FAMILY_LABELS, TRAP_LABELS, passageSegments, subtypeLabel } from "../labels";
import { SCENE_EMOJI, levelInfo, sceneFor } from "../levels";
import ChoiceDistribution from "./ChoiceDistribution.vue";
import JudgeMeter from "./JudgeMeter.vue";

// `locatable`: the card sits next to the source page (the extension), so "Show in article" can work.
const props = withDefaults(defineProps<{ item: Item; chosen?: Label | null; busy?: boolean; locatable?: boolean }>(), {
  chosen: null,
  busy: false,
  locatable: true,
});
const emit = defineEmits<{ answer: [label: Label]; locate: [anchor: string]; flag: [reason: FlagReason, comment: string]; vote: [kind: "up" | "down"] }>();

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

const scene = computed(() => sceneFor(props.item));
const level = computed(() => levelInfo(props.item.level));

function mark(label: Label): "right" | "wrong" | null {
  if (!revealed.value) return null;
  if (label === revealed.value.correct_label) return "right";
  return label === selected.value ? "wrong" : null;
}

function check() {
  if (picked.value && !props.busy) emit("answer", picked.value);
}
</script>

<template>
  <article class="qz-card">
    <header class="qz-card-head">
      <span class="qz-scene" :data-scene="scene" aria-hidden="true">{{ SCENE_EMOJI[scene] }}</span>
      <span class="qz-head-text">
        <span class="qz-family">{{ FAMILY_LABELS[item.family] }}</span>
        <span class="qz-head-tags">
          <span class="qz-tag">{{ subtypeLabel(item.subtype) }}</span>
          <span v-if="level" class="qz-tag qz-level">{{ level.label }}</span>
        </span>
      </span>
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
          <span class="qz-lbl" :class="mark(choice.label)" :aria-label="mark(choice.label) === 'right' ? `${choice.label}, correct answer` : mark(choice.label) === 'wrong' ? `${choice.label}, your answer` : undefined">
            <svg v-if="mark(choice.label) === 'right'" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 12.5l4 4 8-9" /></svg>
            <svg v-else-if="mark(choice.label) === 'wrong'" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7l10 10M17 7L7 17" /></svg>
            <template v-else>{{ choice.label }}</template>
          </span>
          <span>{{ choice.text }}</span>
        </button>
      </li>
    </ol>

    <div v-if="!revealed" class="qz-actions">
      <button type="button" class="qz-primary" :disabled="!picked || busy" @click="check">{{ busy ? "Checking…" : "Check answer" }}</button>
    </div>

    <div v-else class="qz-reveal">
      <p class="qz-verdict" :class="correct ? 'good' : 'bad'">
        <span class="qz-verdict-icon" aria-hidden="true">{{ correct ? "✓" : "✕" }}</span>
        <span>
          <template v-if="correct">Correct! The answer is {{ revealed.correct_label }}.</template>
          <template v-else>Not quite. You chose {{ selected }}<template v-if="chosenTrap"> (trap: {{ chosenTrap }})</template>; the answer is {{ revealed.correct_label }}.</template>
        </span>
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

      <div v-if="revealed.votes" class="qz-vote" role="group" aria-label="Rate this question">
        <span>Good question?</span>
        <button type="button" :aria-pressed="revealed.votes.mine === 'up'" :class="{ on: revealed.votes.mine === 'up' }" @click="emit('vote', 'up')">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 11v9H4v-9zM7 11l4-7a2 2 0 0 1 3 2l-1 4h5a2 2 0 0 1 2 2l-2 7a2 2 0 0 1-2 1H7" /></svg>
          {{ revealed.votes.up }}<span class="qz-sr"> found it good</span>
        </button>
        <button type="button" :aria-pressed="revealed.votes.mine === 'down'" :class="{ on: revealed.votes.mine === 'down' }" @click="emit('vote', 'down')">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17 13V4h3v9zM17 13l-4 7a2 2 0 0 1-3-2l1-4H6a2 2 0 0 1-2-2l2-7a2 2 0 0 1 2-1h9" /></svg>
          {{ revealed.votes.down }}<span class="qz-sr"> found it weak</span>
        </button>
      </div>

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
.qz-card { border: 1px solid var(--line, rgba(127, 127, 127, 0.25)); border-radius: var(--radius, 12px); padding: 18px; margin: 12px 0; background: var(--surface, transparent); box-shadow: var(--shadow, none); }
.qz-card-head { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; }
.qz-scene { width: 46px; height: 46px; flex: none; border-radius: 14px; display: inline-flex; align-items: center; justify-content: center; font-size: 26px; background: linear-gradient(135deg, #fff3d6, #ffe0e9); }
.qz-scene[data-scene="science"], .qz-scene[data-scene="technology"], .qz-scene[data-scene="space"] { background: linear-gradient(135deg, #dde8ff, #e9ddff); }
.qz-scene[data-scene="nature"], .qz-scene[data-scene="animals"], .qz-scene[data-scene="food"], .qz-scene[data-scene="health"] { background: linear-gradient(135deg, #dcf5e4, #f0f7d4); }
.qz-scene[data-scene="city"], .qz-scene[data-scene="transport"], .qz-scene[data-scene="law"], .qz-scene[data-scene="business"] { background: linear-gradient(135deg, #e3eef7, #f3e9dc); }
.qz-head-text { display: flex; flex-direction: column; gap: 4px; min-width: 0; flex: 1; }
.qz-family { font-weight: 800; font-size: 14px; }
.qz-head-tags { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.qz-level { background: var(--accent-soft, rgba(59, 111, 208, 0.12)); color: var(--accent, #3b6fd0); }
.qz-tag { font-size: 11px; font-weight: 600; padding: 3px 9px; border-radius: 999px; background: var(--chip, rgba(127, 127, 127, 0.15)); }
.qz-badge { font-size: 11px; margin-left: auto; }
.qz-badge.verified { color: #2e9d5b; }
.qz-badge.unverified { color: #b7791f; }
.qz-passage { white-space: pre-wrap; font-family: var(--serif, inherit); line-height: 1.6; font-size: 16.5px; margin: 6px 0 12px; }
.qz-stem { font-weight: 700; line-height: 1.45; }
.qz-choices { list-style: none; padding: 0; margin: 8px 0; display: flex; flex-direction: column; gap: 6px; }
.qz-choices button { width: 100%; text-align: left; display: grid; grid-template-columns: 26px 1fr; align-items: start; gap: 10px; padding: 12px; border-radius: 12px; border: 1px solid var(--line, rgba(127, 127, 127, 0.3)); background: transparent; color: inherit; font: inherit; line-height: 1.4; cursor: pointer; transition: border-color 0.12s, background 0.12s; }
.qz-choices button.selected { border-color: var(--accent, #3b6fd0); box-shadow: 0 0 0 1px var(--accent, #3b6fd0); background: var(--accent-soft, transparent); }
.qz-choices button.correct { border-color: var(--good, #2e9d5b); background: var(--good-soft, rgba(46, 157, 91, 0.1)); }
.qz-choices button.wrong { border-color: var(--bad, #d0563b); background: var(--bad-soft, rgba(208, 86, 59, 0.1)); }
.qz-lbl { width: 26px; height: 26px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-weight: 800; font-size: 13px; background: var(--chip, rgba(127, 127, 127, 0.15)); }
.qz-choices button.selected .qz-lbl { background: var(--accent, #3b6fd0); color: #fff; }
.qz-lbl.right { background: var(--good, #2e9d5b); color: #fff; }
.qz-lbl.wrong { background: var(--bad, #d0563b); color: #fff; }
.qz-lbl svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }
.qz-primary { padding: 11px 18px; border-radius: 10px; border: 0; background: var(--accent, #3b6fd0); color: #fff; font: inherit; font-weight: 700; cursor: pointer; }
.qz-primary:disabled { opacity: 0.5; cursor: default; }
.qz-ghost { margin-top: 10px; padding: 6px 10px; border-radius: 8px; border: 1px solid rgba(127, 127, 127, 0.4); background: transparent; color: inherit; font: inherit; cursor: pointer; }
.qz-verdict { display: flex; align-items: center; gap: 10px; font-weight: 800; font-size: 17px; }
.qz-verdict-icon { width: 30px; height: 30px; flex: none; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; color: #fff; font-size: 17px; background: currentColor; }
.qz-verdict-icon { color: inherit; }
.qz-verdict.good .qz-verdict-icon { background: var(--good, #2e9d5b); color: #fff; }
.qz-verdict.bad .qz-verdict-icon { background: var(--bad, #d0563b); color: #fff; }
.qz-verdict.good { color: var(--good, #2e9d5b); }
.qz-verdict.bad { color: var(--bad, #d0563b); }
.qz-details { margin-top: 10px; font-size: 13px; }
.qz-rationales { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.qz-rationales li { display: grid; grid-template-columns: 18px 1fr; gap: 6px; }
.qz-rationales li.key { color: #2e9d5b; }
.qz-trap { font-style: normal; font-size: 11px; padding: 0 6px; border-radius: 8px; border: 1px solid currentColor; opacity: 0.75; }
.qz-small { font-size: 12px; opacity: 0.85; }
.qz-tag.revised { background: rgba(59, 111, 208, 0.15); }
.qz-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 10px; }
.qz-row .qz-ghost { margin-top: 0; }
.qz-vote { display: flex; align-items: center; gap: 8px; margin-top: 12px; font-size: 13px; }
.qz-vote > span { opacity: 0.75; margin-right: 2px; }
.qz-vote button { display: inline-flex; align-items: center; gap: 5px; padding: 5px 10px; border-radius: 999px; border: 1px solid rgba(127, 127, 127, 0.35); background: transparent; color: inherit; font: inherit; font-variant-numeric: tabular-nums; cursor: pointer; }
.qz-vote button.on { border-color: #3b6fd0; background: rgba(59, 111, 208, 0.12); color: #3b6fd0; }
.qz-vote svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linejoin: round; }
.qz-sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.qz-report { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
.qz-report select, .qz-report textarea { font: inherit; padding: 6px; border-radius: 6px; border: 1px solid rgba(127, 127, 127, 0.4); background: transparent; color: inherit; }
</style>
