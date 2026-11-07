"""Generate a self-contained HTML coding UI for the 60-item human coding sheet.

Reads `mini_study/coding_sheet_for_human.csv`, embeds the items as a JSON
array inside an HTML page with:
  - keyboard shortcuts (1-5 = label, q/w/e = confidence, j/k = nav, /=search)
  - filters (anchor, language, country, protest flag, status, label)
  - localStorage autosave (per coder name) — survives reloads
  - export to CSV (downloads the filled coding sheet)
  - import progress (paste previous JSON to resume)
  - collapsible codebook reference panel
  - sidebar item list with status indicators

Output: mini_study/coding_ui.html — open directly in a browser, no server needed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
CSV = REPO / "mini_study" / "coding_sheet_for_human.csv"
CODEBOOK = REPO / "mini_study" / "framing_codebook.md"
OUT = REPO / "mini_study" / "coding_ui.html"


LABELS = [
    {"key": "prokremlowski",         "pl": "prokremlowski",         "en": "pro-Kremlin",         "color": "#c0392b", "kb": "1"},
    {"key": "antywojenny",            "pl": "antywojenny",            "en": "antiwar",             "color": "#27ae60", "kb": "2"},
    {"key": "prozachodni",            "pl": "prozachodni",            "en": "pro-Western",         "color": "#2980b9", "kb": "3"},
    {"key": "bialorusko-narodowy",    "pl": "białorusko-narodowy",    "en": "Belarusian-national", "color": "#8e44ad", "kb": "4"},
    {"key": "neutralny-informacyjny", "pl": "neutralny-informacyjny", "en": "neutral-info",        "color": "#7f8c8d", "kb": "5"},
]

CODEBOOK_SHORT = """\
**prokremlowski** — adopts Russian state framing; «СВО» without distancing quotes; delegitimises UA/BY opposition.
**antywojenny** — explicitly opposes the war or state repression; protest slogans, voices of detained/exiled.
**prozachodni** — Western institutions (EU/NATO/US) as normative reference; DW/Reuters/BBC explainer format.
**białorusko-narodowy** — Belarusian national identity (БЧБ, Tikhanouskaya, Belsat, ВКЛ); distinct from Russian.
**neutralny-informacyjny** — news/briefing format without overt stance. *Default when in doubt.*

Boundary tips:
- `prokremlowski` vs `neutralny` → only mark proKremlin if explicit evaluative markers («так называемая оппозиция», «нацистский режим»).
- `białorusko-narodowy` vs `prozachodni` → Belsat in BE → BN; DW in EN about Belarus → PZ.
- `antywojenny` vs `prozachodni` → Russian opposition channels (Navalny, Dozhd) → antywojenny (primary frame is *anti-state*, not *pro-West*).
"""


def load_items():
    df = pd.read_csv(CSV, dtype=str, keep_default_na=False, na_values=[""])
    items = []
    for i, r in df.iterrows():
        items.append({
            "idx": int(i),
            "yt_id": r["YT_ID"],
            "anchor": r["anchor"],
            "rank": int(float(r["rank"])) if r.get("rank") else None,
            "similarity": round(float(r["similarity"]), 3) if r.get("similarity") else None,
            "language_norm": r.get("language_norm", ""),
            "country_combo": r.get("country_combo", ""),
            "protest_anywhere": str(r.get("protest_anywhere", "")).lower() == "true",
            "title": r.get("TITLE", "") or "",
            "description": r.get("DESCRIPTION", "") or "",
            "feed_text": r.get("feed_text", "") or "",
            "dur_sec": int(float(r["dur_sec"])) if r.get("dur_sec") and r["dur_sec"] not in ("", "nan") else None,
            "published_at": r.get("PUBLISHED_AT", "") or "",
        })
    return items


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Framing coding — AGH mini-study</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root {
    --bg:#1a1a1a; --panel:#242424; --panel-2:#2d2d2d; --border:#3a3a3a;
    --fg:#e8e8e8; --muted:#9a9a9a; --accent:#f5b342; --warn:#e67e22;
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--fg);
         font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,system-ui,sans-serif;
         font-size:14px; line-height:1.5; }
  header { padding:10px 16px; background:var(--panel); border-bottom:1px solid var(--border);
           display:flex; align-items:center; gap:16px; flex-wrap:wrap; }
  header h1 { margin:0; font-size:15px; font-weight:600; }
  header .progress { font-family:'SF Mono',monospace; color:var(--accent); }
  header .coder { display:flex; align-items:center; gap:6px; }
  header .coder input { background:var(--panel-2); color:var(--fg); border:1px solid var(--border);
                        padding:3px 6px; border-radius:3px; font-size:13px; width:120px; }
  header button { background:var(--panel-2); color:var(--fg); border:1px solid var(--border);
                  padding:5px 11px; border-radius:4px; cursor:pointer; font-size:13px; }
  header button:hover { background:#3a3a3a; }
  header button.primary { background:var(--accent); color:#1a1a1a; border-color:var(--accent); font-weight:600; }
  header button.warn { background:var(--warn); color:#1a1a1a; border-color:var(--warn); }

  .main { display:grid; grid-template-columns: 280px 1fr 320px; height: calc(100vh - 49px); }

  /* Sidebar — item list */
  .sidebar { background:var(--panel); border-right:1px solid var(--border); overflow-y:auto;
             display:flex; flex-direction:column; }
  .filters { padding:10px; border-bottom:1px solid var(--border); display:flex; flex-direction:column; gap:6px; }
  .filters label { font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:0.5px; }
  .filters select, .filters input[type=text] { background:var(--panel-2); color:var(--fg); border:1px solid var(--border);
            padding:4px 6px; border-radius:3px; font-size:13px; width:100%; }
  .filters .row { display:flex; gap:6px; }
  .filters .row > * { flex:1; }
  .filter-stats { font-size:11px; color:var(--muted); padding:2px 0; }
  .item-list { overflow-y:auto; flex:1; }
  .item-row { padding:8px 10px; border-bottom:1px solid var(--border); cursor:pointer;
              display:grid; grid-template-columns: 16px 1fr 24px; gap:6px; align-items:center; }
  .item-row:hover { background:var(--panel-2); }
  .item-row.active { background:#3a3a3a; border-left:3px solid var(--accent); padding-left:7px; }
  .item-row .status { font-size:13px; }
  .item-row .title-prev { font-size:12px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
                          color:var(--fg); }
  .item-row .meta-mini { font-size:10px; color:var(--muted); }
  .item-row .swatch { width:14px; height:14px; border-radius:3px; margin-left:auto; }

  /* Main coding area */
  .coding { padding:16px 22px; overflow-y:auto; }
  .meta-bar { display:flex; gap:14px; font-size:11px; color:var(--muted);
              text-transform:uppercase; letter-spacing:0.6px; margin-bottom:8px; }
  .meta-bar .tag { padding:3px 8px; border-radius:11px; background:var(--panel-2); }
  .meta-bar .tag.protest { background:#5e3c0a; color:#f5b342; }
  .title { font-size:18px; font-weight:600; line-height:1.35; margin:6px 0 12px 0; }
  .description { background:var(--panel); padding:12px 14px; border-radius:6px;
                 white-space:pre-wrap; max-height:380px; overflow-y:auto; border:1px solid var(--border);
                 font-size:13.5px; line-height:1.55; }
  .desc-expand { color:var(--accent); cursor:pointer; font-size:12px; margin-top:6px; }
  .yt-link { color:var(--accent); text-decoration:none; }
  .yt-link:hover { text-decoration:underline; }

  /* Label buttons */
  .label-group { margin-top:18px; }
  .label-group h3 { margin:0 0 8px 0; font-size:11px; color:var(--muted);
                    text-transform:uppercase; letter-spacing:0.6px; }
  .labels { display:grid; grid-template-columns:repeat(5,1fr); gap:8px; }
  .label-btn { background:var(--panel-2); color:var(--fg); border:2px solid var(--border);
               padding:14px 10px; border-radius:6px; cursor:pointer; text-align:left;
               transition:all 0.1s; font-size:13px; }
  .label-btn:hover { border-color:var(--accent); }
  .label-btn .kb-hint { float:right; opacity:0.7; font-family:'SF Mono',monospace;
                        background:var(--border); padding:1px 5px; border-radius:3px; font-size:11px; }
  .label-btn .pl-name { display:block; font-weight:600; margin-bottom:2px; }
  .label-btn .en-name { display:block; font-size:11px; color:var(--muted); }
  .label-btn.selected { border-width:2px; }
  .label-btn.selected .pl-name { color:#fff; }

  .conf-group { display:flex; gap:8px; margin-top:14px; align-items:center; }
  .conf-group h3 { margin:0; font-size:11px; color:var(--muted);
                   text-transform:uppercase; letter-spacing:0.6px; min-width:90px; }
  .conf-btn { background:var(--panel-2); color:var(--fg); border:2px solid var(--border);
              padding:6px 14px; border-radius:5px; cursor:pointer; font-size:13px; }
  .conf-btn:hover { border-color:var(--accent); }
  .conf-btn.selected { background:var(--accent); color:#1a1a1a; border-color:var(--accent); font-weight:600; }

  textarea.notes { width:100%; min-height:70px; background:var(--panel); color:var(--fg);
                   border:1px solid var(--border); border-radius:5px; padding:8px 10px; font-family:inherit;
                   font-size:13px; resize:vertical; margin-top:14px; }

  .nav-row { display:flex; gap:8px; margin-top:18px; }
  .nav-row button { flex:1; }

  /* Right panel — codebook + stats */
  .right { background:var(--panel); border-left:1px solid var(--border); overflow-y:auto; padding:14px 16px; }
  .right h3 { margin:0 0 10px 0; font-size:11px; color:var(--muted);
              text-transform:uppercase; letter-spacing:0.6px; }
  .codebook { font-size:12.5px; line-height:1.55; white-space:pre-wrap;
              background:var(--panel-2); padding:10px 12px; border-radius:5px; border:1px solid var(--border); }
  .codebook strong { color:var(--accent); }
  .stats-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px 16px; margin-top:14px;
                font-size:12.5px; }
  .stats-grid .stat-row { display:flex; justify-content:space-between;
                          padding:4px 0; border-bottom:1px dotted var(--border); }
  .stats-grid .stat-row .name { color:var(--muted); }
  .stats-grid .swatch-row { display:flex; align-items:center; gap:6px; }
  .stats-grid .mini-swatch { width:10px; height:10px; border-radius:2px; }
  .kb-help { margin-top:14px; font-size:11.5px; color:var(--muted); line-height:1.7; }
  .kb-help code { background:var(--panel-2); padding:1px 6px; border-radius:3px;
                  font-family:'SF Mono',monospace; color:var(--fg); }
  details summary { cursor:pointer; color:var(--accent); font-size:12px; margin-top:14px; }

  /* Modal */
  .modal-backdrop { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:none;
                    align-items:center; justify-content:center; z-index:99; }
  .modal-backdrop.show { display:flex; }
  .modal { background:var(--panel); border:1px solid var(--border); border-radius:8px;
           padding:22px 26px; max-width:560px; width:90%; }
  .modal h2 { margin:0 0 14px 0; font-size:16px; }
  .modal textarea { width:100%; height:200px; font-family:'SF Mono',monospace; font-size:12px;
                    background:var(--panel-2); color:var(--fg); border:1px solid var(--border);
                    border-radius:4px; padding:8px; }
  .modal .modal-buttons { display:flex; gap:10px; justify-content:flex-end; margin-top:14px; }
</style>
</head>
<body>
<header>
  <h1>🎯 Framing coding — AGH mini-study</h1>
  <span class="progress" id="progress">0 / 0</span>
  <span class="coder">coder: <input type="text" id="coder-name" value="sulzhytski"></span>
  <div style="margin-left:auto; display:flex; gap:6px;">
    <button id="btn-import" title="Paste previously exported JSON to resume">↥ Import</button>
    <button id="btn-export-csv" class="primary" title="Download CSV with your labels">↓ Export CSV</button>
    <button id="btn-export-json" title="Download JSON backup">↓ JSON</button>
    <button id="btn-reset" class="warn" title="Clear all labels (cannot undo)">⌫ Reset</button>
  </div>
</header>

<div class="main">
  <!-- Sidebar -->
  <div class="sidebar">
    <div class="filters">
      <label>Filter — anchor</label>
      <select id="f-anchor"><option value="">(all)</option></select>
      <div class="row">
        <div>
          <label>language</label>
          <select id="f-lang"><option value="">(all)</option></select>
        </div>
        <div>
          <label>country</label>
          <select id="f-country"><option value="">(all)</option></select>
        </div>
      </div>
      <div class="row">
        <div>
          <label>protest</label>
          <select id="f-protest"><option value="">(all)</option><option value="true">yes</option><option value="false">no</option></select>
        </div>
        <div>
          <label>status</label>
          <select id="f-status">
            <option value="">(all)</option>
            <option value="uncoded">uncoded</option>
            <option value="coded">coded</option>
          </select>
        </div>
      </div>
      <label>label</label>
      <select id="f-label"><option value="">(all)</option></select>
      <label>search title / desc</label>
      <input type="text" id="f-search" placeholder="text…">
      <div class="filter-stats" id="filter-stats">— shown</div>
    </div>
    <div class="item-list" id="item-list"></div>
  </div>

  <!-- Main coding -->
  <div class="coding">
    <div class="meta-bar" id="meta-bar"></div>
    <div class="title" id="item-title">Pick an item from the sidebar</div>
    <div class="description" id="item-description"></div>
    <div class="desc-expand" id="desc-expand" style="display:none">Toggle full description</div>

    <div class="label-group">
      <h3>Framing label <span style="font-weight:normal;text-transform:none;color:var(--muted)">(or click in PL/EN labels)</span></h3>
      <div class="labels" id="labels"></div>
    </div>

    <div class="conf-group">
      <h3>Confidence</h3>
      <button class="conf-btn" data-conf="1">1 — low <span style="opacity:0.6">[q]</span></button>
      <button class="conf-btn" data-conf="2">2 — medium <span style="opacity:0.6">[w]</span></button>
      <button class="conf-btn" data-conf="3">3 — high <span style="opacity:0.6">[e]</span></button>
    </div>

    <textarea class="notes" id="notes" placeholder="Coding notes — ambiguities, edge cases, why this label vs adjacent ones…"></textarea>

    <div class="nav-row">
      <button id="btn-prev" title="Previous (←/j)">← Prev</button>
      <button id="btn-next" class="primary" title="Next (→/k)">Next →</button>
      <button id="btn-next-uncoded" title="Jump to next uncoded item (Enter)">⇥ Next uncoded</button>
      <button id="btn-skip">Skip</button>
    </div>

    <div style="margin-top:16px; font-size:11px; color:var(--muted)">
      Item ID: <span id="item-id-display" style="font-family:'SF Mono',monospace; color:var(--fg)">—</span>
      &nbsp;|&nbsp; YouTube:
      <a class="yt-link" id="yt-link" target="_blank" rel="noopener">open ↗</a>
    </div>
  </div>

  <!-- Right panel -->
  <div class="right">
    <h3>Codebook quick-reference</h3>
    <div class="codebook" id="codebook"></div>

    <h3 style="margin-top:18px">Progress per label</h3>
    <div id="label-stats" class="stats-grid"></div>

    <h3 style="margin-top:18px">Per anchor</h3>
    <div id="anchor-stats" class="stats-grid"></div>

    <div class="kb-help">
      <strong>Keyboard:</strong><br>
      <code>1-5</code> assign label · <code>q/w/e</code> confidence (1/2/3)<br>
      <code>j</code>/<code>k</code> or <code>←</code>/<code>→</code> prev / next<br>
      <code>Enter</code> next uncoded · <code>/</code> focus search<br>
      <code>n</code> focus notes textarea
    </div>

    <details>
      <summary>About this coding sheet</summary>
      <div style="font-size:11.5px; color:var(--muted); margin-top:8px; line-height:1.6">
        Produced by <code>mini_study/build_coding_ui.py</code> from
        <code>coding_sheet_for_human.csv</code>. Labels saved to <code>localStorage</code>
        keyed by coder name. Use <strong>Export CSV</strong> to produce
        <code>coding_sheet_for_human_FILLED.csv</code> for the κ pipeline.
      </div>
    </details>
  </div>
</div>

<!-- Import modal -->
<div class="modal-backdrop" id="import-modal">
  <div class="modal">
    <h2>Import progress (paste JSON)</h2>
    <textarea id="import-text" placeholder='{"yt_id_1": {"label": "...", "confidence": "2", "notes": "..."}}'></textarea>
    <div class="modal-buttons">
      <button id="btn-import-cancel">Cancel</button>
      <button id="btn-import-apply" class="primary">Import</button>
    </div>
  </div>
</div>

<script>
const ITEMS = __ITEMS_PLACEHOLDER__;
const LABELS = __LABELS_PLACEHOLDER__;
const CODEBOOK_TEXT = __CODEBOOK_PLACEHOLDER__;

const state = {
  filtered: [],
  currentIdx: null,
  coder: 'sulzhytski',
  data: {}, // yt_id -> {label, confidence, notes}
};

function storageKey() { return 'agh_coding_' + state.coder; }

function loadState() {
  try {
    const raw = localStorage.getItem(storageKey());
    if (raw) state.data = JSON.parse(raw);
  } catch(e) { console.warn('localStorage load failed', e); }
}
function saveState() {
  try {
    localStorage.setItem(storageKey(), JSON.stringify(state.data));
  } catch(e) { console.warn('localStorage save failed', e); }
}

function escHtml(s) {
  return String(s||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function ytUrl(id) { return 'https://www.youtube.com/watch?v=' + id; }

function renderCodebook() {
  let html = escHtml(CODEBOOK_TEXT);
  // Bold the **terms**
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  document.getElementById('codebook').innerHTML = html;
}

function buildFilters() {
  const ANCHORS = [...new Set(ITEMS.map(x => x.anchor))].sort();
  const LANGS = [...new Set(ITEMS.map(x => x.language_norm))].sort();
  const COUNTRIES = [...new Set(ITEMS.map(x => x.country_combo))].sort();
  document.getElementById('f-anchor').innerHTML = '<option value="">(all)</option>' +
    ANCHORS.map(a => `<option value="${escHtml(a)}">${escHtml(a)}</option>`).join('');
  document.getElementById('f-lang').innerHTML = '<option value="">(all)</option>' +
    LANGS.map(a => `<option value="${escHtml(a)}">${escHtml(a)}</option>`).join('');
  document.getElementById('f-country').innerHTML = '<option value="">(all)</option>' +
    COUNTRIES.map(a => `<option value="${escHtml(a)}">${escHtml(a)}</option>`).join('');
  document.getElementById('f-label').innerHTML = '<option value="">(all)</option>' +
    '<option value="__none__">(uncoded)</option>' +
    LABELS.map(l => `<option value="${l.key}">${l.pl}</option>`).join('');
}

function applyFilters() {
  const fa = document.getElementById('f-anchor').value;
  const fl = document.getElementById('f-lang').value;
  const fc = document.getElementById('f-country').value;
  const fp = document.getElementById('f-protest').value;
  const fs = document.getElementById('f-status').value;
  const fL = document.getElementById('f-label').value;
  const search = document.getElementById('f-search').value.toLowerCase().trim();
  state.filtered = ITEMS.filter(it => {
    if (fa && it.anchor !== fa) return false;
    if (fl && it.language_norm !== fl) return false;
    if (fc && it.country_combo !== fc) return false;
    if (fp === 'true' && !it.protest_anywhere) return false;
    if (fp === 'false' && it.protest_anywhere) return false;
    const rec = state.data[it.yt_id] || {};
    if (fs === 'coded' && !rec.label) return false;
    if (fs === 'uncoded' && rec.label) return false;
    if (fL === '__none__' && rec.label) return false;
    if (fL && fL !== '__none__' && rec.label !== fL) return false;
    if (search && !(it.title.toLowerCase().includes(search) || it.description.toLowerCase().includes(search))) return false;
    return true;
  });
  renderItemList();
  document.getElementById('filter-stats').textContent = state.filtered.length + ' of ' + ITEMS.length + ' shown';
}

function renderItemList() {
  const el = document.getElementById('item-list');
  el.innerHTML = state.filtered.map(it => {
    const rec = state.data[it.yt_id] || {};
    const lbl = LABELS.find(l => l.key === rec.label);
    const status = rec.label ? '✓' : (rec.notes || rec.confidence ? '·' : '');
    const swatch = lbl ? `<span class="swatch" style="background:${lbl.color}" title="${lbl.pl}"></span>` : '<span></span>';
    const active = it.idx === state.currentIdx ? ' active' : '';
    const titlePreview = escHtml(it.title.substring(0, 80));
    const meta = `${it.anchor.replace('-protest','')} · ${it.language_norm}`;
    return `<div class="item-row${active}" data-idx="${it.idx}">
      <span class="status" style="color:${rec.label ? '#27ae60' : (status === '·' ? 'var(--muted)' : 'var(--border)')}">${status||'·'}</span>
      <span>
        <span class="title-prev">${titlePreview}</span>
        <span class="meta-mini">${escHtml(meta)}</span>
      </span>
      ${swatch}
    </div>`;
  }).join('');
  // Click handlers
  el.querySelectorAll('.item-row').forEach(row => {
    row.addEventListener('click', () => goTo(parseInt(row.dataset.idx)));
  });
  // Scroll active into view
  const active = el.querySelector('.active');
  if (active) active.scrollIntoView({block:'nearest'});
}

function buildLabelButtons() {
  document.getElementById('labels').innerHTML = LABELS.map(l => `
    <button class="label-btn" data-label="${l.key}" style="border-color:${l.color}">
      <span class="kb-hint">${l.kb}</span>
      <span class="pl-name" style="color:${l.color}">${l.pl}</span>
      <span class="en-name">${l.en}</span>
    </button>
  `).join('');
  document.querySelectorAll('.label-btn').forEach(b => {
    b.addEventListener('click', () => setLabel(b.dataset.label));
  });
}

function renderItem() {
  if (state.currentIdx === null || state.currentIdx >= ITEMS.length) {
    document.getElementById('item-title').textContent = 'Pick an item from the sidebar';
    document.getElementById('item-description').textContent = '';
    document.getElementById('meta-bar').innerHTML = '';
    return;
  }
  const it = ITEMS[state.currentIdx];
  const rec = state.data[it.yt_id] || {};
  document.getElementById('item-title').textContent = it.title || '(no title)';
  document.getElementById('item-description').textContent = it.description || '(no description)';
  document.getElementById('item-id-display').textContent = it.yt_id + '  (rank ' + it.rank + ', sim ' + it.similarity + ')';
  document.getElementById('yt-link').href = ytUrl(it.yt_id);
  const dur = it.dur_sec ? `${Math.floor(it.dur_sec/60)}:${String(it.dur_sec%60).padStart(2,'0')}` : '?';
  document.getElementById('meta-bar').innerHTML = `
    <span class="tag">${escHtml(it.anchor)}</span>
    <span class="tag">${escHtml(it.language_norm)}</span>
    <span class="tag">cc=${escHtml(it.country_combo)}</span>
    <span class="tag${it.protest_anywhere?' protest':''}">${it.protest_anywhere ? 'protest kw ✓' : 'newly-surfaced'}</span>
    <span class="tag">${dur}</span>
    <span class="tag">${escHtml(it.published_at||'?')}</span>
  `;
  // Highlight selected label
  document.querySelectorAll('.label-btn').forEach(b => {
    if (b.dataset.label === rec.label) {
      b.classList.add('selected');
      const lbl = LABELS.find(l => l.key === rec.label);
      b.style.background = lbl.color;
      b.style.color = '#fff';
    } else {
      b.classList.remove('selected');
      b.style.background = '';
      b.style.color = '';
    }
  });
  // Highlight confidence
  document.querySelectorAll('.conf-btn').forEach(b => {
    b.classList.toggle('selected', b.dataset.conf === String(rec.confidence||''));
  });
  document.getElementById('notes').value = rec.notes || '';
  updateProgress();
}

function goTo(idx) {
  state.currentIdx = idx;
  renderItem();
  renderItemList();
}

function nextItem(onlyUncoded=false) {
  const list = state.filtered.length ? state.filtered : ITEMS;
  const curPos = list.findIndex(it => it.idx === state.currentIdx);
  for (let i = curPos + 1; i < list.length; i++) {
    if (!onlyUncoded || !state.data[list[i].yt_id]?.label) { goTo(list[i].idx); return; }
  }
  // wrap if onlyUncoded
  if (onlyUncoded) {
    for (let i = 0; i < curPos; i++) {
      if (!state.data[list[i].yt_id]?.label) { goTo(list[i].idx); return; }
    }
  }
}
function prevItem() {
  const list = state.filtered.length ? state.filtered : ITEMS;
  const curPos = list.findIndex(it => it.idx === state.currentIdx);
  if (curPos > 0) goTo(list[curPos-1].idx);
}

function setLabel(key) {
  if (state.currentIdx === null) return;
  const it = ITEMS[state.currentIdx];
  if (!state.data[it.yt_id]) state.data[it.yt_id] = {};
  state.data[it.yt_id].label = key;
  saveState();
  renderItem();
  renderItemList();
  updateStats();
}
function setConfidence(c) {
  if (state.currentIdx === null) return;
  const it = ITEMS[state.currentIdx];
  if (!state.data[it.yt_id]) state.data[it.yt_id] = {};
  state.data[it.yt_id].confidence = c;
  saveState();
  renderItem();
}
function setNotes(t) {
  if (state.currentIdx === null) return;
  const it = ITEMS[state.currentIdx];
  if (!state.data[it.yt_id]) state.data[it.yt_id] = {};
  state.data[it.yt_id].notes = t;
  saveState();
}

function updateProgress() {
  const coded = ITEMS.filter(it => state.data[it.yt_id]?.label).length;
  document.getElementById('progress').textContent = coded + ' / ' + ITEMS.length + ' coded';
}
function updateStats() {
  const counts = {};
  LABELS.forEach(l => counts[l.key] = 0);
  counts['__uncoded'] = 0;
  ITEMS.forEach(it => {
    const lbl = state.data[it.yt_id]?.label;
    if (lbl && counts[lbl] !== undefined) counts[lbl]++;
    else counts['__uncoded']++;
  });
  const lblEl = document.getElementById('label-stats');
  lblEl.innerHTML = LABELS.map(l => `
    <div class="stat-row">
      <span class="swatch-row"><span class="mini-swatch" style="background:${l.color}"></span> ${l.pl}</span>
      <span>${counts[l.key]}</span>
    </div>
  `).join('') + `<div class="stat-row" style="grid-column:span 2"><span class="name">uncoded</span><span>${counts['__uncoded']}</span></div>`;

  // Per-anchor
  const acounts = {};
  ITEMS.forEach(it => {
    if (!acounts[it.anchor]) acounts[it.anchor] = {total:0, coded:0};
    acounts[it.anchor].total++;
    if (state.data[it.yt_id]?.label) acounts[it.anchor].coded++;
  });
  document.getElementById('anchor-stats').innerHTML = Object.entries(acounts).map(([a, v]) => `
    <div class="stat-row" style="grid-column:span 2">
      <span class="name">${escHtml(a)}</span>
      <span>${v.coded}/${v.total}</span>
    </div>
  `).join('');
}

function exportCsv() {
  // Reproduce coding_sheet schema, fill in human_label/coding_confidence/coding_notes
  const rows = [];
  // Use original ITEMS order
  const header = ['human_label','coding_confidence','coding_notes','coder','anchor','rank','similarity','YT_ID','language_norm','country_combo','protest_anywhere','TITLE','DESCRIPTION','feed_text','dur_sec','PUBLISHED_AT'];
  rows.push(header.join(','));
  for (const it of ITEMS) {
    const rec = state.data[it.yt_id] || {};
    const row = [
      rec.label || '',
      rec.confidence || '',
      rec.notes || '',
      state.coder,
      it.anchor,
      it.rank ?? '',
      it.similarity ?? '',
      it.yt_id,
      it.language_norm,
      it.country_combo,
      it.protest_anywhere ? 'True' : 'False',
      it.title,
      it.description,
      it.feed_text,
      it.dur_sec ?? '',
      it.published_at,
    ];
    rows.push(row.map(v => csvField(v)).join(','));
  }
  download('coding_sheet_for_human_FILLED.csv', rows.join('\n'), 'text/csv');
}

function csvField(v) {
  let s = String(v ?? '');
  if (/[",\n\r]/.test(s)) {
    s = '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

function exportJson() {
  download('coding_progress.json', JSON.stringify({coder: state.coder, data: state.data}, null, 2), 'application/json');
}

function download(filename, content, mime) {
  const blob = new Blob([content], {type: mime + ';charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 100);
}

function showImport() { document.getElementById('import-modal').classList.add('show'); }
function hideImport() { document.getElementById('import-modal').classList.remove('show'); }
function applyImport() {
  try {
    const raw = JSON.parse(document.getElementById('import-text').value);
    const incoming = raw.data || raw;
    state.data = {...state.data, ...incoming};
    saveState();
    updateProgress(); updateStats(); applyFilters(); renderItem();
    hideImport();
  } catch(e) { alert('Bad JSON: ' + e.message); }
}

function resetAll() {
  if (!confirm('Clear all labels for coder "' + state.coder + '"? This cannot be undone.')) return;
  state.data = {};
  saveState();
  updateProgress(); updateStats(); applyFilters(); renderItem();
}

function keybind(e) {
  // ignore when typing in inputs (except global handlers)
  const tag = (e.target.tagName || '').toLowerCase();
  if (tag === 'input' || tag === 'textarea' || tag === 'select') {
    if (e.key === 'Escape') e.target.blur();
    return;
  }
  if (e.key >= '1' && e.key <= '5') {
    const lbl = LABELS[parseInt(e.key)-1];
    if (lbl) setLabel(lbl.key);
    e.preventDefault();
  } else if (e.key === 'q') { setConfidence('1'); e.preventDefault(); }
  else if (e.key === 'w') { setConfidence('2'); e.preventDefault(); }
  else if (e.key === 'e') { setConfidence('3'); e.preventDefault(); }
  else if (e.key === 'j' || e.key === 'ArrowLeft') { prevItem(); e.preventDefault(); }
  else if (e.key === 'k' || e.key === 'ArrowRight') { nextItem(false); e.preventDefault(); }
  else if (e.key === 'Enter') { nextItem(true); e.preventDefault(); }
  else if (e.key === '/') { document.getElementById('f-search').focus(); e.preventDefault(); }
  else if (e.key === 'n') { document.getElementById('notes').focus(); e.preventDefault(); }
}

// Init
function init() {
  renderCodebook();
  buildFilters();
  buildLabelButtons();
  const ce = document.getElementById('coder-name');
  state.coder = ce.value;
  loadState();
  applyFilters();
  if (ITEMS.length) {
    // jump to first uncoded
    const firstUn = ITEMS.find(it => !state.data[it.yt_id]?.label);
    state.currentIdx = (firstUn || ITEMS[0]).idx;
    renderItem();
  }
  updateStats();
  ['f-anchor','f-lang','f-country','f-protest','f-status','f-label','f-search'].forEach(id => {
    document.getElementById(id).addEventListener('input', applyFilters);
  });
  document.querySelectorAll('.conf-btn').forEach(b => b.addEventListener('click', () => setConfidence(b.dataset.conf)));
  document.getElementById('notes').addEventListener('input', e => setNotes(e.target.value));
  document.getElementById('btn-prev').addEventListener('click', prevItem);
  document.getElementById('btn-next').addEventListener('click', () => nextItem(false));
  document.getElementById('btn-next-uncoded').addEventListener('click', () => nextItem(true));
  document.getElementById('btn-skip').addEventListener('click', () => nextItem(false));
  document.getElementById('btn-export-csv').addEventListener('click', exportCsv);
  document.getElementById('btn-export-json').addEventListener('click', exportJson);
  document.getElementById('btn-import').addEventListener('click', showImport);
  document.getElementById('btn-import-cancel').addEventListener('click', hideImport);
  document.getElementById('btn-import-apply').addEventListener('click', applyImport);
  document.getElementById('btn-reset').addEventListener('click', resetAll);
  ce.addEventListener('change', () => {
    state.coder = ce.value || 'sulzhytski';
    loadState();
    updateProgress(); updateStats(); applyFilters(); renderItem();
  });
  document.addEventListener('keydown', keybind);
}
init();
</script>
</body>
</html>
"""


def main():
    items = load_items()
    print(f"Loaded {len(items)} items")
    html = HTML_TEMPLATE \
        .replace("__ITEMS_PLACEHOLDER__", json.dumps(items, ensure_ascii=False)) \
        .replace("__LABELS_PLACEHOLDER__", json.dumps(LABELS, ensure_ascii=False)) \
        .replace("__CODEBOOK_PLACEHOLDER__", json.dumps(CODEBOOK_SHORT, ensure_ascii=False))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT}  ({OUT.stat().st_size/1024:.1f} KB)")
    print(f"\nOpen in browser:  open {OUT}")


if __name__ == "__main__":
    main()
