<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { FAMILY_LABELS, subtypeLabel, type Me, type QuestionType } from "@questionize/shared";
import { withDevice } from "../api";

const me = ref<Me | null>(null);
const error = ref("");

function label(skill: string) {
  if (skill === "overall") return "Overall";
  const [family, subtype] = skill.split(":");
  const name = FAMILY_LABELS[family as QuestionType] ?? family;
  return subtype ? `${name} · ${subtypeLabel(subtype)}` : name;
}

const rows = computed(() =>
  [...(me.value?.ratings ?? [])].sort((a, b) => (a.skill === "overall" ? -1 : b.skill === "overall" ? 1 : a.skill.localeCompare(b.skill))),
);

onMounted(async () => {
  try {
    me.value = await withDevice((api) => api.getMe());
  } catch {
    error.value = "Couldn't load your ratings.";
  }
});
</script>

<template>
  <h1>My ratings</h1>
  <p v-if="error" class="error">{{ error }}</p>
  <template v-else-if="me">
    <p class="muted">{{ me.handle }} · {{ me.xp }} XP · ratings are an internal practice scale, not official test scores.</p>
    <p v-if="!rows.length" class="muted">Answer a few questions to get your first ratings.</p>
    <table v-else>
      <thead><tr><th>Skill</th><th>Rating</th><th>Answered</th><th>Correct</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.skill" :class="{ overall: r.skill === 'overall' }">
          <td>{{ label(r.skill) }}</td>
          <td>{{ r.rating }}<span v-if="r.provisional" class="muted" title="Fewer than 10 rated answers"> (provisional)</span></td>
          <td>{{ r.attempts }}</td>
          <td>{{ r.attempts ? Math.round((r.correct / r.attempts) * 100) : 0 }}%</td>
        </tr>
      </tbody>
    </table>
  </template>
</template>

<style scoped>
.muted { opacity: 0.7; font-size: 13px; }
.error { color: #d0563b; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid rgba(127, 127, 127, 0.2); }
tr.overall td { font-weight: 700; }
</style>
