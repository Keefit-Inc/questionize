<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { ApiError, QuestionCard, subscribeToItem, type FlagReason, type Item, type Label } from "@questionize/shared";
import { api, withDevice } from "../api";
import { useRoute, useRouter } from "vue-router";
import DetailBar from "../components/DetailBar.vue";
import ShareRow from "../components/ShareRow.vue";
import { loadReview, type ListName } from "../review";

const props = defineProps<{ id: string }>();
const route = useRoute();
const router = useRouter();
// Opened from My misses or Archived: show the list's previous / next and archive controls.
const list = computed<ListName | null>(() => (route.query.list === "archived" ? "archived" : route.query.list === "misses" ? "misses" : null));
const saving = ref(false);

const item = ref<Item | null>(null);
const chosen = ref<Label | null>(null);
const busy = ref(false);
const note = ref("");
const error = ref("");
const shownAt = ref(Date.now());
let stopTally: (() => void) | null = null;


function followTally() {
  stopTally?.();
  stopTally = subscribeToItem(api.cableUrl(), props.id, (update) => {
    if (item.value?.revealed) item.value = { ...item.value, tally: update.tally, attempts_count: update.attempts_count };
  });
}

async function load() {
  error.value = "";
  item.value = null;
  chosen.value = null;
  note.value = "";
  try {
    item.value = await withDevice((client) => client.getItem(props.id));
    shownAt.value = Date.now();
    if (item.value.revealed) followTally();
  } catch (e) {
    error.value = e instanceof ApiError && e.status === 404 ? "This question isn't available." : "Couldn't load this question.";
  }
}

async function answer(label: Label) {
  busy.value = true;
  try {
    const res = await withDevice((client) => client.attempt(props.id, label, Date.now() - shownAt.value));
    item.value = res.item;
    chosen.value = label;
    const change = res.rating_changes[`${res.item.family}:${res.item.subtype}`];
    note.value = change
      ? `Your ${res.item.family} rating: ${Math.round(change.before)} → ${Math.round(change.after)} · +${res.xp_awarded} XP`
      : "Only your first answer counts toward your rating.";
    followTally();
  } catch {
    error.value = "Couldn't submit your answer. Please try again.";
  } finally {
    busy.value = false;
  }
}

async function flag(reason: FlagReason, comment: string) {
  try {
    const res = await withDevice((client) => client.feedback(props.id, { kind: "flag", reason, comment }));
    if (res.review_started) note.value = "Your report started an automatic re-review of this question.";
  } catch {
    error.value = "Couldn't send your report. Please try again.";
  }
}

async function vote(kind: "up" | "down") {
  const res = await withDevice((client) => client.feedback(props.id, { kind })).catch(() => null);
  if (res?.votes && item.value?.revealed) item.value = { ...item.value, votes: res.votes };
}

// Save to My misses, or archive / restore an item that is on it.
async function keep(archived: boolean) {
  if (!item.value) return;
  saving.value = true;
  try {
    const saved = await withDevice((client) => client.saveItem(props.id, archived));
    item.value = { ...item.value, saved };
    if (list.value) {
      await loadReview(list.value);
      if (archived !== (list.value === "archived")) router.replace(list.value === "archived" ? "/questions?view=archived" : "/questions");
    }
  } catch {
    error.value = "Couldn't update your list. Please try again.";
  } finally {
    saving.value = false;
  }
}


watch(() => props.id, load, { immediate: true });
onBeforeUnmount(() => stopTally?.());
</script>

<template>
  <DetailBar v-if="list && item" :list="list" :card-key="`item:${id}`" :archived="!!item.saved?.archived" :busy="saving" @archive="keep" />
  <p v-if="error" class="error">{{ error }}</p>
  <template v-else-if="item">
    <p v-if="item.source" class="source">
      Written from <a :href="item.source.url" target="_blank" rel="noopener noreferrer">{{ item.source.title || item.source.domain }}</a>
      <span class="muted"> · passage adapted, not quoted</span>
    </p>
    <p v-else-if="item.origin === 'pattern'" class="source muted">Practice question, written from the design of a question a learner missed</p>
    <QuestionCard :item="item" :chosen="chosen" :busy="busy" :locatable="false" @answer="answer" @flag="flag" @vote="vote" />
    <p v-if="note" class="note">{{ note }}</p>
    <button v-if="!list && !item.saved" type="button" class="save" :disabled="saving" @click="keep(false)">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4h12v16l-6-4-6 4z" /></svg>
      Practice later
    </button>
    <p v-else-if="!list && item.saved" class="muted saved">
      On your list ({{ item.saved.archived ? "archived" : item.saved.reason === "missed" ? "missed" : "saved" }}) ·
      <RouterLink :to="item.saved.archived ? '/questions?view=archived' : '/questions'">Open My misses</RouterLink>
    </p>
    <ShareRow v-if="item.verified" :item="item" />
  </template>
  <div v-else class="skeleton" aria-hidden="true"><span /></div>
</template>

<style scoped>
.source { font-size: 13px; margin: 0 0 4px; }
.muted { color: var(--muted); }
.note { font-size: 13px; color: var(--muted); }
.error { color: var(--bad); }
.save { display: inline-flex; align-items: center; gap: 6px; margin-top: 4px; padding: 9px 14px; border-radius: 999px; border: 1px solid var(--line); background: var(--surface); color: inherit; font: inherit; font-size: 14px; font-weight: 600; cursor: pointer; }
.save svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linejoin: round; }
.saved { font-size: 13px; margin: 4px 0 0; }
.skeleton span { display: block; height: 320px; border-radius: var(--radius); background: var(--chip); }
</style>
