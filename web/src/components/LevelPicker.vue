<script setup lang="ts">
// Choose who you're studying as. Everything written for you from then on (questions, explanations,
// analyses) is pitched at that level, and the Bank opens on it.
import { computed } from "vue";
import { LEVELS, type LevelId } from "@questionize/shared";

const props = defineProps<{ current?: LevelId | null; busy?: boolean }>();
const emit = defineEmits<{ pick: [level: LevelId] }>();
const groups = computed(() => (["School", "College & adult", "Test prep"] as const).map((g) => ({ name: g, levels: LEVELS.filter((l) => l.group === g) })));
const ICONS: Record<LevelId, string> = { elementary: "🎒", middle: "📓", high: "🎓", college: "📰", gmat: "📊", lsat: "⚖️", gre: "🔭" };
</script>

<template>
  <div class="picker">
    <section v-for="g in groups" :key="g.name">
      <h3>{{ g.name }}</h3>
      <div class="grid">
        <button
          v-for="l in g.levels"
          :key="l.id"
          type="button"
          class="level"
          :class="{ on: props.current === l.id }"
          :aria-pressed="props.current === l.id"
          :disabled="busy"
          @click="emit('pick', l.id)"
        >
          <span class="icon" aria-hidden="true">{{ ICONS[l.id] }}</span>
          <span class="text"><strong>{{ l.label }}</strong><small>{{ l.detail }}</small></span>
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.picker { display: flex; flex-direction: column; gap: 14px; }
h3 { margin: 0 0 8px; font-size: 11px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
.level { display: flex; align-items: flex-start; gap: 10px; padding: 12px; border-radius: 14px; border: 1.5px solid var(--line); background: var(--surface); color: inherit; font: inherit; text-align: left; cursor: pointer; transition: border-color 0.12s, transform 0.12s; }
.level:active { transform: scale(0.98); }
.level.on { border-color: var(--accent); background: var(--accent-soft); }
.icon { font-size: 24px; line-height: 1; }
.text { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.text small { font-size: 12px; color: var(--muted); line-height: 1.35; }
</style>
