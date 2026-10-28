<script setup lang="ts">
// Photograph one missed question → watch it being analyzed → land on the analysis.
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError, eventKey, preparePhoto, replayRunState, subscribeToGeneration, type GenerationEvent, type Label, type PreparedPhoto } from "@questionize/shared";
import AnalysisScene from "../components/AnalysisScene.vue";
import { ensureDevice, withDevice } from "../api";
import { savePhoto } from "../photos";

const router = useRouter();
const LABELS: Label[] = ["A", "B", "C", "D", "E"];
const form = reactive({ book: "", page: "", number: "", chosen: null as Label | null });
const photo = ref<PreparedPhoto | null>(null);
const preview = ref("");
const preparing = ref(false);
const error = ref("");
const lab = ref(false);
const events = ref<GenerationEvent[]>([]);
const finished = ref(false);
const failed = ref("");
const entryId = ref<number | null>(null);
const seen = new Set<string>();
let closeStream: (() => void) | null = null;

const photoInfo = computed(() => (photo.value ? `${photo.value.width}×${photo.value.height} · ${Math.round(photo.value.blob.size / 1024)} KB` : ""));

onMounted(async () => {
  try {
    const page = await withDevice((c) => c.listErrorLog());
    if (!page.eligible) router.replace("/error-log");
  } catch {
    error.value = "Couldn't reach Questionize. Check your connection.";
  }
});
onBeforeUnmount(() => {
  closeStream?.();
  if (preview.value) URL.revokeObjectURL(preview.value);
});

async function pick(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  error.value = "";
  preparing.value = true;
  try {
    photo.value = await preparePhoto(file);
    if (preview.value) URL.revokeObjectURL(preview.value);
    preview.value = URL.createObjectURL(photo.value.blob);
  } catch {
    error.value = "That file isn't an image we can read. Try another photo.";
  } finally {
    preparing.value = false;
  }
}

async function onEvent(event: GenerationEvent) {
  const key = event.stage === "diagnosis" ? `diagnosis|${event.entry.id}` : eventKey(event);
  if (seen.has(key)) return;
  seen.add(key);
  events.value = [...events.value, event];
  if (event.stage === "diagnosis") {
    entryId.value = event.entry.id;
    if (photo.value) await savePhoto(event.entry.id, photo.value.blob);
  }
  if (event.stage === "done") {
    if (entryId.value === null) failed.value = "We couldn't read a question in that photo. Try a sharper, closer shot of one question.";
    finished.value = true;
  }
  if (event.stage === "declined" || event.stage === "failed") {
    failed.value = event.message;
    finished.value = true;
  }
}

async function analyze() {
  if (!photo.value) return;
  error.value = "";
  try {
    const res = await withDevice((c) =>
      c.captureErrorLog({
        image: photo.value!.dataUrl,
        book: form.book || undefined,
        page: form.page || undefined,
        number: form.number || undefined,
        chosen_label: form.chosen ?? undefined,
      }),
    );
    events.value = [];
    seen.clear();
    finished.value = false;
    failed.value = "";
    entryId.value = null;
    lab.value = true;
    const client = await ensureDevice();
    closeStream = subscribeToGeneration(client.cableUrl(), res.run_id, onEvent, {
      onConnected: async () => {
        for (const e of replayRunState(await client.getRun(res.run_id))) await onEvent(e);
      },
      onRejected: () => {
        failed.value = "Lost the connection to the analysis. Your entry will still appear in your error log.";
        finished.value = true;
      },
    });
  } catch (e) {
    if (e instanceof ApiError && e.status === 403) router.replace("/error-log");
    else if (e instanceof ApiError && e.status === 429) error.value = "That's a lot of photos at once. Wait a few minutes and try again.";
    else error.value = "Couldn't send the photo. Please try again.";
  }
}

function showAnalysis() {
  if (entryId.value !== null) router.push(`/error-log/${entryId.value}`);
}

function retry() {
  closeStream?.();
  lab.value = false;
  photo.value = null;
}
</script>

<template>
  <section class="capture">
    <RouterLink to="/error-log" class="back">← Error log</RouterLink>
    <h1>Add a question you missed</h1>
    <p class="lede">One question per photo. We read it once and delete it; the photo stays on this device.</p>

    <div class="shoot">
      <label class="shot primary">
        <input type="file" accept="image/*" capture="environment" @change="pick" />
        Take a photo
      </label>
      <label class="shot">
        <input type="file" accept="image/*" @change="pick" />
        Choose from library
      </label>
    </div>
    <p v-if="preparing" class="muted">Preparing the photo…</p>
    <img v-if="preview" :src="preview" alt="Your photo of the question" class="preview" />

    <fieldset class="answer">
      <legend>Which answer did you choose?</legend>
      <div class="chips">
        <button v-for="l in LABELS" :key="l" type="button" :aria-pressed="form.chosen === l" @click="form.chosen = form.chosen === l ? null : l">{{ l }}</button>
      </div>
    </fieldset>

    <div class="where">
      <label>Book <input v-model.trim="form.book" maxlength="200" placeholder="e.g. Official Guide" /></label>
      <label>Page <input v-model.trim="form.page" maxlength="20" inputmode="numeric" /></label>
      <label>Question # <input v-model.trim="form.number" maxlength="20" inputmode="numeric" /></label>
    </div>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <button type="button" class="go" :disabled="!photo || preparing" @click="analyze">Analyze</button>

    <AnalysisScene
      v-if="lab && photo"
      :photo-url="preview"
      :photo-info="photoInfo"
      :events="events"
      :finished="finished"
      :failed="failed"
      @continue="showAnalysis"
      @retry="retry"
    />
  </section>
</template>

<style scoped>
.capture { display: flex; flex-direction: column; gap: 14px; }
h1 { margin: 0; font-size: 22px; }
.lede, .muted { margin: 0; opacity: 0.75; }
.back { text-decoration: none; font-size: 14px; }
.shoot { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.shot { position: relative; display: flex; align-items: center; justify-content: center; min-height: 52px; border-radius: 12px; border: 1px solid rgba(127, 127, 127, 0.4); font-weight: 600; cursor: pointer; }
.shot.primary { background: #3b6fd0; border-color: #3b6fd0; color: #fff; }
.shot input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
.shot:focus-within { outline: 2px solid #3b6fd0; outline-offset: 2px; }
.preview { max-width: 100%; max-height: 320px; object-fit: contain; border-radius: 10px; border: 1px solid rgba(127, 127, 127, 0.3); align-self: flex-start; }
.answer { border: 0; padding: 0; margin: 0; }
.answer legend { font-weight: 600; margin-bottom: 6px; }
.chips { display: flex; gap: 8px; }
.chips button { width: 48px; height: 44px; border-radius: 10px; border: 1px solid rgba(127, 127, 127, 0.4); background: transparent; color: inherit; font: inherit; font-weight: 700; cursor: pointer; }
.chips button[aria-pressed="true"] { border-color: #d0563b; background: rgba(208, 86, 59, 0.12); color: #d0563b; }
.where { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 8px; }
@media (max-width: 480px) { .where { grid-template-columns: 1fr 1fr; } .where label:first-child { grid-column: 1 / -1; } }
.where label { display: flex; flex-direction: column; gap: 4px; font-size: 13px; }
.where input { font: inherit; padding: 8px; border-radius: 8px; border: 1px solid rgba(127, 127, 127, 0.4); background: transparent; color: inherit; min-width: 0; }
.go { padding: 14px; border-radius: 12px; border: 0; background: #1b2230; color: #fff; font: inherit; font-weight: 700; cursor: pointer; }
.go:disabled { opacity: 0.45; cursor: default; }
.error { color: #d0563b; margin: 0; }
</style>
