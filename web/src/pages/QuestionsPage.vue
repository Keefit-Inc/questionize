<script setup lang="ts">
// Questions tab: what to review (My misses), the shared bank, and what's been archived.
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import ReviewList from "../components/ReviewList.vue";
import BankList from "../components/BankList.vue";
import InstallCard from "../components/InstallCard.vue";

const VIEWS = [
  { key: "misses", label: "My misses" },
  { key: "bank", label: "Bank" },
  { key: "archived", label: "Archived" },
] as const;
type View = (typeof VIEWS)[number]["key"];

const route = useRoute();
const router = useRouter();
const view = computed<View>(() => (route.query.view === "bank" || route.query.view === "shared" ? "bank" : route.query.view === "archived" ? "archived" : "misses"));
const show = (v: View) => router.replace({ query: v === "misses" ? {} : { view: v } });
</script>

<template>
  <h1 class="page-title">Questions</h1>
  <InstallCard />
  <div class="seg" role="tablist" aria-label="Which questions">
    <button v-for="v in VIEWS" :key="v.key" role="tab" :aria-selected="view === v.key" :class="{ on: view === v.key }" @click="show(v.key)">{{ v.label }}</button>
  </div>
  <ReviewList v-if="view === 'misses'" key="misses" list="misses" />
  <BankList v-else-if="view === 'bank'" />
  <ReviewList v-else key="archived" list="archived" />
</template>
