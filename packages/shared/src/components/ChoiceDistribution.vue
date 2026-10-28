<script setup lang="ts">
import { computed } from "vue";
import type { Label } from "../types";

const props = defineProps<{ tally: Record<Label, number>; correctLabel: Label; chosen?: Label | null }>();

const total = computed(() => Object.values(props.tally).reduce((a, b) => a + b, 0));
const rows = computed(() =>
  (Object.keys(props.tally) as Label[]).map((label) => ({
    label,
    pct: total.value ? Math.round((props.tally[label] / total.value) * 100) : 0,
  })),
);
</script>

<template>
  <section class="qz-dist" aria-label="How everyone answered">
    <p class="qz-dist-title">How everyone answered <span class="qz-muted">({{ total }})</span></p>
    <div v-for="row in rows" :key="row.label" class="qz-dist-row" :class="{ key: row.label === correctLabel, mine: row.label === chosen }">
      <span class="qz-dist-label">{{ row.label }}</span>
      <span class="qz-dist-bar"><span :style="{ width: row.pct + '%' }"></span></span>
      <span class="qz-dist-pct">{{ row.pct }}%</span>
    </div>
  </section>
</template>

<style scoped>
.qz-dist { margin-top: 12px; }
.qz-dist-title { margin: 0 0 6px; font-weight: 600; font-size: 13px; }
.qz-muted { font-weight: 400; opacity: 0.7; }
.qz-dist-row { display: grid; grid-template-columns: 18px 1fr 40px; gap: 6px; align-items: center; font-size: 12px; margin: 3px 0; }
.qz-dist-bar { height: 8px; border-radius: 4px; background: rgba(127, 127, 127, 0.18); overflow: hidden; }
.qz-dist-bar span { display: block; height: 100%; background: rgba(127, 127, 127, 0.55); }
.qz-dist-row.key .qz-dist-bar span { background: #2e9d5b; }
.qz-dist-row.mine:not(.key) .qz-dist-bar span { background: #d0563b; }
.qz-dist-pct { text-align: right; font-variant-numeric: tabular-nums; }
</style>
