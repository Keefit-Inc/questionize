<script setup lang="ts">
import type { ArgumentMapPayload, MapElement } from "../api";

defineProps<{ map: ArgumentMapPayload }>();
const emit = defineEmits<{ locate: [anchor: string] }>();

const SCHEMES: Record<string, string> = {
  causal: "Causal argument",
  generalization: "Generalization",
  analogy: "Argument by analogy",
  expert_opinion: "Appeal to expert opinion",
  consequences: "Argument from consequences",
  sign: "Argument from a sign",
  comparison: "Comparison",
  definition: "Argument from definition",
  other: "Argument",
};

function pct(m: MapElement["necessity"]) {
  return Math.round(Math.max(0, Math.min(1, m.value)) * 100);
}
</script>

<template>
  <section class="qz-map" aria-label="Argument map">
    <p class="qz-map-note">AI reconstruction of the author's reasoning · {{ SCHEMES[map.scheme] ?? "Argument" }} · not a verdict on whether it is true</p>

    <div class="qz-node conclusion">
      <span class="qz-node-kind">Conclusion</span>
      <p>{{ map.conclusion.text }}</p>
      <button v-if="map.conclusion.anchor" type="button" class="qz-link" @click="emit('locate', map.conclusion.anchor)">Show in article</button>
    </div>

    <p class="qz-map-head">Stated premises <span class="qz-muted">· how much the conclusion leans on each</span></p>
    <div v-for="p in map.premises" :key="p.id" class="qz-node">
      <span class="qz-node-kind">{{ p.id }}</span>
      <p>{{ p.text }}</p>
      <div class="qz-weight" :title="`Argument falls apart without it: ${pct(p.necessity)}%`">
        <span :style="{ width: pct(p.necessity) + '%' }"></span>
      </div>
      <button v-if="p.anchor" type="button" class="qz-link" @click="emit('locate', p.anchor)">Show in article</button>
    </div>

    <p class="qz-map-head">Unstated assumptions <span class="qz-muted">· what it takes for granted</span></p>
    <div v-for="a in map.assumptions" :key="a.id" class="qz-node assumption" :class="{ gap: a.id === map.largest_gap }">
      <span class="qz-node-kind">{{ a.id }}<template v-if="a.id === map.largest_gap"> · largest gap</template></span>
      <p>{{ a.text }}</p>
      <div class="qz-weight" :title="`Argument falls apart without it: ${pct(a.necessity)}%`">
        <span :style="{ width: pct(a.necessity) + '%' }"></span>
      </div>
    </div>
    <p class="qz-muted qz-small">Bars: Argument Judge estimate of how badly the argument fails without each element ({{ map.judge_version }}).</p>
  </section>
</template>

<style scoped>
.qz-map-note { font-size: 12px; opacity: 0.75; margin: 0 0 8px; }
.qz-map-head { font-weight: 600; font-size: 13px; margin: 12px 0 6px; }
.qz-muted { font-weight: 400; opacity: 0.7; }
.qz-small { font-size: 11px; }
.qz-node { border: 1px solid rgba(127, 127, 127, 0.25); border-radius: 10px; padding: 8px 10px; margin: 6px 0; }
.qz-node p { margin: 4px 0; line-height: 1.4; }
.qz-node.conclusion { border-color: #3b6fd0; }
.qz-node.assumption { border-style: dashed; }
.qz-node.gap { border-color: #d0563b; border-style: solid; }
.qz-node-kind { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em; opacity: 0.75; }
.qz-weight { height: 6px; border-radius: 3px; background: rgba(127, 127, 127, 0.15); overflow: hidden; }
.qz-weight span { display: block; height: 100%; background: #3b6fd0; }
.qz-node.gap .qz-weight span { background: #d0563b; }
.qz-link { margin-top: 4px; padding: 0; border: 0; background: none; color: #3b6fd0; font: inherit; font-size: 12px; cursor: pointer; }
</style>
