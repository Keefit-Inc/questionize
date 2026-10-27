// Functions injected into the reader's tab with chrome.scripting.executeScript.
// They must be self-contained: no closures over side-panel variables.

/** Extract the main article with Readability (injected beforehand), falling back to visible text. */
export function extractArticle() {
  const selection = String(window.getSelection() || "").trim();
  let title = document.title;
  let text = "";
  try {
    // eslint-disable-next-line no-undef
    const parsed = new Readability(document.cloneNode(true)).parse();
    if (parsed && parsed.textContent) {
      title = parsed.title || title;
      text = parsed.textContent;
    }
  } catch (e) {
    console.warn("[Questionize] Readability failed", e);
  }
  if (text.trim().length < 400) {
    const root = document.querySelector("article, main, [role=main]") || document.body;
    text = root.innerText;
  }
  text = text.replace(/[ \t]+/g, " ").replace(/\n{3,}/g, "\n\n").trim();
  return { title, url: location.href, text, selection };
}

/** Highlight the first occurrence of `phrase` on the page and scroll to it. */
export function highlightPhrase(phrase) {
  const STYLE_ID = "questionize-style";
  if (!document.getElementById(STYLE_ID)) {
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent =
      "mark.questionize-hit{background:#ffe08a;color:inherit;border-radius:3px;box-shadow:0 0 0 3px #ffe08a;transition:box-shadow .6s}" +
      "mark.questionize-hit.pulse{box-shadow:0 0 0 8px rgba(255,200,60,.45)}";
    document.head.appendChild(style);
  }
  for (const m of document.querySelectorAll("mark.questionize-hit")) {
    m.replaceWith(...m.childNodes);
  }
  const fold = (ch) => (/[\u2018\u2019]/.test(ch) ? "'" : /[\u201c\u201d]/.test(ch) ? '"' : ch.toLowerCase());
  const target = (phrase || "").replace(/\s+/g, " ").trim().split("").map(fold).join("");
  if (target.length < 4) return false;

  // Flatten visible text with collapsed whitespace, remembering where each char came from,
  // so phrases spanning inline tags (links, <em>) still match.
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
    acceptNode: (n) =>
      n.parentElement && !n.parentElement.closest("script,style,noscript,textarea,input")
        ? NodeFilter.FILTER_ACCEPT
        : NodeFilter.FILTER_REJECT,
  });
  const nodes = [];
  const map = []; // map[i] = [nodeIndex, offsetInNode]
  let flat = "";
  let prevSpace = true;
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const ni = nodes.push(n) - 1;
    const v = n.nodeValue;
    for (let k = 0; k < v.length; k++) {
      const isSpace = /\s/.test(v[k]);
      if (isSpace && prevSpace) continue;
      flat += isSpace ? " " : fold(v[k]);
      map.push([ni, k]);
      prevSpace = isSpace;
    }
  }

  // Try the whole phrase, then progressively shorter prefixes.
  let idx = -1;
  let len = 0;
  for (const cut of [target.length, 80, 50, 30]) {
    const probe = target.slice(0, cut);
    idx = flat.indexOf(probe);
    if (idx !== -1) {
      len = probe.length;
      break;
    }
  }
  if (idx === -1) return false;

  // Group the matched chars by text node and wrap each piece in <mark>.
  const pieces = new Map();
  for (let i = idx; i < idx + len; i++) {
    const [ni, k] = map[i];
    const p = pieces.get(ni);
    if (p) p.to = k + 1;
    else pieces.set(ni, { from: k, to: k + 1 });
  }
  let first = null;
  for (const [ni, { from, to }] of pieces) {
    const range = document.createRange();
    range.setStart(nodes[ni], from);
    range.setEnd(nodes[ni], to);
    const mark = document.createElement("mark");
    mark.className = "questionize-hit";
    range.surroundContents(mark);
    first = first || mark;
  }
  if (first) {
    first.scrollIntoView({ behavior: "smooth", block: "center" });
    first.classList.add("pulse");
    setTimeout(() => first.classList.remove("pulse"), 900);
  }
  return Boolean(first);
}
