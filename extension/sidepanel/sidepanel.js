import { extractArticle, highlightPhrase } from "../content/page-tools.js";

const DEFAULT_SERVER = "http://localhost:8000";
const SUBTYPE_LABEL = (s) => s.replace(/_/g, " ");
const TYPE_LABEL = { RC: "Reading Comp", CR: "Critical Reasoning", SC: "Sentence Correction" };
const AGENT_FOR_STAGE = {
  analyze: "Analyst",
  analyzed: "Analyst",
  plan: "Planner",
  write: "Writer",
  solve: "Solver",
  critic: "Critic",
  verdict: "Verifier",
  revise: "Reviser",
  error: "Error",
};

const TRAP_LABELS = {
  out_of_scope: "Out of scope",
  too_extreme: "Too extreme",
  reversal: "Reversal",
  half_right: "Half right",
  unsupported: "Unsupported",
  irrelevant: "Irrelevant",
  distortion: "Distortion",
  grammar_error: "Grammar error",
  changes_meaning: "Changes meaning",
};

const $ = (id) => document.getElementById(id);
const els = {
  settingsToggle: $("settings-toggle"),
  settings: $("settings"),
  serverUrl: $("server-url"),
  devToken: $("dev-token"),
  serverStatus: $("server-status"),
  sourceTitle: $("source-title"),
  sourceSel: $("source-sel"),
  difficulty: $("difficulty"),
  count: $("count"),
  generate: $("generate"),
  progress: $("progress"),
  progressLog: $("progress-log"),
  error: $("error"),
  questions: $("questions"),
  stats: $("stats"),
  tpl: $("question-tpl"),
};

let pendingSelection = null; // { tabId, text } from the right-click menu
let running = false;

// ------------------------------------------------------------------ settings

async function loadSettings() {
  const s = await chrome.storage.sync.get({
    serverUrl: DEFAULT_SERVER,
    types: ["CR", "RC"],
    difficulty: "medium",
    count: "1",
  });
  els.serverUrl.value = s.serverUrl;
  // Local-only stopgap until the panel talks to Rails; never synced across devices.
  ({ devToken: els.devToken.value = "" } = await chrome.storage.local.get("devToken"));
  els.difficulty.value = s.difficulty;
  els.count.value = String(s.count);
  for (const box of document.querySelectorAll('input[name="type"]')) {
    box.checked = s.types.includes(box.value);
  }
}

function currentOptions() {
  const types = [...document.querySelectorAll('input[name="type"]:checked')].map((b) => b.value);
  return {
    serverUrl: (els.serverUrl.value || DEFAULT_SERVER).replace(/\/+$/, ""),
    devToken: els.devToken.value.trim(),
    types,
    difficulty: els.difficulty.value,
    count: Number(els.count.value),
  };
}

async function saveSettings() {
  const o = currentOptions();
  await chrome.storage.sync.set({ serverUrl: o.serverUrl, types: o.types, difficulty: o.difficulty, count: String(o.count) });
  await chrome.storage.local.set({ devToken: o.devToken });
}

async function checkServer() {
  const { serverUrl } = currentOptions();
  els.serverStatus.textContent = "Checking…";
  try {
    const r = await fetch(`${serverUrl}/health`);
    const j = await r.json();
    els.serverStatus.textContent = `Connected · ${j.model}${j.solver_model !== j.model ? ` + solver ${j.solver_model}` : ""}`;
  } catch {
    els.serverStatus.textContent = "Can't reach the server. Is it running?";
  }
}

// ------------------------------------------------------------------ page access

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function refreshSource() {
  const tab = await activeTab();
  els.sourceTitle.textContent = tab?.title || "Open an article, then generate.";
  const sel = pendingSelection && pendingSelection.tabId === tab?.id ? pendingSelection.text : "";
  els.sourceSel.hidden = !sel;
  els.sourceSel.textContent = sel ? `Focusing on your highlighted passage (${sel.split(/\s+/).length} words)` : "";
}

async function readPage(tabId) {
  await chrome.scripting.executeScript({ target: { tabId }, files: ["vendor/Readability.js"] });
  const [{ result }] = await chrome.scripting.executeScript({ target: { tabId }, func: extractArticle });
  return result;
}

async function locate(tabId, phrase) {
  try {
    const [{ result }] = await chrome.scripting.executeScript({ target: { tabId }, func: highlightPhrase, args: [phrase] });
    return result;
  } catch {
    return false;
  }
}

// ------------------------------------------------------------------ progress UI

function logStep(event) {
  const li = document.createElement("li");
  const dot = document.createElement("span");
  dot.className = "dot";
  const text = document.createElement("span");
  const who = document.createElement("span");
  who.className = "who";
  const qn = typeof event.index === "number" ? ` Q${event.index + 1}` : "";
  who.textContent = `${AGENT_FOR_STAGE[event.stage] || event.stage}${qn}`;
  text.append(who, document.createTextNode(event.message || ""));
  li.append(dot, text);

  if (event.stage === "verdict") li.className = event.passed ? "ok" : "fail";
  else if (event.stage === "error") li.className = "fail";
  else li.className = "active";

  // Only the newest in-flight step per question pulses.
  for (const prev of els.progressLog.querySelectorAll(`li.active[data-q="${event.index ?? "all"}"]`)) {
    prev.className = "ok";
  }
  li.dataset.q = event.index ?? "all";
  els.progressLog.append(li);
  li.scrollIntoView({ block: "nearest" });
}

function settleProgress() {
  for (const li of els.progressLog.querySelectorAll("li.active")) li.className = "ok";
}

function showError(msg) {
  els.error.hidden = !msg;
  els.error.textContent = msg || "";
}

// ------------------------------------------------------------------ question cards

/** Render text with [[underlined]] spans as safe DOM nodes (never innerHTML). */
function renderPassage(container, passage) {
  container.replaceChildren();
  const parts = passage.split(/\[\[|\]\]/);
  parts.forEach((part, i) => {
    if (!part) return;
    if (i % 2 === 1) {
      const u = document.createElement("u");
      u.textContent = part;
      container.append(u);
    } else {
      container.append(document.createTextNode(part));
    }
  });
}

function renderQuestion(vq, tabId) {
  const { question: q, verification: v } = vq;
  const node = els.tpl.content.firstElementChild.cloneNode(true);
  node.querySelector(".type").textContent = TYPE_LABEL[q.type] || q.type;
  node.querySelector(".subtype").textContent = SUBTYPE_LABEL(q.subtype);
  const badge = node.querySelector(".badge");
  badge.textContent = v.verified ? "✓ Verified" : "⚠ Unverified";
  badge.className = `badge ${v.verified ? "verified" : "unverified"}`;
  badge.title = v.verified
    ? "An independent solver reached the keyed answer and a critic confirmed it is unique."
    : "Reviewers could not fully confirm a single correct answer. Treat with care.";

  renderPassage(node.querySelector(".passage"), q.passage);
  node.querySelector(".stem").textContent = q.stem;

  const list = node.querySelector(".choices");
  const check = node.querySelector(".check");
  const locateBtn = node.querySelector(".locate");
  let picked = null;
  const buttons = q.choices.map((c) => {
    const li = document.createElement("li");
    const b = document.createElement("button");
    const lbl = document.createElement("span");
    lbl.className = "lbl";
    lbl.textContent = c.label;
    const txt = document.createElement("span");
    txt.textContent = c.text;
    b.append(lbl, txt);
    b.dataset.label = c.label;
    b.addEventListener("click", () => {
      picked = c.label;
      for (const other of buttons) other.classList.toggle("selected", other === b);
      check.disabled = false;
    });
    li.append(b);
    list.append(li);
    return b;
  });

  check.addEventListener("click", async () => {
    if (!picked) return;
    const correct = picked === q.correct_label;
    for (const b of buttons) {
      b.disabled = true;
      b.classList.remove("selected");
      if (b.dataset.label === q.correct_label) b.classList.add("correct");
      else if (b.dataset.label === picked) b.classList.add("wrong");
    }
    check.hidden = true;
    revealAnswer(node, q, v, picked, correct);
    if (q.source_anchor) locateBtn.hidden = false;
    await recordAttempt(q, correct);
  });

  locateBtn.addEventListener("click", async () => {
    const ok = await locate(tabId, q.source_anchor);
    locateBtn.textContent = ok ? "Shown in article ↗" : "Couldn't find it on the page";
  });

  els.questions.append(node);
}

function revealAnswer(node, q, v, picked, correct) {
  const reveal = node.querySelector(".reveal");
  const verdict = reveal.querySelector(".verdict");
  const pickedTrap = TRAP_LABELS[q.choice_rationales.find((r) => r.label === picked)?.trap];
  verdict.textContent = correct
    ? `Correct — ${q.correct_label}`
    : `Not quite. You chose ${picked}${pickedTrap ? ` (trap: ${pickedTrap})` : ""}; the answer is ${q.correct_label}.`;
  verdict.className = `verdict ${correct ? "good" : "bad"}`;
  reveal.querySelector(".explanation").textContent = q.explanation;

  const rl = reveal.querySelector(".rationales ol");
  for (const r of q.choice_rationales) {
    const li = document.createElement("li");
    if (r.label === q.correct_label) li.className = "key";
    const l = document.createElement("strong");
    l.textContent = r.label;
    const t = document.createElement("span");
    if (TRAP_LABELS[r.trap]) {
      const tag = document.createElement("em");
      tag.className = "trap";
      tag.textContent = TRAP_LABELS[r.trap];
      t.append(tag, " ");
    }
    t.append(r.rationale);
    li.append(l, t);
    rl.append(li);
  }
  if (!correct) reveal.querySelector(".rationales").open = true;

  const vb = reveal.querySelector(".verify-body");
  const p = document.createElement("p");
  p.textContent =
    `Skill: ${q.skill}. Draft attempts: ${v.attempts}. Blind solver (${v.solver_model}) chose ${v.solver_answer} ` +
    `with ${Math.round(v.solver_confidence * 100)}% confidence. Critic verdict: ${v.critic_verdict}` +
    (v.distractor_quality ? `, distractor quality ${v.distractor_quality}/5.` : ".");
  vb.append(p);
  if (v.issues?.length) {
    const ul = document.createElement("ul");
    for (const i of v.issues) {
      const li = document.createElement("li");
      li.textContent = i;
      ul.append(li);
    }
    vb.append(ul);
  }
  reveal.hidden = false;
}

// ------------------------------------------------------------------ progress stats

async function recordAttempt(q, correct) {
  const { stats = {} } = await chrome.storage.local.get("stats");
  const key = `${q.type}:${q.subtype}`;
  const s = (stats[key] ||= { n: 0, correct: 0 });
  s.n += 1;
  s.correct += correct ? 1 : 0;
  await chrome.storage.local.set({ stats });
  renderStats(stats);
}

function renderStats(stats) {
  const entries = Object.entries(stats || {});
  if (!entries.length) {
    els.stats.hidden = true;
    return;
  }
  const n = entries.reduce((a, [, s]) => a + s.n, 0);
  const c = entries.reduce((a, [, s]) => a + s.correct, 0);
  const weakest = entries
    .filter(([, s]) => s.n >= 2)
    .sort((a, b) => a[1].correct / a[1].n - b[1].correct / b[1].n)[0];
  els.stats.replaceChildren();
  const strong = document.createElement("strong");
  strong.textContent = `${c}/${n} correct`;
  els.stats.append(strong);
  if (weakest) {
    const [type, sub] = weakest[0].split(":");
    els.stats.append(document.createTextNode(` · Focus area: ${TYPE_LABEL[type]} — ${SUBTYPE_LABEL(sub)}`));
  }
  els.stats.hidden = false;
}

// ------------------------------------------------------------------ generate

async function* ndjson(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let nl;
    while ((nl = buf.indexOf("\n")) !== -1) {
      const line = buf.slice(0, nl).trim();
      buf = buf.slice(nl + 1);
      if (line) yield JSON.parse(line);
    }
  }
  if (buf.trim()) yield JSON.parse(buf);
}

async function generate() {
  if (running) return;
  const opts = currentOptions();
  if (!opts.types.length) {
    showError("Pick at least one question type.");
    return;
  }
  running = true;
  els.generate.disabled = true;
  els.generate.textContent = "Working…";
  showError("");
  els.questions.replaceChildren();
  els.progressLog.replaceChildren();
  els.progress.hidden = false;

  try {
    await saveSettings();
    const tab = await activeTab();
    if (!tab?.id || !/^https?:/.test(tab.url || "")) throw new Error("Open a regular web article first.");

    logStep({ stage: "analyze", message: "Reading the page" });
    const page = await readPage(tab.id);
    const selection =
      pendingSelection && pendingSelection.tabId === tab.id ? pendingSelection.text : page.selection;
    if ((page.text || "").length < 200) throw new Error("Couldn't find enough article text on this page.");

    const res = await fetch(`${opts.serverUrl}/v1/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Internal-Token": opts.devToken },
      body: JSON.stringify({
        text: page.text,
        title: page.title,
        url: page.url,
        selection: selection || "",
        types: opts.types,
        count_per_type: opts.count,
        difficulty: opts.difficulty,
      }),
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(typeof detail.detail === "string" ? detail.detail : `Server error ${res.status}`);
    }

    let received = 0;
    for await (const ev of ndjson(res)) {
      if (ev.stage === "question") {
        renderQuestion(ev.question, tab.id);
        received += 1;
      } else if (ev.stage === "declined") {
        throw new Error(`Skipped this page: ${ev.message}`);
      } else if (ev.stage === "failed") {
        throw new Error(ev.message);
      } else if (ev.stage === "done") {
        break;
      } else {
        logStep(ev);
      }
    }
    settleProgress();
    if (!received) throw new Error("No questions came back. Try another article.");
    pendingSelection = null;
    await chrome.storage.session.remove("pendingSelection");
    refreshSource();
  } catch (e) {
    settleProgress();
    showError(e.message === "Failed to fetch" ? `Can't reach ${opts.serverUrl}. Start the server or check Settings.` : e.message);
  } finally {
    running = false;
    els.generate.disabled = false;
    els.generate.textContent = "Questionize this page";
  }
}

// ------------------------------------------------------------------ wiring

els.generate.addEventListener("click", generate);
els.settingsToggle.addEventListener("click", () => {
  const open = els.settings.hidden;
  els.settings.hidden = !open;
  els.settingsToggle.setAttribute("aria-expanded", String(open));
  if (open) checkServer();
});
els.devToken.addEventListener("change", saveSettings);
els.serverUrl.addEventListener("change", async () => {
  await saveSettings();
  checkServer();
});
for (const el of [els.difficulty, els.count, ...document.querySelectorAll('input[name="type"]')]) {
  el.addEventListener("change", saveSettings);
}

chrome.tabs.onActivated.addListener(refreshSource);
chrome.tabs.onUpdated.addListener((_id, info) => info.title && refreshSource());
chrome.storage.session.onChanged.addListener((changes) => {
  if (changes.pendingSelection) {
    pendingSelection = changes.pendingSelection.newValue || null;
    refreshSource();
  }
});

(async function init() {
  await loadSettings();
  ({ pendingSelection = null } = await chrome.storage.session.get("pendingSelection"));
  const { stats } = await chrome.storage.local.get("stats");
  renderStats(stats);
  refreshSource();
})();
