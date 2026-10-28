<script setup lang="ts">
// Snap: the app opens on a live camera. Shoot one missed question, mark your answer, then watch
// Miss Lab analyze it. Without a camera (or permission), pick a photo instead.
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError, eventKey, preparePhoto, replayRunState, subscribeToGeneration, type GenerationEvent, type Label, type PreparedPhoto } from "@questionize/shared";
import AnalysisScene from "../components/AnalysisScene.vue";
import { ensureDevice, withDevice } from "../api";
import { savePhoto } from "../photos";

const router = useRouter();
const LABELS: Label[] = ["A", "B", "C", "D", "E"];

const eligible = ref<boolean | null>(null);
const gate = reactive({ country: "US", age: false });
const camera = ref<"starting" | "live" | "denied" | "unavailable">("starting");
const video = ref<HTMLVideoElement | null>(null);
let stream: MediaStream | null = null;

const photo = ref<PreparedPhoto | null>(null);
const still = ref("");
const form = reactive({ chosen: null as Label | null, book: "", page: "", number: "" });
const showWhere = ref(false);
const busy = ref(false);
const error = ref("");

const lab = ref(false);
const events = ref<GenerationEvent[]>([]);
const finished = ref(false);
const failed = ref("");
const entryId = ref<number | null>(null);
const seen = new Set<string>();
let closeStream: (() => void) | null = null;

const photoInfo = computed(() => (photo.value ? `${photo.value.width}×${photo.value.height} · ${Math.round(photo.value.blob.size / 1024)} KB` : ""));

async function startCamera() {
  stopCamera();
  if (!navigator.mediaDevices?.getUserMedia) {
    camera.value = "unavailable";
    return;
  }
  camera.value = "starting";
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1440 } },
      audio: false,
    });
    await nextTick();
    if (!video.value) return stopCamera();
    video.value.srcObject = stream;
    await video.value.play();
    camera.value = "live";
  } catch (e) {
    stopCamera();
    camera.value = e instanceof DOMException && e.name === "NotAllowedError" ? "denied" : "unavailable";
  }
}

function stopCamera() {
  stream?.getTracks().forEach((t) => t.stop());
  stream = null;
}

function onVisibility() {
  if (document.hidden) stopCamera();
  else if (eligible.value && !photo.value && !lab.value) startCamera();
}

onMounted(async () => {
  document.addEventListener("visibilitychange", onVisibility);
  try {
    eligible.value = (await withDevice((c) => c.listErrorLog())).eligible;
  } catch {
    error.value = "Couldn't reach Questionize. Check your connection.";
    eligible.value = true;
  }
  if (eligible.value) startCamera();
});

onBeforeUnmount(() => {
  document.removeEventListener("visibilitychange", onVisibility);
  stopCamera();
  closeStream?.();
  if (still.value) URL.revokeObjectURL(still.value);
});

async function confirmEligibility() {
  error.value = "";
  try {
    const res = await withDevice((c) => c.setEligibility(gate.country, gate.age));
    eligible.value = res.error_log;
    if (!res.error_log) error.value = "Snap is open in the United States for ages 13 and up for now. You can still practice shared questions.";
    else startCamera();
  } catch {
    error.value = "Couldn't save that. Please try again.";
  }
}

async function usePhoto(file: Blob) {
  busy.value = true;
  error.value = "";
  try {
    photo.value = await preparePhoto(file);
    if (still.value) URL.revokeObjectURL(still.value);
    still.value = URL.createObjectURL(photo.value.blob);
    stopCamera();
  } catch {
    error.value = "That file isn't an image we can read. Try another photo.";
  } finally {
    busy.value = false;
  }
}

function shutter() {
  const v = video.value;
  if (!v || camera.value !== "live" || !v.videoWidth) return;
  const canvas = document.createElement("canvas");
  canvas.width = v.videoWidth;
  canvas.height = v.videoHeight;
  canvas.getContext("2d")!.drawImage(v, 0, 0);
  canvas.toBlob((blob) => blob && usePhoto(blob), "image/jpeg", 0.92);
}

function pick(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (file) usePhoto(file);
}

function retake() {
  photo.value = null;
  form.chosen = null;
  error.value = "";
  startCamera();
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
  busy.value = true;
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
        failed.value = "Lost the connection to Miss Lab. Your question will still appear under Questions.";
        finished.value = true;
      },
    });
  } catch (e) {
    if (e instanceof ApiError && e.status === 403) eligible.value = false;
    else if (e instanceof ApiError && e.status === 429) error.value = "That's a lot of photos at once. Wait a few minutes and try again.";
    else error.value = "Couldn't send the photo. Please try again.";
  } finally {
    busy.value = false;
  }
}

function showAnalysis() {
  if (entryId.value !== null) router.push(`/misses/${entryId.value}`);
}

function afterFailure() {
  closeStream?.();
  lab.value = false;
  retake();
}
</script>

<template>
  <section class="snap">
    <!-- Eligibility -->
    <div v-if="eligible === false" class="panel gate">
      <h1>Snap a question you missed</h1>
      <p>We read your photo once, then delete it. You get what the question tests, why your answer was tempting, and new questions on the same trap.</p>
      <label>Where do you live?
        <select v-model="gate.country">
          <option value="US">United States</option>
          <option value="ZZ">Somewhere else</option>
        </select>
      </label>
      <label class="check"><input v-model="gate.age" type="checkbox" /> I am 13 or older</label>
      <button type="button" class="primary" :disabled="!gate.age" @click="confirmEligibility">Continue</button>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <RouterLink to="/questions?view=shared" class="link">Practice shared questions instead</RouterLink>
    </div>

    <!-- Review the shot -->
    <div v-else-if="photo" class="review">
      <img :src="still" alt="Your photo of the question" class="still" />
      <div class="sheet">
        <p class="ask">Which answer did you choose?</p>
        <div class="chips">
          <button v-for="l in LABELS" :key="l" type="button" :aria-pressed="form.chosen === l" @click="form.chosen = form.chosen === l ? null : l">{{ l }}</button>
        </div>
        <button v-if="!showWhere" type="button" class="link" @click="showWhere = true">Add book, page and question number</button>
        <div v-else class="where">
          <input v-model.trim="form.book" maxlength="200" placeholder="Book" aria-label="Book" />
          <input v-model.trim="form.page" maxlength="20" placeholder="Page" inputmode="numeric" aria-label="Page" />
          <input v-model.trim="form.number" maxlength="20" placeholder="Q #" inputmode="numeric" aria-label="Question number" />
        </div>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <div class="actions">
          <button type="button" class="ghost" @click="retake">Retake</button>
          <button type="button" class="primary" :disabled="busy" @click="analyze">{{ busy ? "Sending…" : "Analyze" }}</button>
        </div>
      </div>
    </div>

    <!-- Viewfinder -->
    <div v-else-if="eligible" class="viewfinder">
      <video ref="video" playsinline muted :class="{ on: camera === 'live' }" />
      <div v-if="camera === 'live' || camera === 'starting'" class="frame" aria-hidden="true">
        <span class="c tl" /><span class="c tr" /><span class="c bl" /><span class="c br" />
      </div>
      <p v-if="camera === 'live'" class="hint">Fit one question you missed in the frame</p>
      <div v-else-if="camera !== 'starting'" class="panel nocam">
        <h1>Snap a question you missed</h1>
        <p>{{ camera === "denied" ? "Camera access is off for this site. Allow it in your browser settings, or choose a photo." : "No camera here. Choose a photo of one question you missed." }}</p>
        <label class="primary file">
          <input type="file" accept="image/*" capture="environment" @change="pick" />
          Choose a photo
        </label>
      </div>
      <p v-if="error && camera === 'live'" class="error floating" role="alert">{{ error }}</p>
      <div class="controls">
        <label class="side" title="Choose from library">
          <input type="file" accept="image/*" @change="pick" />
          <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2" /><circle cx="9" cy="10" r="1.6" /><path d="m21 16-5-5-8 8" /></svg>
          <span class="sr">Choose from library</span>
        </label>
        <button type="button" class="shutter" :disabled="camera !== 'live' || busy" aria-label="Take photo" @click="shutter"><span /></button>
        <span class="side" aria-hidden="true" />
      </div>
    </div>

    <AnalysisScene
      v-if="lab && photo"
      :photo-url="still"
      :photo-info="photoInfo"
      :events="events"
      :finished="finished"
      :failed="failed"
      @continue="showAnalysis"
      @retry="afterFailure"
    />
  </section>
</template>

<style scoped>
.snap { position: relative; height: 100%; background: #080c10; color: #e8eef2; overflow: hidden; }
.viewfinder, .review { position: absolute; inset: 0; display: flex; flex-direction: column; }
video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity 0.4s; }
video.on { opacity: 1; }
.frame { position: absolute; inset: 14% 8% 26%; pointer-events: none; }
.c { position: absolute; width: 28px; height: 28px; border: 3px solid #4fd1c5; }
.c.tl { top: 0; left: 0; border-right: 0; border-bottom: 0; border-top-left-radius: 8px; }
.c.tr { top: 0; right: 0; border-left: 0; border-bottom: 0; border-top-right-radius: 8px; }
.c.bl { bottom: 0; left: 0; border-right: 0; border-top: 0; border-bottom-left-radius: 8px; }
.c.br { bottom: 0; right: 0; border-left: 0; border-top: 0; border-bottom-right-radius: 8px; }
.hint { position: absolute; top: max(18px, env(safe-area-inset-top, 0px)); left: 0; right: 0; margin: 0 auto; width: fit-content; padding: 6px 12px; border-radius: 999px; background: rgba(0, 0, 0, 0.55); font-size: 13px; }
.controls { position: absolute; left: 0; right: 0; bottom: 18px; display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; padding: 0 max(28px, env(safe-area-inset-left, 0px)); }
.shutter { width: 76px; height: 76px; border-radius: 50%; border: 4px solid #fff; background: transparent; padding: 5px; cursor: pointer; }
.shutter span { display: block; width: 100%; height: 100%; border-radius: 50%; background: #fff; transition: transform 0.1s; }
.shutter:active span { transform: scale(0.9); }
.shutter:disabled { opacity: 0.35; }
.side { position: relative; justify-self: start; width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; background: rgba(255, 255, 255, 0.12); cursor: pointer; }
span.side { visibility: hidden; justify-self: end; }
.side input, .file input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
.side svg { width: 24px; height: 24px; fill: none; stroke: #fff; stroke-width: 1.7; stroke-linejoin: round; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.panel { margin: auto; width: min(26rem, calc(100% - 32px)); padding: 22px; border-radius: 16px; background: #121a21; display: flex; flex-direction: column; gap: 12px; box-sizing: border-box; }
.panel h1 { margin: 0; font-size: 21px; }
.panel p { margin: 0; line-height: 1.5; opacity: 0.85; }
.gate { margin-top: max(24px, env(safe-area-inset-top, 0px)); }
.gate label { display: flex; flex-direction: column; gap: 4px; }
.gate .check { flex-direction: row; align-items: center; gap: 8px; }
.gate select { font: inherit; padding: 8px; border-radius: 8px; }
.nocam { position: relative; z-index: 1; margin-bottom: 140px; }
.primary { position: relative; display: block; text-align: center; padding: 13px; border-radius: 12px; border: 0; background: #4fd1c5; color: #062022; font: inherit; font-weight: 700; cursor: pointer; }
.primary:disabled { opacity: 0.45; cursor: default; }
.ghost { padding: 13px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.25); background: transparent; color: inherit; font: inherit; font-weight: 600; cursor: pointer; }
.link { background: none; border: 0; padding: 0; color: #4fd1c5; font: inherit; font-size: 14px; text-align: left; cursor: pointer; }
.error { color: #ff8a7a; margin: 0; font-size: 14px; }
.error.floating { position: absolute; top: 60px; left: 16px; right: 16px; text-align: center; }
.still { flex: 1; min-height: 0; width: 100%; object-fit: contain; background: #000; }
.sheet { padding: 16px max(16px, env(safe-area-inset-left, 0px)) 18px; background: #121a21; border-radius: 18px 18px 0 0; display: flex; flex-direction: column; gap: 12px; }
.ask { margin: 0; font-weight: 600; }
.chips { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
.chips button { height: 46px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.25); background: transparent; color: inherit; font: inherit; font-weight: 700; font-size: 17px; cursor: pointer; }
.chips button[aria-pressed="true"] { border-color: #ff8a7a; background: rgba(255, 138, 122, 0.16); color: #ff8a7a; }
.where { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 8px; }
.where input { min-width: 0; font: inherit; padding: 10px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.2); background: rgba(255, 255, 255, 0.06); color: inherit; }
.actions { display: grid; grid-template-columns: 1fr 2fr; gap: 8px; }
button:focus-visible, .side:focus-within, .file:focus-within { outline: 2px solid #4fd1c5; outline-offset: 2px; }
@media (min-width: 900px) { .review { flex-direction: row; } .sheet { width: 24rem; border-radius: 0; justify-content: center; } }
</style>
