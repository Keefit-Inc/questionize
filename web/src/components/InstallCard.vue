<script setup lang="ts">
// Suggests adding Questionize to the home screen, in the way this browser supports.
import { computed, ref } from "vue";
import { canPrompt, installed, isIos, promptInstall } from "../pwa";

const KEY = "questionize.install-dismissed";
const dismissed = ref(false);
try {
  dismissed.value = localStorage.getItem(KEY) === "1";
} catch {
  // Storage off: the card shows each visit.
}
const visible = computed(() => !installed.value && !dismissed.value && (canPrompt.value || isIos));

function dismiss() {
  dismissed.value = true;
  try {
    localStorage.setItem(KEY, "1");
  } catch {
    // ignore
  }
}
</script>

<template>
  <aside v-if="visible" class="install">
    <img src="/icon-192.png" alt="" width="40" height="40" />
    <div class="text">
      <strong>Add Questionize to your home screen</strong>
      <span v-if="canPrompt">It opens straight to the camera, full screen.</span>
      <span v-else>In Safari, tap Share <svg viewBox="0 0 24 24" aria-label="Share icon"><path d="M12 3v12M8 7l4-4 4 4M5 12v8h14v-8" /></svg> then “Add to Home Screen”.</span>
    </div>
    <button v-if="canPrompt" type="button" class="go" @click="promptInstall">Install</button>
    <button type="button" class="x" aria-label="Dismiss" @click="dismiss">×</button>
  </aside>
</template>

<style scoped>
.install { display: flex; align-items: center; gap: 10px; padding: 10px 12px; margin-bottom: 14px; border-radius: 12px; background: rgba(59, 111, 208, 0.1); }
.install img { border-radius: 9px; flex: none; }
.text { display: flex; flex-direction: column; gap: 2px; font-size: 13px; min-width: 0; flex: 1; }
.text svg { width: 14px; height: 14px; vertical-align: -2px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.go { padding: 8px 14px; border-radius: 8px; border: 0; background: var(--accent); color: #fff; font: inherit; font-weight: 600; cursor: pointer; }
.x { width: 30px; height: 30px; border: 0; background: transparent; color: inherit; font-size: 20px; opacity: 0.6; cursor: pointer; }
</style>
