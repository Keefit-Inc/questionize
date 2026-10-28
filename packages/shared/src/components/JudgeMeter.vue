<script setup lang="ts">
import { computed } from "vue";
import type { RevealedItem } from "../api";
import type { Label } from "../types";
import { MEASURE_LABELS } from "../labels";

const props = defineProps<{ judge: NonNullable<RevealedItem["judge"]>; correctLabel: Label; chosen?: Label | null }>();

// The measure that decides this sub-type; fall back to support_delta when the judge does not gate it.
const measure = computed(() => props.judge.measure ?? "support_delta");
const signed = computed(() => measure.value === "support_delta");

function pos(value: number): number {
  // support_delta spans -1..1, necessity 0..1; map both to 0..100%.
  return signed.value ? ((value + 1) / 2) * 100 : value * 100;
}

const rows = computed(() =>
  props.judge.options.map((o) => {
    const m = measure.value === "support_delta" ? o.support_delta : o.necessity;
    return m
      ? { label: o.label, value: m.value, low: pos(m.ci_low), high: pos(m.ci_high), at: pos(m.value) }
      : { label: o.label, value: null, low: 0, high: 0, at: 0 };
  }),
);

const summary = computed(() => {
  const j = props.judge;
  if (j.verdict === "pass") return `Key leads ${j.runner_up} by ${j.margin.toFixed(2)} (first in ${Math.round(j.key_first_rate * 100)}% of resamples)`;
  if (j.verdict === "not_applicable") return "Measured, not gated for this question type yet";
  return `Close call: key vs ${j.runner_up}, margin ${j.margin.toFixed(2)}`;
});
</script>

<template>
  <section class="qz-judge" aria-label="Argument Judge">
    <p class="qz-judge-title">Argument Judge · {{ MEASURE_LABELS[measure] }}</p>
    <div v-for="row in rows" :key="row.label" class="qz-judge-row" :class="{ key: row.label === correctLabel, mine: row.label === chosen }">
      <span class="qz-judge-label">{{ row.label }}</span>
      <span class="qz-judge-track" :class="{ signed }">
        <span class="qz-judge-ci" :style="{ left: row.low + '%', width: Math.max(row.high - row.low, 1) + '%' }"></span>
        <span class="qz-judge-dot" :style="{ left: row.at + '%' }"></span>
      </span>
      <span class="qz-judge-value">{{ row.value === null ? "–" : (row.value > 0 && signed ? "+" : "") + row.value.toFixed(2) }}</span>
    </div>
    <p class="qz-judge-summary">{{ summary }}</p>
    <p class="qz-judge-version">{{ judge.judge_version }} · {{ judge.samples }} samples</p>
  </section>
</template>

<style scoped>
.qz-judge { margin-top: 12px; }
.qz-judge-title { margin: 0 0 6px; font-weight: 600; font-size: 13px; }
.qz-judge-row { display: grid; grid-template-columns: 18px 1fr 48px; gap: 6px; align-items: center; font-size: 12px; margin: 4px 0; }
.qz-judge-track { position: relative; height: 10px; border-radius: 5px; background: rgba(127, 127, 127, 0.15); }
.qz-judge-track.signed::before { content: ""; position: absolute; left: 50%; top: -2px; bottom: -2px; width: 1px; background: rgba(127, 127, 127, 0.5); }
.qz-judge-ci { position: absolute; top: 2px; bottom: 2px; border-radius: 3px; background: rgba(127, 127, 127, 0.35); }
.qz-judge-dot { position: absolute; top: 50%; width: 10px; height: 10px; margin: -5px 0 0 -5px; border-radius: 50%; background: #666; }
.qz-judge-row.key .qz-judge-dot { background: #2e9d5b; }
.qz-judge-row.key .qz-judge-ci { background: rgba(46, 157, 91, 0.3); }
.qz-judge-row.mine:not(.key) .qz-judge-dot { background: #d0563b; }
.qz-judge-value { text-align: right; font-variant-numeric: tabular-nums; }
.qz-judge-summary { margin: 6px 0 0; font-size: 12px; }
.qz-judge-version { margin: 2px 0 0; font-size: 11px; opacity: 0.6; }
</style>
