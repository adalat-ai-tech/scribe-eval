/* SCRIBE live demo.
 *
 * Boot: showcases render instantly from CI-baked JSON; Pyodide then loads
 * the real scribe wheel (with a pure-Python Levenshtein shim) and the
 * free-text inputs come alive. All metric logic stays in Python — the
 * functions below only render the dict returned by demo_api.evaluate_single.
 *
 * Evaluation runs on the main thread: post-warm-up calls on sentence-length
 * input are <100 ms. If batch upload ever lands, move Pyodide into a Web
 * Worker and add progress reporting.
 */

const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/";

const el = (id) => document.getElementById(id);
const statusPill = el("status-pill");
const refInput = el("ref-input");
const hypInput = el("hyp-input");
const domainSelect = el("domain-select");
const normalizeToggle = el("normalize-toggle");
const sandhiToggle = el("sandhi-toggle");
const showcaseNote = el("showcase-note");

let showcases = [];
let bakedResults = {};
let evaluateJson = null; // PyProxy of demo_api.evaluate_single_json once ready
let debounceTimer = null;

/* ---------- rendering (pure DOM, zero metric logic) ---------- */

const pct = (frac) => `${(frac * 100).toFixed(2)}%`;

function renderTiles(tiles) {
  el("tile-wer").textContent = pct(tiles.wer_scribe);
  el("tile-cer").textContent = pct(tiles.cer_scribe);
  el("tile-acc").textContent = pct(tiles.accuracy);
}

function renderChips(chips, tiles) {
  el("chips-caption").textContent =
    `${chips.join("  +  ")}  =  ${pct(tiles.wer_scribe)}   ·   ${tiles.sandhi_hits} sandhi matches`;
}

const STATUS_MAP = {
  correct: "s-correct",
  substitution: "s-sub",
  insertion: "s-ins",
  deletion: "s-del",
  sandhi: "s-merge",
};

function renderAlignment(rows) {
  const tr = el("alignment-row");
  tr.replaceChildren();
  for (const item of rows) {
    const td = document.createElement("td");
    td.className = `token-cell ${STATUS_MAP[item.error_type] || "s-correct"} t-${item.token_type}`;
    const top = document.createElement("div");
    top.className = "top-text";
    const bot = document.createElement("div");
    bot.className = "bot-text";
    const tag = document.createElement("div");
    tag.className = "tag-label";
    // "**" marks a gap cell; textContent everywhere keeps user input inert.
    if (item.ref_text === "**") top.innerHTML = "&nbsp;";
    else top.textContent = item.ref_text;
    if (item.hyp_text === "**") bot.innerHTML = "&nbsp;";
    else bot.textContent = item.hyp_text;
    tag.textContent = item.token_type;
    td.append(top, bot, tag);
    tr.append(td);
  }
}

const CONTRIBUTION_COLUMNS = [
  "Category", "Ref Tokens", "Match", "Accuracy", "Sub", "Del", "Ins",
  "Errors", "Error Rate", "Impact on Total",
];

function renderContribution(rows) {
  const table = el("contribution-table");
  table.replaceChildren();
  const cols = CONTRIBUTION_COLUMNS.filter((c) => rows.length && c in rows[0]);
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const c of cols) {
    const th = document.createElement("th");
    th.textContent = c;
    headRow.append(th);
  }
  thead.append(headRow);
  const tbody = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    if (row.Category === "TOTAL") tr.className = "total-row";
    for (const c of cols) {
      const td = document.createElement("td");
      td.textContent = row[c];
      tr.append(td);
    }
    tbody.append(tr);
  }
  table.append(thead, tbody);
}

function renderResult(result) {
  renderTiles(result.tiles);
  renderChips(result.chips, result.tiles);
  renderAlignment(result.alignment);
  renderContribution(result.contribution);
  el("results").hidden = false;
}

/* ---------- status pill ---------- */

function setEngineStatus(state, detail) {
  statusPill.className = `status-pill ${state}`;
  if (state === "loading") {
    statusPill.textContent = "Loading Python engine · runs entirely in your browser";
  } else if (state === "ready") {
    statusPill.textContent = "Live — running the published scribe-eval wheel in your browser";
  } else {
    statusPill.textContent =
      "Live engine unavailable — showcase results below were precomputed with the same library";
    if (detail) console.error("SCRIBE demo engine failed:", detail);
  }
}

/* ---------- evaluation flow ---------- */

function currentParams() {
  return {
    ref: refInput.value,
    hyp: hypInput.value,
    domain: domainSelect.value,
    normalize: normalizeToggle.checked,
    useSandhi: sandhiToggle.checked,
  };
}

function evaluateLive() {
  if (!evaluateJson) return;
  const p = currentParams();
  if (!p.ref.trim() && !p.hyp.trim()) return;
  try {
    const result = JSON.parse(evaluateJson(p.ref, p.hyp, p.domain, p.normalize, p.useSandhi));
    renderResult(result);
  } catch (err) {
    console.error("evaluation failed:", err);
  }
}

function scheduleEvaluate() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(evaluateLive, 250);
  clearActiveChip();
}

function clearActiveChip() {
  for (const chip of document.querySelectorAll(".showcase-chip.active")) {
    chip.classList.remove("active");
  }
  showcaseNote.textContent = "";
}

function loadShowcase(id) {
  const sc = showcases.find((s) => s.id === id);
  if (!sc) return;
  refInput.value = sc.ref;
  hypInput.value = sc.hyp;
  domainSelect.value = sc.domain;
  normalizeToggle.checked = sc.normalize;
  sandhiToggle.checked = sc.use_sandhi;
  clearActiveChip();
  const chip = document.querySelector(`.showcase-chip[data-id="${id}"]`);
  if (chip) {
    chip.classList.add("active");
    // Scroll only the strip. scrollIntoView() would also scroll the document
    // and cancel the #demo anchor jump the "Try it" links rely on.
    const row = chip.parentElement;
    row.scrollTo({
      left: chip.offsetLeft - (row.clientWidth - chip.offsetWidth) / 2,
      behavior: "smooth",
    });
  }
  showcaseNote.textContent = sc.note || "";
  if (evaluateJson) {
    evaluateLive();
  } else if (bakedResults[id]) {
    renderResult(bakedResults[id]);
  }
}

/* ---------- boot ---------- */

async function fetchJson(path) {
  const resp = await fetch(path);
  if (!resp.ok) throw new Error(`${path}: HTTP ${resp.status}`);
  return resp.json();
}

async function initShowcases() {
  showcases = await fetchJson("data/showcases.json");
  try {
    bakedResults = await fetchJson("data/showcase_results.json");
  } catch {
    bakedResults = {}; // page still works; results appear once the engine is live
  }
  const row = el("showcase-row");
  for (const sc of showcases) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "showcase-chip";
    chip.dataset.id = sc.id;
    chip.textContent = sc.label;
    chip.addEventListener("click", () => loadShowcase(sc.id));
    row.append(chip);
  }
  for (const link of document.querySelectorAll("[data-showcase]")) {
    link.addEventListener("click", () => loadShowcase(link.dataset.showcase));
  }
  loadShowcase(showcases[0].id);
}

async function bootPyodide() {
  setEngineStatus("loading");
  await new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = `${PYODIDE_CDN}pyodide.js`;
    s.onload = resolve;
    s.onerror = () => reject(new Error("Pyodide CDN unreachable"));
    document.head.append(s);
  });
  const pyodide = await loadPyodide({ indexURL: PYODIDE_CDN });
  await pyodide.loadPackage("micropip");

  // Register the pure-Python Levenshtein shim before scribe imports it.
  const shimSrc = await (await fetch("py/levenshtein_shim.py")).text();
  pyodide.runPython(`
import importlib.util, sys
_spec = importlib.util.spec_from_loader("Levenshtein", loader=None)
_mod = importlib.util.module_from_spec(_spec)
exec(${JSON.stringify(shimSrc)}, _mod.__dict__)
sys.modules["Levenshtein"] = _mod
`);

  const { wheel } = await fetchJson("wheels/manifest.json");
  const micropip = pyodide.pyimport("micropip");
  // callKwargs: micropip.install(url, deps=False) — a plain JS object would
  // bind positionally, and deps=True would try to resolve levenshtein on PyPI.
  await micropip.install.callKwargs(new URL(`wheels/${wheel}`, location.href).href, {
    deps: false,
  });

  const apiSrc = await (await fetch("py/demo_api.py")).text();
  pyodide.runPython(apiSrc);
  evaluateJson = pyodide.globals.get("evaluate_single_json");

  // Warm-up: touches the bundled legal config so the first user call is instant.
  JSON.parse(evaluateJson("warm up", "warm up", "legal", true, true));

  for (const input of [refInput, hypInput, domainSelect, normalizeToggle, sandhiToggle]) {
    input.disabled = false;
  }
  setEngineStatus("ready");
  evaluateLive(); // re-run whatever is in the boxes, live this time
}

document.addEventListener("DOMContentLoaded", () => {
  initShowcases().catch((err) => console.error("showcase init failed:", err));
  refInput.addEventListener("input", scheduleEvaluate);
  hypInput.addEventListener("input", scheduleEvaluate);
  for (const control of [domainSelect, normalizeToggle, sandhiToggle]) {
    control.addEventListener("change", () => {
      clearTimeout(debounceTimer);
      evaluateLive();
    });
  }
  bootPyodide().catch((err) => setEngineStatus("failed", err));
});
