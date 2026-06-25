/* ============================================================
   Learning Curve — Case Workspace front-end
   POST /ask (grounded answers), GET /threads (history), GET /documents (source).
   Matter selection: visible case cards drive a hidden <select id="matter-select">,
   the canonical source for the matter sent to the backend.
   ============================================================ */

const form = document.getElementById("ask-form");
const questionInput = document.getElementById("question-input");
const matterSelect = document.getElementById("matter-select");
const roleSelect = document.getElementById("role-select");
const hintRole = document.getElementById("hint-role");
const caseSearch = document.getElementById("case-search");
const transcript = document.getElementById("transcript");
const errorBanner = document.getElementById("error-banner");
const submitButton = document.getElementById("submit-button");

const caseCards = Array.from(document.querySelectorAll(".case-card"));
const caseName = document.getElementById("case-name");
const caseStatus = document.getElementById("case-status");
const caseDocLabel = document.getElementById("case-doclabel");

const turnTemplate = document.getElementById("turn-template");
const pendingTemplate = document.getElementById("pending-template");
const evidenceCardTemplate = document.getElementById("evidence-card-template");

const drawer = document.getElementById("drawer");
const scrim = document.getElementById("scrim");
const drawerClose = document.getElementById("drawer-close");
const drawerQuestion = document.getElementById("drawer-question");
const drawerMeta = document.getElementById("drawer-meta");
const drawerMain = document.getElementById("drawer-main");
const drawerPassages = document.getElementById("drawer-passages");
const evidenceHandle = document.getElementById("evidence-handle");
const openCorpusBtn = document.getElementById("open-corpus");

const corpusItems = Array.from(document.querySelectorAll(".corpus-item"));
const corpusCount = document.getElementById("corpus-count");
const sourceView = document.getElementById("source-view");
const sourceBack = document.getElementById("source-back");
const sourceTitle = document.getElementById("source-title");
const sourceMeta = document.getElementById("source-meta");
const sourceText = document.getElementById("source-text");

// Captured before any thread rebuild so we can restore the empty state per case.
const emptyStateTpl = document.getElementById("empty-state").cloneNode(true);

let focusPayload = null; // payload currently shown in the drawer
let activeMarker = null; // citation marker highlighted in the drawer
let threadToken = 0;     // guards against out-of-order thread loads

/* ---------- role / matter accessors ---------- */
function currentMatter() {
  if (matterSelect && matterSelect.value) return matterSelect.value;
  const active = document.querySelector(".case-card.active") || caseCards[0];
  return active ? active.dataset.matter : null;
}
function currentRole() {
  return roleSelect ? roleSelect.value : "pilot_user";
}
function activeCaseName() {
  const c = document.querySelector(".case-card.active") || caseCards[0];
  return c ? (c.dataset.name || c.dataset.matter) : "this case";
}

/* ---------- case selection (cards <-> hidden matter-select) ---------- */
function setActiveMatter(matterId) {
  const card = caseCards.find((node) => node.dataset.matter === matterId) || caseCards[0];
  if (!card) return;
  const matter = card.dataset.matter || matterId;
  if (matterSelect) matterSelect.value = matter;
  caseCards.forEach((node) => node.classList.toggle("active", node === card));
  if (caseName) caseName.textContent = card.dataset.name || matter;
  if (caseStatus) caseStatus.textContent = card.dataset.status || "Active";
  if (caseDocLabel) caseDocLabel.textContent = card.dataset.docLabel || "";

  filterCorpus(matter);
  closeDrawer();
  showPassagesView();
  loadThread(matter);
}

caseCards.forEach((card) => {
  card.addEventListener("click", () => setActiveMatter(card.dataset.matter || ""));
});
if (matterSelect) {
  matterSelect.addEventListener("change", () => setActiveMatter(matterSelect.value));
}

/* ---------- case search (filter the visible card list) ---------- */
if (caseSearch) {
  caseSearch.addEventListener("input", () => {
    const q = caseSearch.value.trim().toLowerCase();
    caseCards.forEach((card) => {
      const name = (card.dataset.name || "").toLowerCase();
      card.classList.toggle("hidden", q !== "" && !name.includes(q));
    });
  });
}

/* ---------- role hint ---------- */
if (roleSelect && hintRole) {
  roleSelect.addEventListener("change", () => {
    hintRole.textContent = currentRole();
    loadThread(currentMatter()); // history is role-scoped
  });
}

/* ---------- helpers ---------- */
function makeEmptyState(matterName) {
  const e = emptyStateTpl.cloneNode(true);
  const ec = e.querySelector("#empty-case");
  if (ec) ec.textContent = matterName || "this case";
  e.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => { questionInput.value = chip.dataset.q; autoGrow(); ask(chip.dataset.q); });
  });
  return e;
}
function clearEmptyState() {
  const e = document.getElementById("empty-state");
  if (e) e.remove();
}
function showError(message) {
  errorBanner.textContent = message;
  errorBanner.classList.remove("hidden");
}
function hideError() {
  errorBanner.textContent = "";
  errorBanner.classList.add("hidden");
}
function formatTime(iso) {
  const d = iso ? new Date(iso) : new Date();
  try {
    return d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  } catch (e) {
    return "";
  }
}

/* ---------- answer_text -> formatted DOM ----------
   Handles: \n\n paragraphs, **bold** (a fully-bold line becomes a subhead),
   "- " bullet lines, and [n] citation markers (clickable). */
function appendInline(parent, str, payload) {
  const re = /(\[\d+\]|\*\*[^*]+\*\*)/g;
  let last = 0, m;
  while ((m = re.exec(str)) !== null) {
    if (m.index > last) parent.appendChild(document.createTextNode(str.slice(last, m.index)));
    const tok = m[0];
    if (tok[0] === "[") {
      const n = parseInt(tok.slice(1, -1), 10);
      const sup = document.createElement("button");
      sup.type = "button";
      sup.className = "cite";
      sup.textContent = n;
      sup.addEventListener("click", () => openDrawer(payload, n));
      parent.appendChild(sup);
    } else {
      const strong = document.createElement("strong");
      strong.textContent = tok.slice(2, -2);
      parent.appendChild(strong);
    }
    last = m.index + tok.length;
  }
  if (last < str.length) parent.appendChild(document.createTextNode(str.slice(last)));
}

function renderAnswer(host, text, payload) {
  host.innerHTML = "";
  const paras = String(text || "").split(/\n{2,}/);
  paras.forEach((p) => {
    const trimmed = p.trim();
    if (!trimmed) return;
    const lines = trimmed.split("\n");
    const isSubhead = /^\*\*[^*]+\*\*:?$/.test(trimmed);
    const allBullets = lines.length > 0 && lines.every((l) => l.trim().startsWith("- "));

    if (isSubhead) {
      const d = document.createElement("div");
      d.className = "subhead";
      d.textContent = trimmed.replace(/\*\*/g, "").replace(/:$/, "");
      host.appendChild(d);
    } else if (allBullets) {
      lines.forEach((l) => {
        const para = document.createElement("p");
        para.className = "ans bullet";
        const dash = document.createElement("span");
        dash.className = "dash";
        dash.textContent = "—  ";
        para.appendChild(dash);
        appendInline(para, l.trim().slice(2), payload);
        host.appendChild(para);
      });
    } else {
      const para = document.createElement("p");
      para.className = "ans";
      appendInline(para, p, payload);
      host.appendChild(para);
    }
  });
}

/* ---------- assessment callout (abstention / grounded-but-unresolved) ---------- */
function deriveAssessment(payload) {
  if (payload.abstained) {
    return {
      kind: "warn", label: "Why no answer",
      text: "No approved passage cleared the grounding threshold, so the assistant declined rather than infer an answer.",
    };
  }
  const t = (payload.answer_text || "").toLowerCase();
  const unresolved = /insufficient evidence|does not (identify|resolve|answer)|cannot identify|remains unclear|not enough information/.test(t);
  if (unresolved) {
    return {
      kind: "ok", label: "Assessment",
      text: "The assistant reaches a defensible conclusion grounded in the record rather than inferring beyond it.",
    };
  }
  return null;
}

/* ---------- evidence drawer ---------- */
function citedMarkerFor(payload, chunkId) {
  const hit = (payload.citations || []).find((c) => c.chunk_id === chunkId);
  return hit ? hit.marker : null;
}

function buildDrawerPassages(payload) {
  drawerPassages.innerHTML = "";
  const cards = (payload && payload.debug && payload.debug.evidence_cards) || [];
  if (!cards.length) {
    const empty = document.createElement("div");
    empty.className = "drawer-empty";
    empty.innerHTML =
      '<div class="drawer-empty-title">No retrieved passages</div>' +
      "<p>Open a cited answer to inspect the passages that grounded it, or browse the approved corpus below.</p>";
    drawerPassages.appendChild(empty);
    return;
  }
  cards.forEach((card, i) => {
    const marker = citedMarkerFor(payload, card.chunk_id);
    const cited = marker !== null;
    const idx = cited ? marker : i + 1;

    const node = evidenceCardTemplate.content.cloneNode(true);
    const wrap = node.querySelector(".ev-card");
    if (cited && marker === activeMarker) {
      wrap.classList.add("active");
      node.querySelector("[data-linked]").textContent = "Linked to citation [" + marker + "]";
    }
    const index = node.querySelector("[data-index]");
    index.textContent = idx;
    index.classList.add(cited ? "cited" : "uncited");

    const status = node.querySelector("[data-status]");
    status.textContent = cited ? "Cited" : "Retrieved · not cited";
    status.classList.add(cited ? "cited" : "uncited");

    node.querySelector("[data-doc]").textContent = card.doc_title || card.display_text || "";
    node.querySelector("[data-page]").textContent = [card.section_title, card.display_text].filter(Boolean).join(" · ");
    node.querySelector("[data-preview]").textContent = card.preview || "";

    const tagsHost = node.querySelector("[data-tags]");
    (card.tags || []).forEach((t) => {
      const tag = document.createElement("span");
      tag.className = "ev-tag";
      tag.textContent = t;
      tagsHost.appendChild(tag);
    });
    drawerPassages.appendChild(node);
  });
}

function showDrawer() {
  drawer.classList.add("open");
  scrim.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
  evidenceHandle.classList.add("hidden");
}

function showPassagesView() {
  if (sourceView) sourceView.classList.add("hidden");
  if (drawerMain) drawerMain.classList.remove("hidden");
}

function openDrawer(payload, marker) {
  if (payload) focusPayload = payload;
  if (!focusPayload) return;
  activeMarker = typeof marker === "number" ? marker : null;
  showPassagesView();

  drawerQuestion.textContent = focusPayload._question || "";
  const n = (focusPayload.debug && focusPayload.debug.evidence_cards ? focusPayload.debug.evidence_cards.length : 0);
  drawerMeta.textContent = n + " passage" + (n === 1 ? "" : "s") + " · top-k retrieval · hybrid search";

  buildDrawerPassages(focusPayload);
  showDrawer();
}

function openCorpusOnly() {
  showPassagesView();
  if (focusPayload) { openDrawer(focusPayload, null); return; }
  drawerQuestion.textContent = "";
  drawerMeta.textContent = "Approved corpus for this case";
  buildDrawerPassages(null);
  showDrawer();
}

function closeDrawer() {
  drawer.classList.remove("open");
  scrim.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
  if (focusPayload) evidenceHandle.classList.remove("hidden");
}

drawerClose.addEventListener("click", closeDrawer);
scrim.addEventListener("click", closeDrawer);
evidenceHandle.addEventListener("click", () => openDrawer(focusPayload, null));
if (openCorpusBtn) openCorpusBtn.addEventListener("click", openCorpusOnly);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

/* ---------- SP2: corpus filtering + source viewer ---------- */
function filterCorpus(matter) {
  let count = 0;
  corpusItems.forEach((item) => {
    const show = item.dataset.matter === matter;
    item.classList.toggle("hidden", !show);
    if (show) count++;
  });
  if (corpusCount) corpusCount.textContent = count;
}

async function openSource(matter, docId) {
  try {
    const url = "/documents/" + encodeURIComponent(matter) + "/" + encodeURIComponent(docId) +
      "?role=" + encodeURIComponent(currentRole());
    const r = await fetch(url);
    if (!r.ok) { showError("Could not open that document."); return; }
    const doc = await r.json();
    sourceTitle.textContent = doc.title || docId;
    sourceMeta.textContent = [doc.type, doc.date].filter(Boolean).join(" · ");
    sourceText.textContent = doc.text || "";
    if (drawerMain) drawerMain.classList.add("hidden");
    if (sourceView) sourceView.classList.remove("hidden");
    showDrawer();
  } catch (e) {
    showError("Could not open that document: " + e.message);
  }
}

corpusItems.forEach((item) => {
  item.addEventListener("click", () => openSource(item.dataset.matter, item.dataset.docId));
});
if (sourceBack) sourceBack.addEventListener("click", showPassagesView);

/* ---------- turn rendering ---------- */
function appendPending(question) {
  const node = pendingTemplate.content.cloneNode(true);
  const q = node.querySelector("[data-question]");
  if (q) q.textContent = question;
  const article = node.querySelector(".turn");
  transcript.appendChild(node);
  article.scrollIntoView({ behavior: "smooth", block: "end" });
  return article;
}

function fillTurn(article, question, payload) {
  payload._question = question;
  const node = turnTemplate.content.cloneNode(true);
  const turn = node.querySelector(".turn");
  turn._payload = payload;
  if (payload._history) turn.classList.add("history");

  node.querySelector("[data-question]").textContent = question;

  const status = node.querySelector("[data-status]");
  if (payload.abstained) {
    status.className = "status-pill warn";
    status.textContent = "Insufficient evidence";
  } else {
    status.className = "status-pill ok";
    status.textContent = "Grounded answer";
  }
  if (payload._history) {
    const tag = document.createElement("span");
    tag.className = "history-tag";
    tag.textContent = "History";
    status.parentNode.appendChild(tag);
  }
  node.querySelector("[data-time]").textContent = formatTime(payload.debug && payload.debug.request_timestamp);

  renderAnswer(node.querySelector("[data-answer]"), payload.answer_text, payload);

  const assess = deriveAssessment(payload);
  const assessWrap = node.querySelector("[data-assessment]");
  if (assess) {
    assessWrap.classList.remove("hidden");
    assessWrap.classList.add(assess.kind);
    node.querySelector("[data-assessment-label]").textContent = assess.label;
    node.querySelector("[data-assessment-text]").textContent = assess.text;
  }

  const citations = payload.citations || [];
  if (citations.length) {
    node.querySelector("[data-sources-wrap]").classList.remove("hidden");
    const row = node.querySelector("[data-sources]");
    citations.forEach((c) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "source-chip";
      const marker = document.createElement("span");
      marker.className = "marker";
      marker.textContent = c.marker;
      chip.appendChild(marker);
      chip.appendChild(document.createTextNode(c.display_text || ""));
      chip.addEventListener("click", () => openDrawer(payload, c.marker));
      row.appendChild(chip);
    });
  }

  const evCount = (payload.debug && payload.debug.evidence_cards ? payload.debug.evidence_cards.length : 0);
  node.querySelector("[data-runline]").textContent =
    "Independent retrieval · " + evCount + " passage" + (evCount === 1 ? "" : "s");
  node.querySelector("[data-evidence-btn]").addEventListener("click", () => openDrawer(payload, null));

  article.replaceWith(node);
}

/* ---------- SP4: per-case thread history ---------- */
function renderThread(turns, matterName) {
  transcript.innerHTML = "";
  if (!turns || !turns.length) {
    transcript.appendChild(makeEmptyState(matterName));
    focusPayload = null;
    evidenceHandle.classList.add("hidden");
    return;
  }
  turns.forEach((t) => {
    const payload = {
      answer_text: t.answer,
      abstained: t.abstained,
      citations: t.citations || [],
      evidence_chunk_ids: [],
      debug: { request_timestamp: t.timestamp, evidence_cards: [] },
      _question: t.question,
      _history: true,
    };
    const placeholder = document.createElement("article");
    transcript.appendChild(placeholder);
    fillTurn(placeholder, t.question, payload);
  });
  evidenceHandle.classList.add("hidden");
  focusPayload = null;
}

async function loadThread(matter) {
  if (!matter) return;
  const name = activeCaseName();
  const token = ++threadToken;
  try {
    const url = "/threads/" + encodeURIComponent(matter) + "?role=" + encodeURIComponent(currentRole()) + "&limit=20";
    const r = await fetch(url);
    if (token !== threadToken) return; // superseded by a newer switch
    if (!r.ok) { renderThread([], name); return; }
    const data = await r.json();
    if (token !== threadToken) return;
    renderThread(data.turns || [], name);
  } catch (e) {
    if (token === threadToken) renderThread([], name);
  }
}

/* ---------- submit ---------- */
async function ask(question) {
  const q = (question || "").trim();
  if (!q) { showError("Enter a question before asking the assistant."); return; }
  const matter = currentMatter();
  if (!matter) { showError("Select a case first."); return; }
  hideError();
  clearEmptyState();

  const article = appendPending(q);
  submitButton.disabled = true;

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, matter: matter, role: currentRole() }),
    });
    const payload = await response.json();
    if (!response.ok) {
      article.remove();
      showError(payload.detail || "Assistant request failed.");
      return;
    }
    fillTurn(article, q, payload);
    focusPayload = payload;
    payload._question = q;
    evidenceHandle.classList.remove("hidden");
    questionInput.value = "";
    autoGrow();
  } catch (err) {
    article.remove();
    showError("Unable to reach the assistant: " + err.message);
  } finally {
    submitButton.disabled = false;
    questionInput.focus();
  }
}

form.addEventListener("submit", (e) => { e.preventDefault(); ask(questionInput.value); });

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    questionInput.value = chip.dataset.q;
    autoGrow();
    ask(chip.dataset.q);
  });
});

/* textarea auto-grow + Enter-to-send (Shift+Enter for newline) */
function autoGrow() {
  questionInput.style.height = "auto";
  questionInput.style.height = Math.min(questionInput.scrollHeight, 120) + "px";
}
questionInput.addEventListener("input", autoGrow);
questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(questionInput.value); }
});

/* ---------- SP5: appearance settings (persisted in localStorage) ---------- */
const setPalette = document.getElementById("set-palette");
const setAnswer = document.getElementById("set-answer");
const setDensity = document.getElementById("set-density");
const settingsBtn = document.getElementById("settings-btn");
const settingsMenu = document.getElementById("settings-menu");
const SETTINGS_KEY = "lc-settings";
const DEFAULT_SETTINGS = { palette: "indigo", answer: "serif", density: "detailed" };

function loadSettings() {
  try {
    return Object.assign({}, DEFAULT_SETTINGS, JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}"));
  } catch (e) {
    return Object.assign({}, DEFAULT_SETTINGS);
  }
}
function applySettings(s) {
  document.body.setAttribute("data-theme", s.palette);
  document.body.classList.toggle("answer-clean", s.answer === "clean");
  const sb = document.querySelector(".sidebar");
  if (sb) sb.classList.toggle("compact", s.density === "compact");
  if (setPalette) setPalette.value = s.palette;
  if (setAnswer) setAnswer.value = s.answer;
  if (setDensity) setDensity.value = s.density;
}
let settings = loadSettings();
applySettings(settings);

function updateSetting(key, value) {
  settings[key] = value;
  try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); } catch (e) { /* ignore */ }
  applySettings(settings);
}
if (setPalette) setPalette.addEventListener("change", () => updateSetting("palette", setPalette.value));
if (setAnswer) setAnswer.addEventListener("change", () => updateSetting("answer", setAnswer.value));
if (setDensity) setDensity.addEventListener("change", () => updateSetting("density", setDensity.value));
if (settingsBtn && settingsMenu) {
  settingsBtn.addEventListener("click", (e) => { e.stopPropagation(); settingsMenu.classList.toggle("hidden"); });
  document.addEventListener("click", (e) => {
    if (!settingsMenu.contains(e.target) && e.target !== settingsBtn) settingsMenu.classList.add("hidden");
  });
}

/* ---------- init ---------- */
if (caseCards.length) {
  const initial = (matterSelect && matterSelect.value) || caseCards[0].dataset.matter || "";
  setActiveMatter(initial);
}
