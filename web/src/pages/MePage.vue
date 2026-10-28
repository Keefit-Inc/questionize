<script setup lang="ts">
// Me tab: Analysis (what keeps tripping the learner up, from their misses) and Stats (ratings).
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { FAMILY_LABELS, TRAP_LABELS, subtypeLabel, type ErrorLogPage, type Me, type QuestionType, type TrapType } from "@questionize/shared";
import { withDevice } from "../api";

const route = useRoute();
const router = useRouter();
const view = computed(() => (route.query.view === "stats" ? "stats" : "analysis"));
const show = (v: "analysis" | "stats") => router.replace({ query: v === "stats" ? { view: "stats" } : {} });

const me = ref<Me | null>(null);
const log = ref<ErrorLogPage | null>(null);
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
const bars = (counts: Record<string, number> | undefined, name: (k: string) => string) => {
  const list = Object.entries(counts ?? {}).slice(0, 5);
  const max = Math.max(1, ...list.map(([, n]) => n));
  return list.map(([k, n]) => ({ key: k, label: name(k), n, pct: (n / max) * 100 }));
};
const traps = computed(() => bars(log.value?.weaknesses.traps, (k) => TRAP_LABELS[k as Exclude<TrapType, "correct">] ?? k));
const misconceptions = computed(() => bars(log.value?.weaknesses.misconceptions, (k) => k.replace(/_/g, " ")));
// Question types the learner misses most, with how hard those questions were on average.
const types = computed(() => {
  const groups = new Map<string, { n: number; difficulty: number[] }>();
  for (const e of log.value?.entries ?? []) {
    const key = `${e.diagnosis.family}:${e.diagnosis.subtype}`;
    const g = groups.get(key) ?? { n: 0, difficulty: [] };
    g.n++;
    if (e.diagnosis.difficulty) g.difficulty.push(e.diagnosis.difficulty);
    groups.set(key, g);
  }
  return [...groups.entries()]
    .sort((a, b) => b[1].n - a[1].n)
    .slice(0, 5)
    .map(([key, g]) => ({ key, label: label(key), n: g.n, avg: g.difficulty.length ? (g.difficulty.reduce((a, b) => a + b, 0) / g.difficulty.length).toFixed(1) : "–" }));
});
const goals = computed(() => {
  const counts = new Map<string, number>();
  for (const e of log.value?.entries ?? []) for (const g of e.diagnosis.learning_objectives ?? []) counts.set(g, (counts.get(g) ?? 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([g]) => g);
});

onMounted(async () => {
  try {
    [me.value, log.value] = await Promise.all([withDevice((api) => api.getMe()), withDevice((api) => api.listErrorLog())]);
  } catch {
    error.value = "Couldn't load your profile.";
  }
});
</script>

<template>
  <h1>Me</h1>
  <p v-if="me" class="muted">{{ me.handle }} · {{ me.xp }} XP</p>
  <div class="seg" role="tablist" aria-label="Profile views">
    <button role="tab" :aria-selected="view === 'analysis'" :class="{ on: view === 'analysis' }" @click="show('analysis')">Analysis</button>
    <button role="tab" :aria-selected="view === 'stats'" :class="{ on: view === 'stats' }" @click="show('stats')">Stats</button>
  </div>
  <p v-if="error" class="error">{{ error }}</p>

  <template v-else-if="view === 'analysis' && log">
    <div v-if="!log.entries.length" class="empty">
      <p>Snap a few questions you missed and your patterns show up here: the traps that catch you, the beliefs behind them, and what to practice.</p>
      <RouterLink to="/snap" class="go">Snap a question</RouterLink>
    </div>
    <template v-else>
      <section>
        <h2>Traps that catch you</h2>
        <ul class="bars">
          <li v-for="t in traps" :key="t.key"><span>{{ t.label }}</span><span class="bar"><span :style="{ width: t.pct + '%' }" /></span><span class="n">{{ t.n }}</span></li>
        </ul>
      </section>
      <section v-if="misconceptions.length">
        <h2>Why you fall for them</h2>
        <ul class="bars">
          <li v-for="m in misconceptions" :key="m.key"><span>{{ m.label }}</span><span class="bar alt"><span :style="{ width: m.pct + '%' }" /></span><span class="n">{{ m.n }}</span></li>
        </ul>
      </section>
      <section>
        <h2>Question types you miss</h2>
        <table>
          <thead><tr><th>Type</th><th>Missed</th><th>Avg. difficulty</th></tr></thead>
          <tbody><tr v-for="t in types" :key="t.key"><td>{{ t.label }}</td><td>{{ t.n }}</td><td>{{ t.avg }}</td></tr></tbody>
        </table>
      </section>
      <section v-if="goals.length">
        <h2>What to practice next</h2>
        <ul class="goals"><li v-for="g in goals" :key="g">{{ g }}</li></ul>
      </section>
    </template>
  </template>

  <template v-else-if="view === 'stats' && me">
    <p class="muted">Ratings are an internal practice scale, not official test scores.</p>
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
h1 { margin: 4px 0 2px; font-size: 24px; }
h2 { margin: 18px 0 8px; font-size: 13px; letter-spacing: 0.05em; text-transform: uppercase; opacity: 0.7; }
.muted { opacity: 0.7; font-size: 13px; margin: 0 0 12px; }
.error { color: #d0563b; }
.seg { display: grid; grid-template-columns: 1fr 1fr; padding: 3px; margin-bottom: 8px; border-radius: 10px; background: rgba(127, 127, 127, 0.14); }
.seg button { padding: 8px; border: 0; border-radius: 8px; background: transparent; color: inherit; font: inherit; font-weight: 600; opacity: 0.65; cursor: pointer; }
.seg button.on { background: Canvas; opacity: 1; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12); }
.empty { display: flex; flex-direction: column; gap: 12px; margin-top: 12px; padding: 18px; border-radius: 12px; border: 1px dashed rgba(127, 127, 127, 0.4); }
.empty p { margin: 0; }
.go { display: block; text-align: center; padding: 12px; border-radius: 12px; background: #3b6fd0; color: #fff !important; font-weight: 700; text-decoration: none; }
.bars { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.bars li { display: grid; grid-template-columns: minmax(0, 10rem) 1fr 2rem; align-items: center; gap: 8px; font-size: 14px; }
.bar { height: 8px; border-radius: 4px; background: rgba(127, 127, 127, 0.15); overflow: hidden; }
.bar span { display: block; height: 100%; background: #d0563b; }
.bar.alt span { background: #b7791f; }
.n { text-align: right; font-variant-numeric: tabular-nums; }
.goals { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 4px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid rgba(127, 127, 127, 0.2); }
td:not(:first-child), th:not(:first-child) { font-variant-numeric: tabular-nums; }
tr.overall td { font-weight: 700; }
</style>
