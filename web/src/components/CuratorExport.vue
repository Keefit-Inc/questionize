<script setup lang="ts">
// Curators export a research dataset: the questions they snapped (text from this device only) with
// the checked answer key. The file is private: it is for local evaluation runs (research/README.md)
// and must never be committed or shared.
import { computed, onMounted, ref } from "vue";
import type { ErrorLogEntry } from "@questionize/shared";
import { withDevice } from "../api";
import { loadQuestion } from "../device";

const entries = ref<ErrorLogEntry[]>([]);
const dataset = ref("");
const status = ref("");
const datasets = computed(() => [...new Set(entries.value.map((e) => e.dataset).filter((d): d is string => !!d))]);
const chosen = computed(() => entries.value.filter((e) => e.dataset === dataset.value));

onMounted(async () => {
  entries.value = (await withDevice((c) => c.listErrorLog()).catch(() => null))?.entries ?? [];
  dataset.value = datasets.value[0] ?? "";
});

async function exportDataset() {
  const items = [];
  let missing = 0;
  for (const e of chosen.value) {
    const question = await loadQuestion(e.id);
    if (!question) {
      missing++;
      continue;
    }
    const d = e.diagnosis;
    items.push({
      entry_id: e.id,
      book: e.book, page: e.page, number: e.number,
      chosen_label: e.chosen_label,
      answer_key: question.local_reference?.key ?? d.key_check?.provided ?? null,
      key_verdict: d.learning_trace?.reference_status === "confirmed_reference" ? "book" : d.key_check?.verdict ?? "unchecked",
      checked_key: d.key_guess,
      official_explanation: question.local_reference?.explanation ?? "",
      ai_explanation: d.explanation,
      reference_status: question.local_reference?.status ?? "legacy_unconfirmed",
      knowledge_origin: question.local_reference?.explanation ? "expert_reference" : "user_experience",
      family: d.family, subtype: d.subtype, difficulty: d.difficulty ?? null,
      question,
    });
  }
  const blob = new Blob([JSON.stringify({ dataset: dataset.value, exported_at: new Date().toISOString(), items }, null, 1)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${dataset.value}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
  status.value = `Exported ${items.length} question${items.length === 1 ? "" : "s"}${missing ? `; ${missing} were snapped on another device and are not included` : ""}.`;
}
</script>

<template>
  <section class="curator">
    <h2>Research dataset</h2>
    <p class="muted">Your private captures, source explanations and separate AI analyses. Unverified answers stay marked unverified. Export for private local research only.</p>
    <p v-if="!datasets.length" class="muted">No curated questions yet. Turn on Learn only in Snap to start a dataset.</p>
    <div v-else class="row">
      <select v-model="dataset" aria-label="Dataset">
        <option v-for="d in datasets" :key="d" :value="d">{{ d }} ({{ entries.filter((e) => e.dataset === d).length }})</option>
      </select>
      <button type="button" class="go" @click="exportDataset">Export</button>
    </div>
    <p v-if="status" class="status" role="status">{{ status }}</p>
  </section>
</template>

<style scoped>
.curator { margin-top: 12px; padding: 16px; border-radius: var(--radius); background: var(--surface); border: 1px dashed var(--accent); display: flex; flex-direction: column; gap: 8px; }
h2 { margin: 0; font-size: 11px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: var(--accent); }
.muted { margin: 0; font-size: 13px; color: var(--muted); }
.row { display: flex; gap: 8px; }
select { flex: 1; min-width: 0; font: inherit; padding: 8px; border-radius: 10px; border: 1px solid var(--line); background: var(--surface); color: inherit; }
.go { padding: 8px 16px; border-radius: 10px; border: 0; background: var(--accent); color: #fff; font: inherit; font-weight: 700; cursor: pointer; }
.status { margin: 0; font-size: 13px; color: var(--good); }
</style>
