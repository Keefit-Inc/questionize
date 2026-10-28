<script setup lang="ts">
import { computed, ref } from "vue";
import type { MapChallenge } from "../api";
import type { Label } from "../types";

const props = defineProps<{ challenge: MapChallenge; busy?: boolean }>();
const emit = defineEmits<{ answer: [label: Label] }>();

const picked = ref<Label | null>(null);
const KIND: Record<MapChallenge["kind"], string> = { weaken: "Weaken", assumption: "Assumption", strengthen: "Strengthen" };

const total = computed(() => Object.values(props.challenge.crowd ?? {}).reduce((a, b) => a + b, 0));
const signed = computed(() => props.challenge.judged?.measure !== "necessity");

function value(label: Label): number | null {
  const o = props.challenge.options.find((x) => x.label === label);
  const m = props.challenge.judged?.measure === "necessity" ? o?.necessity : o?.support_delta;
  return m ? m.value : null;
}

function barStyle(label: Label) {
  const v = value(label) ?? 0;
  if (!signed.value) return { left: "0%", width: `${Math.round(v * 100)}%` };
  const width = Math.round(Math.abs(v) * 50);
  return v < 0 ? { left: `${50 - width}%`, width: `${width}%` } : { left: "50%", width: `${width}%` };
}

function crowdPct(label: Label) {
  return total.value ? Math.round(((props.challenge.crowd?.[label] ?? 0) / total.value) * 100) : 0;
}
</script>

<template>
  <article class="qz-challenge">
    <span class="qz-kind">{{ KIND[challenge.kind] }}</span>
    <p class="qz-q">{{ challenge.question }}</p>
    <p v-if="!challenge.revealed" class="qz-hint">Commit to your own answer first.</p>
    <ol class="qz-opts">
      <li v-for="o in challenge.options" :key="o.label">
        <button
          type="button"
          :disabled="challenge.revealed || busy"
          :class="{
            selected: !challenge.revealed && picked === o.label,
            best: challenge.revealed && o.label === challenge.judged?.label,
            mine: challenge.revealed && o.label === challenge.chosen && o.label !== challenge.judged?.label,
          }"
          @click="picked = o.label"
        >
          <span class="qz-lbl">{{ o.label }}</span>
          <span class="qz-text">{{ o.text }}</span>
          <span v-if="challenge.revealed" class="qz-meter" :class="{ signed }"><span :style="barStyle(o.label)"></span></span>
          <span v-if="challenge.revealed" class="qz-num">{{ value(o.label)?.toFixed(2) }} · {{ crowdPct(o.label) }}% chose</span>
        </button>
      </li>
    </ol>
    <button v-if="!challenge.revealed" type="button" class="qz-primary" :disabled="!picked || busy" @click="picked && emit('answer', picked)">
      {{ busy ? "Checking…" : "Reveal the judged answer" }}
    </button>
    <p v-else-if="challenge.judged" class="qz-result">
      Argument Judge: <strong>{{ challenge.judged.label }}</strong> moves the argument most
      (margin {{ challenge.judged.margin.toFixed(2) }} over {{ challenge.judged.runner_up }}, first in
      {{ Math.round(challenge.judged.first_rate * 100) }}% of resamples).
      <template v-if="challenge.chosen === challenge.judged.label"> You saw it too.</template>
    </p>
  </article>
</template>

<style scoped>
.qz-challenge { border: 1px solid rgba(127, 127, 127, 0.25); border-radius: 12px; padding: 12px; margin: 10px 0; }
.qz-kind { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: rgba(127, 127, 127, 0.15); }
.qz-q { font-weight: 600; margin: 8px 0 4px; }
.qz-hint { font-size: 12px; opacity: 0.7; margin: 0 0 6px; }
.qz-opts { list-style: none; padding: 0; margin: 6px 0; display: flex; flex-direction: column; gap: 6px; }
.qz-opts button { width: 100%; text-align: left; display: grid; grid-template-columns: 20px 1fr; gap: 4px 6px; padding: 8px; border-radius: 8px; border: 1px solid rgba(127, 127, 127, 0.3); background: transparent; color: inherit; font: inherit; font-size: 13px; cursor: pointer; }
.qz-opts button.selected { border-color: #3b6fd0; box-shadow: 0 0 0 1px #3b6fd0; }
.qz-opts button.best { border-color: #2e9d5b; background: rgba(46, 157, 91, 0.08); }
.qz-opts button.mine { border-color: #d0563b; }
.qz-lbl { font-weight: 700; }
.qz-meter { grid-column: 2; position: relative; height: 6px; border-radius: 3px; background: rgba(127, 127, 127, 0.15); }
.qz-meter.signed::after { content: ""; position: absolute; left: 50%; top: -2px; bottom: -2px; width: 1px; background: rgba(127, 127, 127, 0.5); }
.qz-meter span { position: absolute; top: 0; bottom: 0; border-radius: 3px; background: #888; }
.qz-opts button.best .qz-meter span { background: #2e9d5b; }
.qz-num { grid-column: 2; font-size: 11px; opacity: 0.75; }
.qz-primary { padding: 8px 12px; border-radius: 8px; border: 0; background: #3b6fd0; color: #fff; font: inherit; cursor: pointer; }
.qz-primary:disabled { opacity: 0.5; }
.qz-result { font-size: 13px; }
</style>
