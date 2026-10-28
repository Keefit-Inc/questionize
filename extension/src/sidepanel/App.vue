<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, shallowRef } from "vue";
import {
  ApiClient,
  ApiError,
  ArgumentMap,
  ChallengeCard,
  QuestionCard,
  eventKey,
  replayRunState,
  subscribeToGeneration,
  type ArgumentMapPayload,
  type FlagReason,
  type GenerationEvent,
  type Item,
  type Label,
  type QuestionType,
} from "@questionize/shared";
import { extractArticle, highlightPhrase, type PageContent } from "../page-tools";
import { errorMessage, eventLine } from "./messages";
import { DEFAULT_SERVER, loadSettings, loadToken, saveSettings, saveToken, type Settings } from "./storage";

interface Entry {
  item: Item;
  chosen: Label | null;
  busy: boolean;
  shownAt: number;
  tabId: number;
  note: string;
}

const settings = reactive<Settings>({ server: DEFAULT_SERVER, types: ["CR", "RC"], difficulty: "medium", count: 1 });
const showSettings = ref(false);
const client = shallowRef<ApiClient | null>(null);
const sourceTitle = ref("Open an article, then generate.");
const pendingSelection = ref<{ tabId: number; text: string } | null>(null);
const running = ref(false);
const log = ref<{ who: string; text: string; ok?: boolean }[]>([]);
const error = ref("");
const entries = ref<Entry[]>([]);
// Map → Challenge is the default view; practice questions are the second tab.
const mode = ref<"map" | "questions">("map");
const argMap = ref<ArgumentMapPayload | null>(null);
const mapTabId = ref<number | null>(null);
const challengeBusy = ref<number | null>(null);
let closeStream: (() => void) | null = null;
// Events can arrive twice (live, and again when catching up from the stored run); handle each once.
const seen = new Set<string>();

const FAMILIES: { value: QuestionType; label: string }[] = [
  { value: "CR", label: "Critical Reasoning" },
  { value: "RC", label: "Reading Comp" },
];

const selectionNote = computed(() => {
  const text = pendingSelection.value?.text ?? "";
  return text ? `Focusing on your highlighted passage (${text.split(/\s+/).length} words)` : "";
});

async function connect(): Promise<ApiClient> {
  const api = new ApiClient(settings.server, await loadToken(settings.server));
  if (!(await loadToken(settings.server))) {
    const device = await api.registerDevice();
    await saveToken(settings.server, device.token);
    api.setToken(device.token);
  }
  client.value = api;
  return api;
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function refreshSource() {
  const tab = await activeTab();
  sourceTitle.value = tab?.title || "Open an article, then generate.";
  if (pendingSelection.value && pendingSelection.value.tabId !== tab?.id) pendingSelection.value = null;
}

async function readPage(tabId: number): Promise<PageContent> {
  await chrome.scripting.executeScript({ target: { tabId }, files: ["vendor/Readability.js"] });
  const [{ result }] = await chrome.scripting.executeScript({ target: { tabId }, func: extractArticle });
  return result as PageContent;
}

function addEntries(items: Item[], tabId: number) {
  for (const item of items) entries.value.push({ item, chosen: null, busy: false, shownAt: Date.now(), tabId, note: "" });
}

function onEvent(event: GenerationEvent, tabId: number) {
  const key = eventKey(event);
  if (seen.has(key)) return;
  seen.add(key);
  if (event.stage === "question") addEntries([event.item], tabId);
  if (event.stage === "map") {
    argMap.value = event.map;
    mapTabId.value = tabId;
  }
  const line = eventLine(event);
  if (line) log.value.push(line);
  if (event.stage === "declined") error.value = `Skipped this page: ${event.message}`;
  if (event.stage === "failed") error.value = event.message;
  if (event.stage === "done" || event.stage === "declined" || event.stage === "failed") {
    running.value = false;
    if (event.stage === "done" && event.count === 0 && mode.value === "questions") error.value = "No questions came back. Try another article.";
  }
}

function follow(api: ApiClient, runId: number, tabId: number, loadStored: () => Promise<GenerationEvent[]>) {
  closeStream?.();
  seen.clear();
  closeStream = subscribeToGeneration(api.cableUrl(), runId, (e) => onEvent(e, tabId), {
    // Anything broadcast before the subscription was confirmed is only in the stored run.
    onConnected: async () => {
      for (const e of await loadStored()) onEvent(e, tabId);
    },
    onRejected: () => {
      error.value = "Couldn't follow this run's progress. Reopen the panel and try again.";
      running.value = false;
    },
  });
}

async function mapArgument() {
  if (running.value) return;
  error.value = "";
  argMap.value = null;
  log.value = [{ who: "Analyst", text: "Reading the page" }];
  running.value = true;
  try {
    const tab = await activeTab();
    if (!tab?.id || !/^https?:/.test(tab.url || "")) throw new Error("Open a regular web article first.");
    const tabId = tab.id;
    const page = await readPage(tabId);
    const selection = pendingSelection.value?.tabId === tabId ? pendingSelection.value.text : page.selection;
    const api = client.value ?? (await connect());
    const res = await api.createMap({ url: page.url, title: page.title, text: page.text, selection });
    if (res.status === "cached") {
      log.value.push({ who: "Bank", text: "This article's argument is already mapped", ok: true });
      argMap.value = res.map;
      mapTabId.value = tabId;
      running.value = false;
    } else {
      follow(api, res.run_id, tabId, async () => {
        const state = await api.getRun(res.run_id);
        const stored = replayRunState(state);
        if (state.status === "completed") stored.push({ stage: "map", map: await api.getMap(res.run_id) });
        return stored;
      });
    }
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) await saveToken(settings.server, "");
    error.value = errorMessage(e, settings.server);
    running.value = false;
  }
}

async function answerChallenge(index: number, label: Label) {
  if (!client.value || !argMap.value) return;
  challengeBusy.value = index;
  try {
    const updated = await client.value.answerChallenge(argMap.value.run_id, index, label);
    argMap.value.challenges = argMap.value.challenges.map((c) => (c.index === index ? updated : c));
  } catch (e) {
    error.value = errorMessage(e, settings.server);
  } finally {
    challengeBusy.value = null;
  }
}

async function locateAnchor(anchor: string) {
  if (mapTabId.value === null) return;
  try {
    await chrome.scripting.executeScript({ target: { tabId: mapTabId.value }, func: highlightPhrase, args: [anchor] });
  } catch {
    error.value = "Couldn't highlight that passage on the page.";
  }
}

async function generate() {
  if (running.value) return;
  if (!settings.types.length) {
    error.value = "Pick at least one question type.";
    return;
  }
  error.value = "";
  log.value = [{ who: "Analyst", text: "Reading the page" }];
  running.value = true;
  try {
    const tab = await activeTab();
    if (!tab?.id || !/^https?:/.test(tab.url || "")) throw new Error("Open a regular web article first.");
    const tabId = tab.id;
    const page = await readPage(tabId);
    const selection = pendingSelection.value?.tabId === tabId ? pendingSelection.value.text : page.selection;
    const api = client.value ?? (await connect());
    const res = await api.generate({
      url: page.url,
      title: page.title,
      text: page.text,
      selection,
      types: settings.types,
      difficulty: settings.difficulty,
      count_per_type: settings.count,
    });
    if (res.status === "cached") {
      log.value.push({ who: "Bank", text: `Found ${res.items.length} verified questions for this article`, ok: true });
      addEntries(res.items, tabId);
      running.value = false;
    } else {
      follow(api, res.run_id, tabId, async () => replayRunState(await api.getRun(res.run_id)));
    }
    pendingSelection.value = null;
    await chrome.storage.session.remove("pendingSelection");
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) await saveToken(settings.server, "");
    error.value = errorMessage(e, settings.server);
    running.value = false;
  }
}

async function answer(entry: Entry, label: Label) {
  if (!client.value) return;
  entry.busy = true;
  try {
    const res = await client.value.attempt(entry.item.id, label, Date.now() - entry.shownAt);
    entry.item = res.item;
    entry.chosen = label;
    const change = res.rating_changes[`${res.item.family}:${res.item.subtype}`];
    entry.note = change
      ? `Rating ${Math.round(change.before)} → ${Math.round(change.after)} · +${res.xp_awarded} XP`
      : "Practice attempt — only your first answer counts toward your rating.";
  } catch (e) {
    error.value = errorMessage(e, settings.server);
  } finally {
    entry.busy = false;
  }
}

async function flag(entry: Entry, reason: FlagReason, comment: string) {
  try {
    const res = await client.value?.feedback(entry.item.id, { kind: "flag", reason, comment });
    if (res?.review_started) entry.note = "Your report started an automatic re-review of this question.";
  } catch (e) {
    error.value = errorMessage(e, settings.server);
  }
}

async function locate(entry: Entry, anchor: string) {
  try {
    await chrome.scripting.executeScript({ target: { tabId: entry.tabId }, func: highlightPhrase, args: [anchor] });
  } catch {
    error.value = "Couldn't highlight that passage on the page.";
  }
}

async function applySettings() {
  settings.server = (settings.server || DEFAULT_SERVER).replace(/\/+$/, "");
  await saveSettings({ ...settings, types: [...settings.types] });
  client.value = null;
  try {
    await connect();
  } catch (e) {
    error.value = errorMessage(e, settings.server);
  }
}

function onSessionChange(changes: Record<string, chrome.storage.StorageChange>) {
  if ("pendingSelection" in changes) {
    pendingSelection.value = (changes.pendingSelection.newValue as typeof pendingSelection.value) ?? null;
    refreshSource();
  }
}

onMounted(async () => {
  Object.assign(settings, await loadSettings());
  pendingSelection.value = ((await chrome.storage.session.get("pendingSelection")).pendingSelection as typeof pendingSelection.value) ?? null;
  chrome.storage.session.onChanged.addListener(onSessionChange);
  chrome.tabs.onActivated.addListener(refreshSource);
  chrome.tabs.onUpdated.addListener(refreshSource);
  refreshSource();
  connect().catch((e) => (error.value = errorMessage(e, settings.server)));
});

onBeforeUnmount(() => {
  closeStream?.();
  chrome.storage.session.onChanged.removeListener(onSessionChange);
  chrome.tabs.onActivated.removeListener(refreshSource);
  chrome.tabs.onUpdated.removeListener(refreshSource);
});
</script>

<template>
  <header class="top">
    <h1>Questionize</h1>
    <button class="icon" title="Settings" :aria-expanded="showSettings" @click="showSettings = !showSettings">⚙</button>
  </header>

  <section v-if="showSettings" class="settings">
    <label>
      <span>Server</span>
      <input v-model.trim="settings.server" type="url" :placeholder="DEFAULT_SERVER" @change="applySettings" />
    </label>
    <p class="hint">{{ client ? "Connected" : "Not connected" }} · use http://localhost:3000 for local development</p>
  </section>

  <nav class="tabs" role="tablist">
    <button role="tab" :aria-selected="mode === 'map'" :class="{ on: mode === 'map' }" @click="mode = 'map'">Map &amp; challenge</button>
    <button role="tab" :aria-selected="mode === 'questions'" :class="{ on: mode === 'questions' }" @click="mode = 'questions'">Practice questions</button>
  </nav>

  <section class="controls">
    <p class="source"><span class="muted">Reading</span> {{ sourceTitle }}</p>
    <p v-if="selectionNote" class="selection">{{ selectionNote }}</p>
  </section>

  <section v-if="mode === 'map'" class="controls">
    <button class="primary" :disabled="running" @click="mapArgument">{{ running ? "Working…" : "Map this argument" }}</button>
  </section>

  <section v-else class="controls">
    <fieldset class="types">
      <label v-for="f in FAMILIES" :key="f.value" class="chip">
        <input v-model="settings.types" type="checkbox" :value="f.value" @change="applySettings" /><span>{{ f.label }}</span>
      </label>
    </fieldset>
    <div class="row">
      <label>Difficulty
        <select v-model="settings.difficulty" @change="applySettings">
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>
      </label>
      <label>Per type
        <select v-model.number="settings.count" @change="applySettings">
          <option :value="1">1</option>
          <option :value="2">2</option>
          <option :value="3">3</option>
        </select>
      </label>
    </div>
    <button class="primary" :disabled="running" @click="generate">{{ running ? "Working…" : "Questionize this page" }}</button>
  </section>

  <ol v-if="log.length" class="log" aria-live="polite">
    <li v-for="(line, i) in log" :key="i" :class="{ ok: line.ok === true, fail: line.ok === false }">
      <span class="who">{{ line.who }}</span> {{ line.text }}
    </li>
  </ol>

  <p v-if="error" class="error" role="alert">{{ error }}</p>

  <section v-if="mode === 'map' && argMap">
    <ArgumentMap :map="argMap" @locate="locateAnchor" />
    <p class="section-head">Challenge the argument</p>
    <ChallengeCard
      v-for="c in argMap.challenges"
      :key="c.index"
      :challenge="c"
      :busy="challengeBusy === c.index"
      @answer="(l) => answerChallenge(c.index, l)"
    />
  </section>

  <section v-if="mode === 'questions'">
    <div v-for="entry in entries" :key="entry.item.id">
      <QuestionCard :item="entry.item" :chosen="entry.chosen" :busy="entry.busy" @answer="(l) => answer(entry, l)" @locate="(a) => locate(entry, a)" @flag="(r, c) => flag(entry, r, c)" />
      <p v-if="entry.note" class="note">{{ entry.note }}</p>
    </div>
  </section>
</template>

<style scoped>
.top { display: flex; align-items: center; justify-content: space-between; }
h1 { font-size: 18px; margin: 0; }
.icon { border: 0; background: transparent; font-size: 18px; cursor: pointer; color: inherit; }
.settings { margin: 8px 0; padding: 10px; border-radius: 10px; background: rgba(127, 127, 127, 0.1); }
.settings label { display: flex; flex-direction: column; gap: 4px; }
.settings input { padding: 6px; border-radius: 6px; border: 1px solid rgba(127, 127, 127, 0.4); font: inherit; }
.hint, .muted { font-size: 12px; opacity: 0.7; }
.controls { display: flex; flex-direction: column; gap: 8px; margin: 10px 0; }
.source { margin: 0; }
.selection { margin: 0; font-size: 12px; color: #3b6fd0; }
.types { border: 0; padding: 0; margin: 0; display: flex; gap: 6px; }
.chip { display: flex; align-items: center; gap: 4px; padding: 4px 8px; border-radius: 12px; background: rgba(127, 127, 127, 0.12); font-size: 13px; }
.row { display: flex; gap: 12px; font-size: 13px; }
.primary { padding: 10px; border-radius: 8px; border: 0; background: #3b6fd0; color: #fff; cursor: pointer; }
.primary:disabled { opacity: 0.6; }
.log { margin: 8px 0; padding-left: 18px; font-size: 12px; display: flex; flex-direction: column; gap: 2px; }
.log .who { font-weight: 600; }
.log .ok { color: #2e9d5b; }
.log .fail { color: #d0563b; }
.error { color: #d0563b; font-size: 13px; }
.note { margin: -6px 0 10px; font-size: 12px; opacity: 0.8; }
.tabs { display: flex; gap: 4px; margin: 8px 0; }
.tabs button { flex: 1; padding: 6px; border-radius: 8px; border: 1px solid rgba(127, 127, 127, 0.3); background: transparent; color: inherit; cursor: pointer; }
.tabs button.on { background: rgba(59, 111, 208, 0.12); border-color: #3b6fd0; font-weight: 600; }
.section-head { font-weight: 700; margin: 16px 0 4px; }
</style>
