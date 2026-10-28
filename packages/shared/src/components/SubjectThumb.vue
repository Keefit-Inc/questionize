<script setup lang="ts">
// A subject's thumbnail: a colored tile with its glyph, like a course icon.
import { computed } from "vue";
import { subjectOf } from "../levels";

const props = withDefaults(defineProps<{ family: string; size?: number }>(), { size: 48 });
const s = computed(() => subjectOf(props.family));
</script>

<template>
  <span class="qz-subject" :style="{ width: size + 'px', height: size + 'px', background: `linear-gradient(135deg, ${s.from}, ${s.to})` }" :title="s.name" role="img" :aria-label="s.name">
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <!-- Critical Reasoning: a balance weighing two claims -->
      <template v-if="family === 'CR'"><path d="M12 4v16M7 20h10M5 7h14" /><path d="M5 7l-2.5 6a3 3 0 0 0 5 0zM19 7l-2.5 6a3 3 0 0 0 5 0z" /></template>
      <!-- Reading: an open book -->
      <template v-else-if="family === 'RC'"><path d="M12 6c-2-1.5-5-2-8-1.5v13c3-.5 6 0 8 1.5 2-1.5 5-2 8-1.5v-13c-3-.5-6 0-8 1.5zM12 6v13" /></template>
      <!-- Writing: a pen -->
      <template v-else-if="family === 'SC'"><path d="M4 20l4-1 11-11-3-3L5 16zM14 6l3 3" /></template>
      <template v-else-if="family === 'MATH'"><path d="M5 8h6M8 5v6M14 8h5M14 15h5M14 18h5M5 15l5 5M10 15l-5 5" /></template>
      <template v-else><path d="M12 3c-4 4-4 14 0 18M12 3c4 4 4 14 0 18M7 7h10M7 17h10" /></template>
    </svg>
  </span>
</template>

<style scoped>
.qz-subject { flex: none; display: inline-flex; align-items: center; justify-content: center; border-radius: 28%; box-shadow: inset 0 -2px 0 rgba(0, 0, 0, 0.12); }
.qz-subject svg { width: 56%; height: 56%; fill: none; stroke: #fff; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
</style>
