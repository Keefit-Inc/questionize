<script setup lang="ts">
// Questions tab: the learner's own missed questions first, the shared bank one tap away.
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import MissesList from "../components/MissesList.vue";
import BankList from "../components/BankList.vue";
import InstallCard from "../components/InstallCard.vue";

const route = useRoute();
const router = useRouter();
const view = computed(() => (route.query.view === "shared" ? "shared" : "mine"));
const show = (v: "mine" | "shared") => router.replace({ query: v === "shared" ? { view: "shared" } : {} });
</script>

<template>
  <h1>Questions</h1>
  <InstallCard />
  <div class="seg" role="tablist" aria-label="Which questions">
    <button role="tab" :aria-selected="view === 'mine'" :class="{ on: view === 'mine' }" @click="show('mine')">My misses</button>
    <button role="tab" :aria-selected="view === 'shared'" :class="{ on: view === 'shared' }" @click="show('shared')">Shared</button>
  </div>
  <MissesList v-if="view === 'mine'" />
  <BankList v-else />
</template>

<style scoped>
h1 { margin: 4px 0 12px; font-size: 24px; }
.seg { display: grid; grid-template-columns: 1fr 1fr; padding: 3px; margin-bottom: 14px; border-radius: 10px; background: rgba(127, 127, 127, 0.14); }
.seg button { padding: 8px; border: 0; border-radius: 8px; background: transparent; color: inherit; font: inherit; font-weight: 600; opacity: 0.65; cursor: pointer; }
.seg button.on { background: Canvas; opacity: 1; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12); }
</style>
