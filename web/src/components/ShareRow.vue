<script setup lang="ts">
// Share a bank question: Facebook, Threads and WhatsApp links (they read the page's preview
// tags), an image card for Instagram through the phone's share sheet, X, and a copied link.
// Only shared-bank questions get this; questions snapped from someone's book never do.
import { computed, ref } from "vue";
import { FAMILY_LABELS, subtypeLabel, type Item } from "@questionize/shared";

const props = defineProps<{ item: Item }>();
const url = computed(() => `${window.location.origin}/q/${props.item.id}`);
const text = "Can you solve this reasoning question?";
const enc = encodeURIComponent;
const links = computed(() => [
  { name: "Facebook", href: `https://www.facebook.com/sharer/sharer.php?u=${enc(url.value)}` },
  { name: "Threads", href: `https://www.threads.net/intent/post?text=${enc(`${text} ${url.value}`)}` },
  { name: "WhatsApp", href: `https://wa.me/?text=${enc(`${text} ${url.value}`)}` },
  { name: "X", href: `https://x.com/intent/post?text=${enc(text)}&url=${enc(url.value)}` },
]);
const status = ref("");

function wrap(ctx: CanvasRenderingContext2D, words: string, width: number, maxLines: number): string[] {
  const lines: string[] = [];
  let line = "";
  for (const word of words.split(/\s+/)) {
    const test = line ? `${line} ${word}` : word;
    if (ctx.measureText(test).width > width && line) {
      lines.push(line);
      line = word;
      if (lines.length === maxLines) break;
    } else line = test;
  }
  if (lines.length < maxLines && line) lines.push(line);
  if (lines.length === maxLines && words.length > lines.join(" ").length) lines[maxLines - 1] = lines[maxLines - 1].replace(/\s*\S*$/, "…");
  return lines;
}

/** A 1080×1350 card (Instagram's portrait size) with the question, never the answer. */
async function card(): Promise<Blob | null> {
  const W = 1080;
  const H = 1350;
  const c = document.createElement("canvas");
  c.width = W;
  c.height = H;
  const ctx = c.getContext("2d")!;
  const grad = ctx.createLinearGradient(0, 0, W, H);
  grad.addColorStop(0, "#0b1116");
  grad.addColorStop(1, "#173040");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = "#4fd1c5";
  ctx.font = "700 40px system-ui, sans-serif";
  ctx.fillText("Questionize", 80, 120);
  ctx.fillStyle = "rgba(255,255,255,0.65)";
  ctx.font = "500 34px system-ui, sans-serif";
  ctx.fillText(`${FAMILY_LABELS[props.item.family]} · ${subtypeLabel(props.item.subtype)}`, 80, 180);
  ctx.fillStyle = "#e8eef2";
  ctx.font = "400 38px Georgia, serif";
  let y = 280;
  for (const l of wrap(ctx, props.item.passage.replace(/\[\[|\]\]/g, ""), W - 160, 9)) {
    ctx.fillText(l, 80, y);
    y += 54;
  }
  y += 30;
  ctx.font = "700 40px system-ui, sans-serif";
  for (const l of wrap(ctx, props.item.stem, W - 160, 4)) {
    ctx.fillText(l, 80, y);
    y += 56;
  }
  ctx.fillStyle = "#ffb454";
  ctx.font = "700 46px system-ui, sans-serif";
  ctx.fillText("Can you solve it?", 80, H - 150);
  ctx.fillStyle = "rgba(255,255,255,0.7)";
  ctx.font = "500 32px system-ui, sans-serif";
  ctx.fillText(url.value.replace(/^https?:\/\//, ""), 80, H - 95);
  return new Promise((r) => c.toBlob(r, "image/png"));
}

async function shareImage() {
  status.value = "";
  const blob = await card();
  if (!blob) return;
  const file = new File([blob], `questionize-${props.item.id}.png`, { type: "image/png" });
  if (navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ files: [file], text: `${text} ${url.value}` });
    } catch {
      // The learner closed the share sheet.
    }
    return;
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = file.name;
  a.click();
  URL.revokeObjectURL(a.href);
  status.value = "Image saved. Post it on Instagram from your photos.";
}

async function copy() {
  try {
    await navigator.clipboard.writeText(url.value);
    status.value = "Link copied";
  } catch {
    status.value = url.value;
  }
}
</script>

<template>
  <section class="share" aria-label="Share this question">
    <p class="label">Challenge a friend</p>
    <div class="buttons">
      <a v-for="l in links" :key="l.name" :href="l.href" target="_blank" rel="noopener noreferrer" class="btn">{{ l.name }}</a>
      <button type="button" class="btn ig" @click="shareImage">Instagram</button>
      <button type="button" class="btn" @click="copy">Copy link</button>
    </div>
    <p v-if="status" class="status" role="status">{{ status }}</p>
  </section>
</template>

<style scoped>
.share { display: flex; flex-direction: column; gap: 8px; margin-top: 16px; }
.label { margin: 0; font-size: 12px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
.buttons { display: flex; flex-wrap: wrap; gap: 8px; }
.btn { padding: 8px 14px; border-radius: 999px; border: 1px solid var(--line); background: var(--surface); color: inherit; font: inherit; font-size: 14px; font-weight: 600; text-decoration: none; cursor: pointer; }
.btn.ig { background: linear-gradient(45deg, #f9ce34, #ee2a7b, #6228d7); color: #fff; border-color: transparent; }
.status { margin: 0; font-size: 13px; color: var(--muted); overflow-wrap: anywhere; }
</style>
