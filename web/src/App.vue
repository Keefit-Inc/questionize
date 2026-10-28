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
      <RouterLink to="/snap" class="brand"><img src="/icon-192.png" alt="" />Questionize</RouterLink>
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
/* Design tokens. Sans for the interface, serif for passages people read closely. */
:root {
  color-scheme: light;
  --bg: #f4f6f9; --surface: #ffffff; --fg: #16202b; --muted: #637083; --line: #e2e7ee; --chip: #eef1f5;
  --accent: #2f62d6; --accent-soft: #e7eefc; --violet: #7a4fd3; --violet-soft: #f0eafc;
  --good: #1f8a52; --good-soft: #e3f4ea; --bad: #c8452f; --bad-soft: #fbe9e5; --warn: #b7791f; --warn-soft: #fbf1df;
  --radius: 16px; --shadow: 0 1px 2px rgba(22, 32, 43, 0.04), 0 4px 16px rgba(22, 32, 43, 0.05);
  --sans: "Plus Jakarta Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --serif: "Source Serif 4", Georgia, "Times New Roman", serif;
  --tabbar: calc(56px + env(safe-area-inset-bottom, 0px));
  font-family: var(--sans); font-size: 15px;
}
@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
    --bg: #0e1319; --surface: #161d26; --fg: #e6ebf1; --muted: #93a0b2; --line: #263140; --chip: #1e2733;
    --accent: #7aa2ff; --accent-soft: #1c2a47; --violet: #b49cff; --violet-soft: #2a2343;
    --good: #5fd39a; --good-soft: #14301f; --bad: #ff8a74; --bad-soft: #3a1d18; --warn: #f0c46c; --warn-soft: #3a2e14;
    --shadow: none;
  }
}
html, body { height: 100%; }
body { margin: 0; background: var(--bg); color: var(--fg); overscroll-behavior-y: none; -webkit-tap-highlight-color: transparent; -webkit-font-smoothing: antialiased; }
a { color: var(--accent); }
button { font-family: inherit; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

.top { max-width: 44rem; margin: 0 auto; padding: max(14px, env(safe-area-inset-top, 0px)) max(16px, env(safe-area-inset-right, 0px)) 4px max(16px, env(safe-area-inset-left, 0px)); display: flex; align-items: center; }
.brand { display: inline-flex; align-items: center; gap: 8px; font-weight: 800; font-size: 17px; letter-spacing: -0.01em; color: inherit !important; text-decoration: none; }
.brand img { width: 26px; height: 26px; border-radius: 7px; }
.shell { max-width: 44rem; margin: 0 auto; padding: 0 max(16px, env(safe-area-inset-right, 0px)) calc(var(--tabbar) + 28px) max(16px, env(safe-area-inset-left, 0px)); }
.stage { position: fixed; inset: 0 0 var(--tabbar) 0; }

/* Shared page pieces */
.page-title { margin: 6px 0 12px; font-size: 28px; font-weight: 800; letter-spacing: -0.02em; }
.seg { display: grid; grid-auto-flow: column; grid-auto-columns: 1fr; padding: 4px; margin-bottom: 16px; border-radius: 12px; background: var(--chip); }
.seg button { padding: 9px 6px; border: 0; border-radius: 9px; background: transparent; color: var(--muted); font: inherit; font-size: 14px; font-weight: 700; cursor: pointer; transition: background 0.15s, color 0.15s; }
.seg button.on { background: var(--surface); color: var(--fg); box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1); }

.tabs { position: fixed; left: 0; right: 0; bottom: 0; z-index: 40; display: grid; grid-template-columns: repeat(3, 1fr); height: var(--tabbar); padding-bottom: env(safe-area-inset-bottom, 0px); box-sizing: border-box; background: color-mix(in srgb, var(--surface) 90%, transparent); backdrop-filter: saturate(1.4) blur(14px); border-top: 1px solid var(--line); }
.bleed .tabs { background: rgba(8, 12, 16, 0.92); color: #e8eef2; border-top-color: rgba(255, 255, 255, 0.08); }
.tab { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px; font-size: 11px; font-weight: 600; color: var(--muted); text-decoration: none; }
.bleed .tab { color: rgba(232, 238, 242, 0.6); }
.tab svg { width: 24px; height: 24px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.tab.on { color: var(--accent); }
.bleed .tab.on { color: #4fd1c5; }
.tab:focus-visible { outline-offset: -4px; }

</style>
