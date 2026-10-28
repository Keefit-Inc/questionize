<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

const route = useRoute();
const tab = computed(() => route.meta.tab as string | undefined);
const fullBleed = computed(() => Boolean(route.meta.fullBleed));
const TABS = [
  { key: "snap", to: "/snap", label: "Snap" },
  { key: "questions", to: "/questions", label: "Questions" },
  { key: "me", to: "/me", label: "Me" },
] as const;
</script>

<template>
  <div class="app" :class="{ bleed: fullBleed }">
    <header v-if="!fullBleed" class="top">
      <RouterLink to="/snap" class="brand">Questionize</RouterLink>
    </header>
    <main :class="fullBleed ? 'stage' : 'shell'">
      <RouterView />
    </main>
    <nav class="tabs" aria-label="Main">
      <RouterLink v-for="t in TABS" :key="t.key" :to="t.to" class="tab" :class="{ on: tab === t.key }" :aria-current="tab === t.key ? 'page' : undefined">
        <svg v-if="t.key === 'snap'" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h3l2-3h6l2 3h3v11H4z" /><circle cx="12" cy="13" r="3.6" /></svg>
        <svg v-else-if="t.key === 'questions'" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 6h12M8 12h12M8 18h12" /><circle cx="4" cy="6" r="1" /><circle cx="4" cy="12" r="1" /><circle cx="4" cy="18" r="1" /></svg>
        <svg v-else viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4" /><path d="M4 20c1.5-4 4.5-6 8-6s6.5 2 8 6" /></svg>
        <span>{{ t.label }}</span>
      </RouterLink>
    </nav>
  </div>
</template>

<style>
:root { color-scheme: light dark; font-family: system-ui, -apple-system, sans-serif; font-size: 15px; --tabbar: calc(54px + env(safe-area-inset-bottom, 0px)); }
html, body { height: 100%; }
body { margin: 0; background: Canvas; color: CanvasText; overscroll-behavior-y: none; -webkit-tap-highlight-color: transparent; }
a { color: #3b6fd0; }
.top { max-width: 44rem; margin: 0 auto; padding: max(14px, env(safe-area-inset-top, 0px)) max(16px, env(safe-area-inset-right, 0px)) 6px max(16px, env(safe-area-inset-left, 0px)); }
.brand { font-weight: 800; font-size: 18px; color: inherit !important; text-decoration: none; }
.shell { max-width: 44rem; margin: 0 auto; padding: 0 max(16px, env(safe-area-inset-right, 0px)) calc(var(--tabbar) + 24px) max(16px, env(safe-area-inset-left, 0px)); }
.stage { position: fixed; inset: 0 0 var(--tabbar) 0; }
.tabs { position: fixed; left: 0; right: 0; bottom: 0; z-index: 40; display: grid; grid-template-columns: repeat(3, 1fr); height: var(--tabbar); padding-bottom: env(safe-area-inset-bottom, 0px); box-sizing: border-box; background: color-mix(in srgb, Canvas 92%, transparent); backdrop-filter: blur(12px); border-top: 1px solid rgba(127, 127, 127, 0.2); }
.bleed .tabs { background: rgba(8, 12, 16, 0.92); color: #e8eef2; border-top-color: rgba(255, 255, 255, 0.08); }
.tab { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; font-size: 11px; color: inherit; opacity: 0.6; text-decoration: none; }
.tab svg { width: 24px; height: 24px; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }
.tab.on { opacity: 1; color: #3b6fd0; font-weight: 600; }
.bleed .tab.on { color: #4fd1c5; }
.tab:focus-visible { outline: 2px solid #3b6fd0; outline-offset: -4px; }
</style>
