<script setup lang="ts">
// Full-screen "lab" while a photographed question is analyzed. Every phase, number and log line
// comes from the run's real events; only the scanning beam and the text-region boxes are decoration.
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { FAMILY_LABELS, subtypeLabel, type GenerationEvent, type QuestionType } from "@questionize/shared";

const props = defineProps<{ photoUrl: string; photoInfo: string; events: GenerationEvent[]; finished: boolean; failed: string }>();
const emit = defineEmits<{ continue: []; retry: [] }>();

const PHASES = [
  { key: "read", label: "Optical read" },
  { key: "structure", label: "Structure & intent" },
  { key: "trap", label: "Trap analysis" },
  { key: "practice", label: "Synthesize practice" },
  { key: "verify", label: "Verify practice" },
] as const;
const LANE_STEPS = ["draft", "solve", "critic", "judge", "verdict"] as const;

const started = Date.now();
const now = ref(Date.now());
let timer = 0;
onMounted(() => (timer = window.setInterval(() => (now.value = Date.now()), 87)));
onBeforeUnmount(() => clearInterval(timer));

const clock = computed(() => {
  const ms = now.value - started;
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}.${String(Math.floor((ms % 1000) / 10)).padStart(2, "0")}`;
});

const stages = computed(() => new Set(props.events.map((e) => e.stage)));
const diagnosed = computed(() => props.events.find((e) => e.stage === "diagnosed") as Extract<GenerationEvent, { stage: "diagnosed" }> | undefined);
const indexed = computed(() => props.events.filter((e) => "index" in e && typeof e.index === "number") as (GenerationEvent & { index: number })[]);

const phaseState = computed(() => {
  const s = stages.value;
  const reached = [true, s.has("diagnosed"), s.has("diagnosed"), s.has("practice"), indexed.value.length > 0];
  const done = [s.has("diagnosed"), s.has("diagnosed"), s.has("practice"), indexed.value.length > 0, props.finished];
  return PHASES.map((p, i) => ({ ...p, state: done[i] ? "done" : reached[i] ? "active" : "waiting" }));
});

function laneStep(index: number) {
  const seen = new Set<string>(indexed.value.filter((e) => e.index === index).map((e) => e.stage));
  if (stages.value.has("practice")) seen.add("draft");
  const passed = indexed.value.some((e) => e.index === index && e.stage === "verdict" && "passed" in e && e.passed);
  return LANE_STEPS.map((step) => ({ step, on: seen.has(step) || (step === "verdict" && props.finished), ok: step === "verdict" && passed }));
}

const lines = computed(() => {
  const out: { t: string; text: string; tone?: "good" | "bad" | "accent" }[] = [];
  const stamp = (i: number) => `T+${String(i).padStart(2, "0")}`;
  let i = 0;
  out.push({ t: stamp(i++), text: `photo ${props.photoInfo}` });
  for (const e of props.events) {
    if (e.stage === "reading") out.push({ t: stamp(i++), text: "reading the photographed question" });
    else if (e.stage === "diagnosed") {
      const fam = FAMILY_LABELS[e.family as QuestionType] ?? e.family ?? "";
      if (fam) out.push({ t: stamp(i++), text: `classified: ${fam} · ${subtypeLabel(e.subtype ?? "")}`, tone: "accent" });
      if (e.difficulty) out.push({ t: stamp(i++), text: `difficulty ${e.difficulty}/5` });
      if (e.key_guess) out.push({ t: stamp(i++), text: `key ${e.key_guess}`, tone: e.chosen_correct === false ? "bad" : e.chosen_correct ? "good" : undefined });
      if (e.competency) out.push({ t: stamp(i++), text: `skill: ${e.competency}` });
    } else if (e.stage === "practice") out.push({ t: stamp(i++), text: "writing new questions on the same trap" });
    else if ("index" in e && typeof e.index === "number" && "message" in e) out.push({ t: stamp(i++), text: `P${e.index + 1} ${e.stage}: ${e.message}`, tone: e.stage === "verdict" ? ("passed" in e && e.passed ? "good" : "bad") : undefined });
    else if (e.stage === "diagnosis") out.push({ t: stamp(i++), text: "saved to My misses", tone: "good" });
  }
  return out.slice(-9);
});

// Text lines found in the photo itself: rows of the image with enough dark pixels, grouped into
// bands, each boxed from its leftmost to rightmost ink. Falls back to nothing if the image can't be read.
type Box = { top: number; left: number; w: number; h: number };
const boxes = ref<Box[]>([]);

async function findTextLines(url: string): Promise<Box[]> {
  const img = new Image();
  img.src = url;
  await img.decode();
  const W = 240;
  const H = Math.max(1, Math.round((img.naturalHeight / img.naturalWidth) * W));
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  ctx.drawImage(img, 0, 0, W, H);
  const { data } = ctx.getImageData(0, 0, W, H);
  const lum = (x: number, y: number) => {
    const i = (y * W + x) * 4;
    return 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
  };
  let mean = 0;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) mean += lum(x, y);
  mean /= W * H;
  const dark = mean - 40;
  const rows: { ink: number; min: number; max: number }[] = [];
  for (let y = 0; y < H; y++) {
    let ink = 0, min = W, max = -1;
    for (let x = 0; x < W; x++) if (lum(x, y) < dark) { ink++; min = Math.min(min, x); max = Math.max(max, x); }
    rows.push({ ink, min, max });
  }
  const out: Box[] = [];
  let start = -1, left = W, right = -1;
  for (let y = 0; y <= H; y++) {
    const on = y < H && rows[y].ink > W * 0.01;
    if (on) {
      if (start < 0) { start = y; left = W; right = -1; }
      left = Math.min(left, rows[y].min);
      right = Math.max(right, rows[y].max);
    } else if (start >= 0) {
      if (y - start >= 2 && right - left > W * 0.05) out.push({ top: (start / H) * 100 - 0.6, left: (left / W) * 100 - 0.6, w: ((right - left) / W) * 100 + 1.2, h: ((y - start) / H) * 100 + 1.2 });
      start = -1;
    }
  }
  return out.slice(0, 24);
}

onMounted(async () => {
  try {
    boxes.value = await findTextLines(props.photoUrl);
  } catch {
    boxes.value = [];
  }
});

const regionsLit = computed(() => (stages.value.has("diagnosed") ? boxes.value.length : Math.min(boxes.value.length, Math.floor((now.value - started) / 350))));
// After classification the lower lines (usually the answer options) are marked in amber.
const optionStart = computed(() => Math.max(0, boxes.value.length - 5));
</script>

<template>
  <div class="lab" role="dialog" aria-modal="true" aria-label="Analyzing your question">
    <div class="lab-inner">
      <header class="lab-top">
        <span class="lab-mark">Miss Lab</span>
        <span class="lab-status" :class="{ done: finished, fail: failed }">{{ failed ? "Analysis stopped" : finished ? "Analysis complete" : "Analyzing" }}</span>
        <span class="lab-clock" aria-hidden="true">{{ clock }}</span>
      </header>

      <div class="lab-grid">
        <figure class="specimen" :class="{ settled: diagnosed }">
          <div class="plate">
            <img :src="photoUrl" alt="Your photo of the question" />
            <div class="grid-overlay" aria-hidden="true" />
            <div v-if="!finished && !failed" class="beam" aria-hidden="true" />
            <div
              v-for="(b, i) in boxes"
              :key="i"
              class="region"
              :class="{ lit: i < regionsLit, key: diagnosed && i >= optionStart }"
              :style="{ top: b.top + '%', left: b.left + '%', width: b.w + '%', height: b.h + '%' }"
              aria-hidden="true"
            />
          </div>
          <span class="corner tl" /><span class="corner tr" /><span class="corner bl" /><span class="corner br" />
          <figcaption>specimen · {{ photoInfo }}</figcaption>
        </figure>

        <section class="hud">
          <ol class="phases">
            <li v-for="(p, i) in phaseState" :key="p.key" :class="p.state">
              <span class="phase-n">{{ String(i + 1).padStart(2, "0") }}</span>
              <span>{{ p.label }}</span>
              <span class="phase-dot" />
            </li>
          </ol>

          <div v-if="diagnosed?.difficulty" class="gauge">
            <span class="gauge-label">Difficulty</span>
            <span v-for="n in 5" :key="n" class="cell" :class="{ on: n <= (diagnosed.difficulty ?? 0) }" :style="{ animationDelay: n * 120 + 'ms' }" />
            <span class="gauge-value">{{ diagnosed.difficulty }}/5</span>
          </div>

          <div v-if="stages.has('practice')" class="lanes">
            <div v-for="lane in [0, 1]" :key="lane" class="lane">
              <span class="lane-name">P{{ lane + 1 }}</span>
              <template v-for="(s, j) in laneStep(lane)" :key="s.step">
                <span v-if="j" class="wire" :class="{ on: s.on }" />
                <span class="node" :class="{ on: s.on, ok: s.ok }">{{ s.step }}</span>
              </template>
            </div>
          </div>

          <ol class="log" aria-live="polite">
            <li v-for="l in lines" :key="l.t + l.text" :class="l.tone">
              <span class="t">{{ l.t }}</span> {{ l.text }}
            </li>
          </ol>

          <p v-if="failed" class="lab-fail">{{ failed }}</p>
          <div class="lab-actions">
            <button v-if="finished && !failed" type="button" class="lab-go" @click="emit('continue')">See the analysis</button>
            <button v-if="failed" type="button" class="lab-go" @click="emit('retry')">Try another photo</button>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* A deliberately dark, single-theme instrument panel. */
.lab {
  --ink: #0b1116; --panel: #111a21; --line: #24333d; --text: #d7e3ea; --dim: #7f95a3;
  --signal: #4fd1c5; --hot: #ffb454; --bad: #ff6b5e; --good: #6be3a0;
  position: fixed; inset: 0; z-index: 50; background: radial-gradient(ellipse at 30% 20%, #142430 0%, var(--ink) 60%);
  color: var(--text); overflow-y: auto; color-scheme: dark;
  font-family: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
}
.lab-inner {
  max-width: 980px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px;
  padding-block: max(16px, env(safe-area-inset-top, 0px)) max(24px, env(safe-area-inset-bottom, 0px));
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
}
.lab-top { display: flex; align-items: center; gap: 12px; font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase; }
.lab-mark { color: var(--signal); font-weight: 700; }
.lab-status { color: var(--hot); }
.lab-status::before { content: "● "; animation: blink 1s steps(2) infinite; }
.lab-status.done { color: var(--good); }
.lab-status.done::before, .lab-status.fail::before { animation: none; }
.lab-status.fail { color: var(--bad); }
.lab-clock { margin-left: auto; font-variant-numeric: tabular-nums; color: var(--dim); }
.lab-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; }
@media (max-width: 720px) { .lab-grid { grid-template-columns: minmax(0, 1fr); } }

.specimen { position: relative; margin: 0; padding: 14px; border: 1px solid var(--line); background: #000; overflow: hidden; align-self: start; display: flex; justify-content: center; }
.plate { position: relative; display: inline-block; max-width: 100%; overflow: hidden; }
.specimen img { display: block; max-width: 100%; max-height: 62vh; width: auto; height: auto; filter: grayscale(0.6) contrast(1.15) brightness(0.8); transition: filter 1.2s; }
.specimen.settled img { filter: grayscale(0.2) contrast(1.05) brightness(0.9); }
.grid-overlay { position: absolute; inset: 0; background-image: linear-gradient(rgba(79, 209, 197, 0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(79, 209, 197, 0.08) 1px, transparent 1px); background-size: 24px 24px; pointer-events: none; }
.beam { position: absolute; left: 0; right: 0; height: 22%; top: -22%; background: linear-gradient(180deg, transparent, rgba(79, 209, 197, 0.28) 80%, rgba(79, 209, 197, 0.9)); animation: sweep 2.4s cubic-bezier(0.45, 0, 0.55, 1) infinite; pointer-events: none; }
.region { position: absolute; border: 1px solid transparent; opacity: 0; transition: opacity 0.4s, border-color 0.6s, background 0.6s; }
.region.lit { opacity: 1; border-color: rgba(79, 209, 197, 0.7); background: rgba(79, 209, 197, 0.06); }
.region.key { border-color: rgba(255, 180, 84, 0.75); background: rgba(255, 180, 84, 0.07); }
.corner { position: absolute; width: 16px; height: 16px; border: 2px solid var(--signal); }
.corner.tl { top: 6px; left: 6px; border-right: 0; border-bottom: 0; }
.corner.tr { top: 6px; right: 6px; border-left: 0; border-bottom: 0; }
.corner.bl { bottom: 6px; left: 6px; border-right: 0; border-top: 0; }
.corner.br { bottom: 6px; right: 6px; border-left: 0; border-top: 0; }
.specimen figcaption { position: absolute; left: 10px; bottom: 8px; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--signal); background: rgba(11, 17, 22, 0.7); padding: 2px 6px; }

.hud { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.phases { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.phases li { display: grid; grid-template-columns: 28px 1fr 12px; align-items: center; padding: 8px 10px; border: 1px solid var(--line); background: var(--panel); font-size: 13px; color: var(--dim); }
.phases li.active { color: var(--text); border-color: var(--hot); }
.phases li.done { color: var(--text); }
.phase-n { color: var(--dim); font-size: 11px; }
.phase-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--line); }
.phases li.active .phase-dot { background: var(--hot); animation: pulse 0.9s ease-in-out infinite; }
.phases li.done .phase-dot { background: var(--good); }

.gauge { display: flex; align-items: center; gap: 5px; font-size: 12px; }
.gauge-label { text-transform: uppercase; letter-spacing: 0.1em; color: var(--dim); margin-right: 6px; }
.cell { width: 26px; height: 10px; background: var(--line); }
.cell.on { background: var(--hot); animation: charge 0.5s both; }
.gauge-value { margin-left: 8px; font-variant-numeric: tabular-nums; }

.lanes { display: flex; flex-direction: column; gap: 8px; }
.lane { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; }
.lane-name { color: var(--signal); width: 24px; }
.node { padding: 3px 6px; border: 1px solid var(--line); color: var(--dim); }
.node.on { border-color: var(--signal); color: var(--text); }
.node.ok { border-color: var(--good); color: var(--good); }
.wire { width: 10px; height: 1px; background: var(--line); }
.wire.on { background: var(--signal); }

.log { list-style: none; margin: 0; padding: 10px; border: 1px solid var(--line); background: rgba(0, 0, 0, 0.35); font-size: 12px; display: flex; flex-direction: column; gap: 4px; min-height: 120px; overflow-wrap: anywhere; }
.log li { animation: type-in 0.45s steps(18) both; }
.log .t { color: var(--dim); }
.log .accent { color: var(--signal); }
.log .good { color: var(--good); }
.log .bad { color: var(--bad); }
.lab-fail { margin: 0; color: var(--bad); font-size: 13px; }
.lab-actions { display: flex; }
.lab-go { font: inherit; font-size: 13px; letter-spacing: 0.08em; text-transform: uppercase; padding: 12px 18px; border: 1px solid var(--signal); background: rgba(79, 209, 197, 0.12); color: var(--text); cursor: pointer; }
.lab-go:focus-visible { outline: 2px solid var(--hot); outline-offset: 2px; }

@keyframes sweep { from { top: -22%; } to { top: 100%; } }
@keyframes pulse { 50% { opacity: 0.35; } }
@keyframes blink { 50% { opacity: 0; } }
@keyframes charge { from { transform: scaleY(0.2); opacity: 0; } to { transform: none; opacity: 1; } }
@keyframes type-in { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }
@media (prefers-reduced-motion: reduce) {
  .beam { display: none; }
  .log li, .cell.on, .lab-status::before, .phases li.active .phase-dot { animation: none; }
}
</style>
