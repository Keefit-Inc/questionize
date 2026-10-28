<script setup lang="ts">
// Snap: the app opens on a live camera. Shoot a missed question, crop it to the passage, question
// and choices (adding up to three parts when they sit on different pages), mark your answer, then
// watch Miss Lab analyze it. Without a camera (or permission), pick a photo instead.
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError, eventKey, preparePhoto, replayRunState, subscribeToGeneration, type GenerationEvent, type Label, type PreparedPhoto } from "@questionize/shared";
import AnalysisScene from "../components/AnalysisScene.vue";
import CropEditor from "../components/CropEditor.vue";
import { ensureDevice, withDevice } from "../api";
import { saveQuestion } from "../device";

const router = useRouter();
const LABELS: Label[] = ["A", "B", "C", "D", "E"];

const eligible = ref<boolean | null>(null);
const gate = reactive({ country: "US", age: false });
const camera = ref<"starting" | "live" | "denied" | "unavailable">("starting");
const cameraNote = ref("");
const video = ref<HTMLVideoElement | null>(null);
let stream: MediaStream | null = null;

const MAX_PARTS = 3;
// The shot being cropped (full photo), and the cropped parts ready to send.
const raw = ref("");
const parts = ref<{ photo: PreparedPhoto; url: string }[]>([]);
const stage = computed(() => (raw.value ? "crop" : parts.value.length && !adding.value ? "review" : "camera"));
const adding = ref(false);
const saved = ref<"pending" | "saved" | "failed" | null>(null);
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

const photoInfo = computed(() => {
  const first = parts.value[0]?.photo;
  if (!first) return "";
  const kb = Math.round(parts.value.reduce((n, p) => n + p.photo.blob.size, 0) / 1024);
  return `${parts.value.length > 1 ? `${parts.value.length} parts · ` : ""}${first.width}×${first.height} · ${kb} KB`;
});

// Only the most recent start may change the camera state: a visibility change (the permission
// prompt can cause one) used to start a second camera that stopped the first, which then reported
// "no camera" even though the second one worked.
let attempt = 0;

async function openStream(): Promise<MediaStream> {
  try {
    return await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1440 } },
      audio: false,
    });
  } catch (e) {
    // Some cameras reject the preferred size or facing; any camera will do.
    if (e instanceof DOMException && ["OverconstrainedError", "NotFoundError", "AbortError"].includes(e.name)) {
      return navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    }
    throw e;
  }
}

async function startCamera() {
  const mine = ++attempt;
  stopCamera();
  if (!navigator.mediaDevices?.getUserMedia) {
    camera.value = "unavailable";
    cameraNote.value = window.isSecureContext ? "This browser doesn't offer camera access." : "The camera only works over a secure (https) connection.";
    return;
  }
  camera.value = "starting";
  cameraNote.value = "";
  try {
    const opened = await openStream();
    if (mine !== attempt) return opened.getTracks().forEach((t) => t.stop());
    stream = opened;
    await nextTick();
    if (!video.value) return;
    video.value.srcObject = opened;
    await video.value.play().catch(() => undefined); // muted inline video; the stream is live either way
    if (mine === attempt) camera.value = "live";
  } catch (e) {
    if (mine !== attempt) return;
    stopCamera();
    const name = e instanceof DOMException ? e.name : "";
    if (name === "NotAllowedError" || name === "SecurityError") {
      camera.value = "denied";
      cameraNote.value = "Camera access is off for this site. Allow it in your browser's site settings, then try again.";
    } else if (name === "NotReadableError") {
      camera.value = "unavailable";
      cameraNote.value = "Another app is using the camera. Close it and try again.";
    } else if (name === "NotFoundError") {
      camera.value = "unavailable";
      cameraNote.value = "We couldn't find a camera on this device.";
    } else {
      camera.value = "unavailable";
      cameraNote.value = `The camera didn't start${name ? ` (${name})` : ""}. Try again, or choose a photo.`;
    }
  }
}

function stopCamera() {
  stream?.getTracks().forEach((t) => t.stop());
  stream = null;
  if (video.value) video.value.srcObject = null;
}

function onVisibility() {
  if (document.hidden) {
    attempt++; // cancels a start in progress
    stopCamera();
  }
  else if (eligible.value && stage.value === "camera" && !lab.value) startCamera();
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
  clearShots();
});

function clearShots() {
  if (raw.value) URL.revokeObjectURL(raw.value);
  parts.value.forEach((p) => URL.revokeObjectURL(p.url));
  raw.value = "";
  parts.value = [];
}

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

// A new shot goes to the crop editor first.
function usePhoto(file: Blob) {
  error.value = "";
  stopCamera();
  if (raw.value) URL.revokeObjectURL(raw.value);
  raw.value = URL.createObjectURL(file);
}

async function cropped(blob: Blob) {
  busy.value = true;
  try {
    const photo = await preparePhoto(blob);
    parts.value = [...parts.value, { photo, url: URL.createObjectURL(photo.blob) }];
    URL.revokeObjectURL(raw.value);
    raw.value = "";
    adding.value = false;
  } catch {
    error.value = "That file isn't an image we can read. Try another photo.";
  } finally {
    busy.value = false;
  }
}

function cancelCrop() {
  URL.revokeObjectURL(raw.value);
  raw.value = "";
  if (parts.value.length && !adding.value) return;
  startCamera();
}

function addPart() {
  adding.value = true;
  startCamera();
}

function removePart(i: number) {
  URL.revokeObjectURL(parts.value[i].url);
  parts.value = parts.value.filter((_, j) => j !== i);
  if (!parts.value.length) startCamera();
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

function startOver() {
  closeStream?.();
  lab.value = false;
  saved.value = null;
  form.chosen = null;
  error.value = "";
  adding.value = false;
  clearShots();
  startCamera();
}

async function onEvent(event: GenerationEvent) {
  const key = event.stage === "diagnosis" ? `diagnosis|${event.entry.id}` : eventKey(event);
  if (seen.has(key)) return;
  seen.add(key);
  events.value = [...events.value, event];
  if (event.stage === "diagnosis") {
    entryId.value = event.entry.id;
    await keepQuestion(event.entry.id, event.question_ready);
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

// Fetch the printed question (offered once) and keep it on this device; the photos can then go.
async function keepQuestion(id: number, ready: boolean | undefined) {
  if (!ready) {
    saved.value = "failed";
    return;
  }
  saved.value = "pending";
  try {
    const question = await withDevice((c) => c.takeErrorLogQuestion(id));
    saved.value = (await saveQuestion(id, question)) ? "saved" : "failed";
  } catch {
    saved.value = "failed";
  }
}

async function analyze() {
  if (!parts.value.length) return;
  busy.value = true;
  error.value = "";
  try {
    const res = await withDevice((c) =>
      c.captureErrorLog({
        images: parts.value.map((p) => p.photo.dataUrl),
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
    saved.value = null;
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
  if (entryId.value === null) return;
  const id = entryId.value;
  // The question is on the device now; the photos are no longer needed.
  clearShots();
  router.push(`/misses/${id}?view=analysis`);
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

    <!-- Crop the shot -->
    <CropEditor v-else-if="stage === 'crop'" :src="raw" :part="parts.length + 1" @done="cropped" @cancel="cancelCrop" />

    <!-- Review the parts -->
    <div v-else-if="stage === 'review'" class="review">
      <div class="parts">
        <figure v-for="(p, i) in parts" :key="p.url" class="part">
          <img :src="p.url" :alt="`Part ${i + 1} of your question`" />
          <figcaption>Part {{ i + 1 }}</figcaption>
          <button type="button" class="remove" :aria-label="`Remove part ${i + 1}`" @click="removePart(i)">×</button>
        </figure>
        <button v-if="parts.length < MAX_PARTS" type="button" class="add" @click="addPart">
          <span aria-hidden="true">+</span>
          Add another part
          <small>e.g. the passage on another page</small>
        </button>
      </div>
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
          <button type="button" class="ghost" @click="startOver">Start over</button>
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
      <p class="hint">
        <strong>{{ adding ? `Part ${parts.length + 1}` : "Snap a question you missed" }}</strong>
        <span>{{ adding ? "the rest of the question" : camera === "live" ? "Fit it inside the frame" : camera === "starting" ? "Starting the camera…" : "" }}</span>
      </p>
      <button v-if="adding" type="button" class="cancel-add" @click="adding = false; stopCamera()">Cancel</button>
      <div v-if="camera === 'denied' || camera === 'unavailable'" class="nocam" role="status">
        <p>{{ cameraNote }}</p>
        <div class="nocam-actions">
          <button type="button" class="ghost" @click="startCamera">Try the camera again</button>
          <label class="primary file">
            <input type="file" accept="image/*" capture="environment" @change="pick" />
            Choose a photo
          </label>
        </div>
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

    <!-- Above everything, the tab bar included: the Snap stage is its own stacking context. -->
    <Teleport to="body">
      <AnalysisScene
        v-if="lab && parts.length"
        :photo-url="parts[0].url"
        :photo-info="photoInfo"
        :events="events"
        :finished="finished"
        :failed="failed"
        :saved="saved"
        @continue="showAnalysis"
        @retry="startOver"
      />
    </Teleport>
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
.hint { position: absolute; top: max(14px, env(safe-area-inset-top, 0px)); left: 0; right: 0; margin: 0 auto; width: fit-content; max-width: calc(100% - 120px); padding: 8px 16px; border-radius: 16px; background: rgba(0, 0, 0, 0.55); backdrop-filter: blur(8px); display: flex; flex-direction: column; align-items: center; gap: 1px; text-align: center; }
.hint strong { font-size: 15px; }
.hint span { font-size: 12px; opacity: 0.8; }
.hint span:empty { display: none; }
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
.nocam { position: absolute; left: 16px; right: 16px; bottom: 120px; padding: 14px; border-radius: 14px; background: rgba(18, 26, 33, 0.92); display: flex; flex-direction: column; gap: 10px; }
.nocam p { margin: 0; font-size: 14px; line-height: 1.45; }
.nocam-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.primary { position: relative; display: block; text-align: center; padding: 13px; border-radius: 12px; border: 0; background: #4fd1c5; color: #062022; font: inherit; font-weight: 700; cursor: pointer; }
.primary:disabled { opacity: 0.45; cursor: default; }
.ghost { padding: 13px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.25); background: transparent; color: inherit; font: inherit; font-weight: 600; cursor: pointer; }
.link { background: none; border: 0; padding: 0; color: #4fd1c5; font: inherit; font-size: 14px; text-align: left; cursor: pointer; }
.error { color: #ff8a7a; margin: 0; font-size: 14px; }
.error.floating { position: absolute; top: 60px; left: 16px; right: 16px; text-align: center; }
.parts { flex: 1; min-height: 0; overflow-y: auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; padding: max(16px, env(safe-area-inset-top, 0px)) 16px 16px; align-content: start; }
.part { position: relative; margin: 0; border-radius: 10px; overflow: hidden; background: #000; border: 1px solid rgba(255, 255, 255, 0.12); }
.part img { display: block; width: 100%; max-height: 42dvh; object-fit: contain; }
.part figcaption { position: absolute; left: 6px; bottom: 6px; font-size: 11px; padding: 2px 6px; border-radius: 6px; background: rgba(0, 0, 0, 0.6); }
.remove { position: absolute; top: 6px; right: 6px; width: 30px; height: 30px; border-radius: 50%; border: 0; background: rgba(0, 0, 0, 0.65); color: #fff; font-size: 18px; line-height: 1; cursor: pointer; }
.add { min-height: 140px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; border-radius: 10px; border: 1.5px dashed rgba(79, 209, 197, 0.6); background: transparent; color: #4fd1c5; font: inherit; font-weight: 600; cursor: pointer; }
.add span { font-size: 28px; line-height: 1; }
.add small { font-weight: 400; opacity: 0.8; color: #e8eef2; }
.cancel-add { position: absolute; top: max(18px, env(safe-area-inset-top, 0px)); right: 14px; padding: 6px 12px; border-radius: 999px; border: 0; background: rgba(0, 0, 0, 0.55); color: #fff; font: inherit; font-size: 13px; cursor: pointer; }
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
.viewfinder, .review { z-index: 0; }
</style>
