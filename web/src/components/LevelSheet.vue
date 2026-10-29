<script setup lang="ts">
// First run: ask who the learner is studying as before anything is written for them.
import { ref } from "vue";
import type { LevelId } from "@questionize/shared";
import LevelPicker from "./LevelPicker.vue";
import { chooseLevel } from "../profile";
import { ALL_LEVELS_VISIBLE } from "../levels";

const busy = ref(false);
const error = ref("");

async function pick(level: LevelId) {
  busy.value = true;
  try {
    await chooseLevel(level);
  } catch {
    error.value = "Couldn't save that. Please try again.";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="sheet-backdrop" role="dialog" aria-modal="true" aria-labelledby="level-title">
    <div class="sheet">
      <p class="kicker">Welcome to Questionize</p>
      <h2 id="level-title">{{ ALL_LEVELS_VISIBLE ? "Who are you studying as?" : "Which test are you studying for?" }}</h2>
      <p class="lede">Questions, explanations and your analysis are written for this level. You can change it any time in Me.</p>
      <LevelPicker :busy="busy" @pick="pick" />
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <p class="note">Questionize is for people 13 and older.<template v-if="ALL_LEVELS_VISIBLE"> For Grades 3–5, a parent or teacher uses it with the child.</template></p>
    </div>
  </div>
</template>

<style scoped>
.sheet-backdrop { position: fixed; inset: 0; z-index: 90; display: flex; align-items: flex-end; justify-content: center; background: rgba(8, 12, 18, 0.55); backdrop-filter: blur(4px); }
.sheet { width: min(36rem, 100%); max-height: 92dvh; overflow-y: auto; box-sizing: border-box; padding: 22px max(18px, env(safe-area-inset-left, 0px)) max(22px, env(safe-area-inset-bottom, 0px)); border-radius: 22px 22px 0 0; background: var(--bg); display: flex; flex-direction: column; gap: 10px; }
@media (min-width: 640px) { .sheet-backdrop { align-items: center; } .sheet { border-radius: 22px; } }
.kicker { margin: 0; font-size: 12px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: var(--accent); }
h2 { margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.02em; }
.lede, .note { margin: 0 0 6px; color: var(--muted); line-height: 1.5; }
.note { font-size: 12px; margin-top: 6px; }
.error { color: var(--bad); margin: 0; }
</style>
