<script setup lang="ts">
// The shared bank: "For you" picks first (weakest skills at your level), then every question at the
// chosen level, filtered by subject.
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { LEVELS, SubjectThumb, levelInfo, subjectOf, subtypeLabel, type Item, type LevelId, type Recommendations } from "@questionize/shared";
import { withDevice } from "../api";
import { me } from "../profile";

const SUBJECT_FILTERS = [
  { value: "", label: "All" },
  { value: "CR", label: "Reasoning" },
  { value: "RC", label: "Reading" },
] as const;

const items = ref<Item[]>([]);
const next = ref<string | null>(null);
const family = ref<"" | "CR" | "RC">("");
const level = ref<LevelId | "">(me.value?.level ?? "");
const forYou = ref<Recommendations | null>(null);
const loading = ref(false);
const error = ref("");

const levelLabel = computed(() => (level.value ? levelInfo(level.value)?.label : "All levels"));

async function load(reset = false) {
  loading.value = true;
  error.value = "";
  try {
    const page = await withDevice((api) =>
      api.listItems({ family: family.value, level: level.value, before: reset ? undefined : (next.value ?? undefined) }),
    );
    items.value = reset ? page.items : [...items.value, ...page.items];
    next.value = page.next;
  } catch {
    error.value = "Couldn't load questions. Please try again.";
  } finally {
    loading.value = false;
  }
}

async function loadForYou() {
  forYou.value = await withDevice((api) => api.recommendations(6)).catch(() => null);
}

// The learner's level arrives after the first paint on a cold start.
watch(
  () => me.value?.level,
  (lv) => {
    if (lv && !level.value) {
      level.value = lv;
      load(true);
      loadForYou();
    }
  },
);
watch([family, level], () => load(true));
onMounted(() => {
  load(true);
  loadForYou();
});

const solved = (item: Item) => item.revealed && "correct_label" in item;
const rating = (item: Item) => (item.revealed && item.votes && item.votes.up + item.votes.down > 0 ? Math.round((item.votes.up / (item.votes.up + item.votes.down)) * 100) : null);
</script>

<template>
  <section v-if="forYou?.items.length" class="for-you" aria-label="Recommended for you">
    <div class="section-head">
      <h2>For you</h2>
      <span class="hint">{{ forYou.items[0].reason }}</span>
    </div>
    <div class="rail" data-no-swipe>
      <RouterLink v-for="r in forYou.items" :key="r.item.id" :to="`/q/${r.item.id}`" class="pick">
        <SubjectThumb :family="r.item.family" :size="36" />
        <span class="pick-skill">{{ subtypeLabel(r.item.subtype) }}</span>
        <span class="pick-stem">{{ r.item.stem }}</span>
      </RouterLink>
    </div>
  </section>

  <div class="filters">
    <label class="level-select">
      <span class="sr">Level</span>
      <select v-model="level" aria-label="Level">
        <option value="">All levels</option>
        <option v-for="l in LEVELS" :key="l.id" :value="l.id">{{ l.label }}</option>
      </select>
    </label>
    <div class="chips" role="group" aria-label="Subject">
      <button v-for="f in SUBJECT_FILTERS" :key="f.value" type="button" :class="{ on: family === f.value }" :aria-pressed="family === f.value" @click="family = f.value">
        {{ f.label }}
      </button>
    </div>
  </div>

  <p v-if="error" class="error">{{ error }}</p>
  <div v-else-if="!loading && !items.length" class="empty">
    <p class="empty-title">No questions at {{ levelLabel }} yet</p>
    <p>Snap a question you missed, or questionize an article with the browser extension, and new ones appear here for everyone.</p>
  </div>

  <ul class="feed">
    <li v-for="item in items" :key="item.id">
      <RouterLink :to="`/q/${item.id}`" class="card">
        <SubjectThumb :family="item.family" :size="46" />
        <span class="body">
          <span class="meta">
            <strong>{{ subjectOf(item.family).short }}</strong> · {{ subtypeLabel(item.subtype) }}
            <span v-if="item.level && !level" class="lv">{{ levelInfo(item.level)?.label }}</span>
          </span>
          <span class="stem">{{ item.stem }}</span>
          <span class="foot">
            <span v-if="solved(item)" class="done">✓ Answered</span>
            <span v-else class="new">New</span>
            <span>{{ item.attempts_count }} {{ item.attempts_count === 1 ? "try" : "tries" }}</span>
            <span v-if="rating(item) !== null">👍 {{ rating(item) }}%</span>
            <span v-if="item.origin === 'pattern'">Practice set</span>
          </span>
        </span>
      </RouterLink>
    </li>
  </ul>
  <div v-if="loading && !items.length" class="skeleton" aria-hidden="true"><span /><span /><span /></div>

  <button v-if="next" class="more" :disabled="loading" @click="load()">{{ loading ? "Loading…" : "More questions" }}</button>
</template>

<style scoped>
.section-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin-bottom: 8px; }
h2 { margin: 0; font-size: 18px; font-weight: 800; }
.hint { font-size: 12px; color: var(--muted); text-align: right; }
.for-you { margin-bottom: 18px; }
.rail { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 6px; scroll-snap-type: x mandatory; }
.pick { flex: 0 0 210px; scroll-snap-align: start; display: flex; flex-direction: column; gap: 6px; padding: 14px; border-radius: var(--radius); background: var(--surface); border: 1px solid var(--line); box-shadow: var(--shadow); color: inherit; text-decoration: none; }
.pick-skill { font-size: 12px; font-weight: 700; color: var(--accent); text-transform: capitalize; }
.pick-stem { font-size: 14px; font-weight: 600; line-height: 1.35; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }

.filters { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
.level-select select { appearance: none; padding: 8px 30px 8px 14px; border-radius: 999px; border: 1px solid var(--line); background: var(--surface) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M6 9l6 6 6-6' fill='none' stroke='%23637083' stroke-width='2'/%3E%3C/svg%3E") no-repeat right 10px center / 14px; color: inherit; font: inherit; font-size: 14px; font-weight: 700; }
.chips { display: flex; gap: 6px; }
.chips button { padding: 8px 14px; border-radius: 999px; border: 1px solid var(--line); background: transparent; color: var(--muted); font: inherit; font-size: 14px; font-weight: 700; cursor: pointer; }
.chips button.on { background: var(--fg); border-color: var(--fg); color: var(--bg); }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }

.feed { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.card { display: flex; gap: 14px; align-items: flex-start; padding: 14px; border-radius: var(--radius); background: var(--surface); border: 1px solid var(--line); box-shadow: var(--shadow); color: inherit; text-decoration: none; transition: transform 0.12s; }
.card:active { transform: scale(0.99); }
.body { display: flex; flex-direction: column; gap: 5px; min-width: 0; flex: 1; }
.meta { font-size: 12px; color: var(--muted); display: flex; align-items: center; gap: 4px; flex-wrap: wrap; text-transform: capitalize; }
.meta strong { color: var(--fg); text-transform: none; }
.lv { margin-left: 4px; padding: 1px 7px; border-radius: 999px; background: var(--accent-soft); color: var(--accent); font-weight: 700; text-transform: none; }
.stem { font-weight: 700; line-height: 1.38; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.foot { display: flex; gap: 10px; font-size: 12px; color: var(--muted); flex-wrap: wrap; }
.done { color: var(--good); font-weight: 700; }
.new { color: var(--accent); font-weight: 700; }
.empty { padding: 22px; border-radius: var(--radius); background: var(--surface); border: 1px solid var(--line); text-align: center; }
.empty p { margin: 0 0 6px; color: var(--muted); line-height: 1.5; }
.empty .empty-title { color: var(--fg); font-weight: 800; }
.error { color: var(--bad); }
.skeleton { display: flex; flex-direction: column; gap: 10px; }
.skeleton span { height: 92px; border-radius: var(--radius); background: var(--chip); }
.more { margin-top: 14px; width: 100%; padding: 12px; border-radius: 12px; border: 1px solid var(--line); background: var(--surface); color: inherit; font: inherit; font-weight: 700; cursor: pointer; }
</style>
