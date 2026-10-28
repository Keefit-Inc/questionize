<script setup lang="ts">
// Select the part of a photo that holds the question: drag the corners or edges, drag inside to
// move, rotate a sideways shot. Emits the cropped region as a JPEG blob.
import { onBeforeUnmount, reactive, ref, watch } from "vue";

const props = defineProps<{ src: string; part: number }>();
const emit = defineEmits<{ done: [blob: Blob]; cancel: [] }>();

type Edge = "n" | "s" | "e" | "w" | "ne" | "nw" | "se" | "sw" | "move";
// The selection, in percent of the displayed image.
const rect = reactive({ x: 6, y: 6, w: 88, h: 88 });
const MIN = 8;
const img = ref<HTMLImageElement | null>(null);
const frame = ref<HTMLElement | null>(null);
const source = ref(props.src);
let rotatedUrl = "";
let drag: { edge: Edge; startX: number; startY: number; from: { x: number; y: number; w: number; h: number } } | null = null;

watch(
  () => props.src,
  (src) => {
    source.value = src;
    Object.assign(rect, { x: 6, y: 6, w: 88, h: 88 });
  },
);
onBeforeUnmount(() => rotatedUrl && URL.revokeObjectURL(rotatedUrl));

function start(edge: Edge, e: PointerEvent) {
  e.preventDefault();
  (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  drag = { edge, startX: e.clientX, startY: e.clientY, from: { ...rect } };
}

function move(e: PointerEvent) {
  if (!drag || !frame.value) return;
  const box = frame.value.getBoundingClientRect();
  const dx = ((e.clientX - drag.startX) / box.width) * 100;
  const dy = ((e.clientY - drag.startY) / box.height) * 100;
  const f = drag.from;
  let { x, y, w, h } = f;
  if (drag.edge === "move") {
    x = Math.min(Math.max(0, f.x + dx), 100 - f.w);
    y = Math.min(Math.max(0, f.y + dy), 100 - f.h);
  } else {
    if (drag.edge.includes("w")) { x = Math.min(Math.max(0, f.x + dx), f.x + f.w - MIN); w = f.x + f.w - x; }
    if (drag.edge.includes("e")) w = Math.min(Math.max(MIN, f.w + dx), 100 - f.x);
    if (drag.edge.includes("n")) { y = Math.min(Math.max(0, f.y + dy), f.y + f.h - MIN); h = f.y + f.h - y; }
    if (drag.edge.includes("s")) h = Math.min(Math.max(MIN, f.h + dy), 100 - f.y);
  }
  Object.assign(rect, { x, y, w, h });
}

function end() {
  drag = null;
}

async function rotate() {
  const image = img.value;
  if (!image) return;
  const canvas = document.createElement("canvas");
  canvas.width = image.naturalHeight;
  canvas.height = image.naturalWidth;
  const ctx = canvas.getContext("2d")!;
  ctx.translate(canvas.width, 0);
  ctx.rotate(Math.PI / 2);
  ctx.drawImage(image, 0, 0);
  const blob = await new Promise<Blob | null>((r) => canvas.toBlob(r, "image/jpeg", 0.92));
  if (!blob) return;
  if (rotatedUrl) URL.revokeObjectURL(rotatedUrl);
  rotatedUrl = URL.createObjectURL(blob);
  source.value = rotatedUrl;
  Object.assign(rect, { x: 6, y: 6, w: 88, h: 88 });
}

async function confirm() {
  const image = img.value;
  if (!image) return;
  const sx = (rect.x / 100) * image.naturalWidth;
  const sy = (rect.y / 100) * image.naturalHeight;
  const sw = (rect.w / 100) * image.naturalWidth;
  const sh = (rect.h / 100) * image.naturalHeight;
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(sw);
  canvas.height = Math.round(sh);
  canvas.getContext("2d")!.drawImage(image, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise<Blob | null>((r) => canvas.toBlob(r, "image/jpeg", 0.92));
  if (blob) emit("done", blob);
}

const HANDLES: Edge[] = ["nw", "n", "ne", "e", "se", "s", "sw", "w"];
</script>

<template>
  <div class="crop">
    <p class="hint">
      <strong>Part {{ part }}</strong> · Drag the corners so the box holds the passage, the question and every answer choice.
    </p>
    <div class="area">
      <div ref="frame" class="frame" @pointermove="move" @pointerup="end" @pointercancel="end">
        <img ref="img" :src="source" alt="Your photo" draggable="false" />
        <div
          class="sel"
          :style="{ left: rect.x + '%', top: rect.y + '%', width: rect.w + '%', height: rect.h + '%' }"
          @pointerdown="start('move', $event)"
        >
          <span class="grid" aria-hidden="true" />
          <span v-for="hd in HANDLES" :key="hd" class="h" :class="hd" @pointerdown.stop="start(hd, $event)" />
        </div>
      </div>
    </div>
    <div class="bar">
      <button type="button" class="ghost" @click="emit('cancel')">Retake</button>
      <button type="button" class="ghost icon" aria-label="Rotate" @click="rotate">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8 8 0 1 1-2.3-5.7M20 4v5h-5" /></svg>
      </button>
      <button type="button" class="primary" @click="confirm">Use this part</button>
    </div>
  </div>
</template>

<style scoped>
.crop { position: absolute; inset: 0; display: flex; flex-direction: column; background: #080c10; color: #e8eef2; }
.hint { margin: 0; padding: max(14px, env(safe-area-inset-top, 0px)) 16px 10px; font-size: 14px; line-height: 1.4; text-align: center; }
.area { flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center; padding: 8px 16px; }
.frame { position: relative; display: inline-block; max-width: 100%; max-height: 100%; overflow: hidden; touch-action: none; user-select: none; }
.frame img { display: block; max-width: 100%; max-height: calc(100dvh - 240px); pointer-events: none; }
.sel { position: absolute; box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.6); outline: 2px solid #4fd1c5; cursor: move; touch-action: none; }
.grid { position: absolute; inset: 0; background-image: linear-gradient(90deg, transparent 33.2%, rgba(79, 209, 197, 0.35) 33.3%, transparent 33.6%, transparent 66.5%, rgba(79, 209, 197, 0.35) 66.6%, transparent 66.9%); pointer-events: none; }
.h { position: absolute; width: 28px; height: 28px; touch-action: none; }
.h::after { content: ""; position: absolute; inset: 8px; border-radius: 50%; background: #4fd1c5; box-shadow: 0 0 0 2px #080c10; }
.h.nw { left: -14px; top: -14px; cursor: nwse-resize; }
.h.ne { right: -14px; top: -14px; cursor: nesw-resize; }
.h.se { right: -14px; bottom: -14px; cursor: nwse-resize; }
.h.sw { left: -14px; bottom: -14px; cursor: nesw-resize; }
.h.n { left: calc(50% - 14px); top: -14px; cursor: ns-resize; }
.h.s { left: calc(50% - 14px); bottom: -14px; cursor: ns-resize; }
.h.e { right: -14px; top: calc(50% - 14px); cursor: ew-resize; }
.h.w { left: -14px; top: calc(50% - 14px); cursor: ew-resize; }
.h.n::after, .h.s::after { inset: 11px 4px; border-radius: 3px; }
.h.e::after, .h.w::after { inset: 4px 11px; border-radius: 3px; }
.bar { display: grid; grid-template-columns: 1fr auto 2fr; gap: 8px; padding: 12px 16px 16px; }
.primary { padding: 13px; border-radius: 12px; border: 0; background: #4fd1c5; color: #062022; font: inherit; font-weight: 700; cursor: pointer; }
.ghost { padding: 13px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.25); background: transparent; color: inherit; font: inherit; font-weight: 600; cursor: pointer; }
.icon { width: 50px; display: flex; align-items: center; justify-content: center; padding: 0; }
.icon svg { width: 22px; height: 22px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
button:focus-visible { outline: 2px solid #4fd1c5; outline-offset: 2px; }
</style>
