<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { ApiError, QuestionCard, subscribeToItem, type Item, type Label } from "@questionize/shared";
import { api, withDevice } from "../api";

const props = defineProps<{ id: string }>();

const item = ref<Item | null>(null);
const chosen = ref<Label | null>(null);
const busy = ref(false);
const note = ref("");
const error = ref("");
const copied = ref(false);
const shownAt = ref(Date.now());
let stopTally: (() => void) | null = null;

const shareUrl = computed(() => `${window.location.origin}/q/${props.id}`);
const xUrl = computed(() => {
  const text = "Can you solve this reasoning question? I'd love to see how you answer.";
  return `https://x.com/intent/post?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl.value)}`;
});

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

async function copyLink() {
  try {
    await navigator.clipboard.writeText(shareUrl.value);
    copied.value = true;
    setTimeout(() => (copied.value = false), 1500);
  } catch {
    copied.value = false;
  }
}

watch(() => props.id, load, { immediate: true });
onBeforeUnmount(() => stopTally?.());
</script>

<template>
  <p v-if="error" class="error">{{ error }}</p>
  <template v-else-if="item">
    <p v-if="item.source" class="source">
      Written from <a :href="item.source.url" target="_blank" rel="noopener noreferrer">{{ item.source.title || item.source.domain }}</a>
      <span class="muted"> · passage adapted, not quoted</span>
    </p>
    <QuestionCard :item="item" :chosen="chosen" :busy="busy" :locatable="false" @answer="answer" />
    <p v-if="note" class="note">{{ note }}</p>
    <div class="share">
      <button type="button" @click="copyLink">{{ copied ? "Link copied" : "Copy link" }}</button>
      <a :href="xUrl" target="_blank" rel="noopener noreferrer">Post on X</a>
    </div>
  </template>
  <p v-else class="muted">Loading…</p>
</template>

<style scoped>
.source { font-size: 13px; }
.muted { opacity: 0.7; }
.note { font-size: 13px; opacity: 0.85; }
.error { color: #d0563b; }
.share { display: flex; gap: 10px; align-items: center; margin-top: 8px; }
.share button, .share a { padding: 8px 14px; border-radius: 8px; border: 1px solid rgba(127, 127, 127, 0.35); background: transparent; color: inherit; font: inherit; font-size: 14px; cursor: pointer; text-decoration: none; }
</style>
