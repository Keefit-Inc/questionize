<script setup lang="ts">
import { RouterLink, RouterView } from "vue-router";
</script>

<template>
  <header class="nav">
    <RouterLink to="/" class="brand">Questionize</RouterLink>
    <nav>
      <RouterLink to="/">Questions</RouterLink>
      <RouterLink to="/me">My ratings</RouterLink>
    </nav>
  </header>
  <main class="shell">
    <RouterView />
  </main>
  <footer class="foot">
    Open, verified reasoning practice from the articles people read. Code MIT · questions CC BY-SA 4.0 ·
    <a href="https://github.com/Keefit-Inc/questionize">GitHub</a>
  </footer>
</template>

<style>
:root { color-scheme: light dark; font-family: system-ui, -apple-system, sans-serif; font-size: 15px; }
body { margin: 0; background: Canvas; color: CanvasText; }
a { color: #3b6fd0; }
.shell { max-width: 44rem; margin: 0 auto; padding: 0 16px 48px; }
.nav { max-width: 44rem; margin: 0 auto; padding: 16px; display: flex; align-items: center; justify-content: space-between; }
.nav nav { display: flex; gap: 16px; }
.nav a { text-decoration: none; }
.nav a.router-link-exact-active { font-weight: 700; }
.brand { font-weight: 800; font-size: 18px; color: inherit !important; }
.foot { max-width: 44rem; margin: 0 auto; padding: 24px 16px; font-size: 12px; opacity: 0.7; }
</style>
