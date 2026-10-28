<script setup lang="ts">
// Top of a question from a review list: back to the list, position, previous / next, archive.
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { cardPath, neighbors, type ListName } from "../review";
import type { ReviewCard } from "@questionize/shared";

const props = defineProps<{ list: ListName; cardKey: string; archived: boolean; busy?: boolean }>();
const emit = defineEmits<{ archive: [archived: boolean] }>();
const router = useRouter();

const pos = ref<{ index: number; total: number; prev: ReviewCard | null; next: ReviewCard | null } | null>(null);
watch(
  () => [props.list, props.cardKey],
  async () => (pos.value = await neighbors(props.list, props.cardKey)),
  { immediate: true },
);
const backTo = computed(() => (props.list === "archived" ? "/questions?view=archived" : "/questions"));
const go = (card: ReviewCard | null) => card && router.replace(cardPath(card, props.list));

defineExpose({ prev: () => go(pos.value?.prev ?? null), next: () => go(pos.value?.next ?? null) });
</script>

<template>
  <div class="bar">
    <RouterLink :to="backTo" class="back" aria-label="Back to the list">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7" /></svg>
      {{ list === "archived" ? "Archived" : "My misses" }}
    </RouterLink>
    <div class="step">
      <button type="button" :disabled="!pos?.prev" aria-label="Previous question" @click="go(pos?.prev ?? null)">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7" /></svg>
      </button>
      <span v-if="pos && pos.index >= 0" class="count">{{ pos.index + 1 }} / {{ pos.total }}</span>
      <button type="button" :disabled="!pos?.next" aria-label="Next question" @click="go(pos?.next ?? null)">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7" /></svg>
      </button>
    </div>
    <button type="button" class="archive" :disabled="busy" @click="emit('archive', !archived)">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16v3H4zM6 10v9h12v-9M10 14h4" /></svg>
      {{ archived ? "Restore" : "Archive" }}
    </button>
  </div>
</template>

<style scoped>
.bar { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 8px; margin: 2px 0 12px; }
.back { display: inline-flex; align-items: center; gap: 2px; font-size: 14px; font-weight: 600; text-decoration: none; color: var(--accent); }
.step { display: flex; align-items: center; gap: 4px; }
.step button { width: 34px; height: 34px; border-radius: 50%; border: 1px solid var(--line); background: var(--surface); color: inherit; display: flex; align-items: center; justify-content: center; cursor: pointer; }
.step button:disabled { opacity: 0.35; cursor: default; }
.count { min-width: 3.5em; text-align: center; font-size: 13px; color: var(--muted); font-variant-numeric: tabular-nums; }
.archive { justify-self: end; display: inline-flex; align-items: center; gap: 4px; padding: 6px 10px; border-radius: 999px; border: 1px solid var(--line); background: var(--surface); color: inherit; font: inherit; font-size: 13px; font-weight: 600; cursor: pointer; }
svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
</style>
