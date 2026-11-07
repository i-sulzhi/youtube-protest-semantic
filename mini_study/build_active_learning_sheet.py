"""Stage E Task 4 — active-learning coding sheet (grow the 60-item gold).

Selects the most *informative* uncoded videos from the 4-way pool for the PI to
hand-code on the `protest_relevance` axis, so the κ that validates the gate rests
on more than 60 labels. Targets the gate's uncertain zone, per the roadmap:

  * LLM confidence==1 items (the sub-agents flagged these),
  * `indirect` predictions (the fuzzy middle class κ is most fragile on),
  * rank/label disagreements — gate `absent` but high composite rank (a possible
    gate false-negative), or kept (direct/indirect) but ranked low.

It does NOT fabricate labels. It writes a BLIND coding instrument (no LLM label
shown, to avoid anchoring the coder) + an internal selection manifest for the
post-hoc analysis. After the PI codes, `mini_study/merge_round2_gold.py` folds
the new labels into an enlarged gold and the gate/tune scripts recompute κ.

Outputs:
  mini_study/coding_sheet_round2.csv        blind sheet (fill protest_relevance)
  mini_study/round2_selection_manifest.csv  why each item was picked (internal)
  mini_study/coding_round2.html             self-contained click-to-code UI

Run from project root:
    .venv_v2/bin/python mini_study/build_active_learning_sheet.py --budget 50
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--scored", default="outputs/stage_e/protest_index_scored.csv")
    p.add_argument("--pool",   default="outputs/retrieval_nway/all_sources_combined.csv")
    p.add_argument("--gold",   default="mini_study/coding_layer2.csv")
    p.add_argument("--budget", type=int, default=50, help="items to select")
    p.add_argument("--out-dir", default="mini_study")
    return p.parse_args()


def main():
    a = parse_args()
    out = Path(a.out_dir)

    scored = pd.read_csv(a.scored)
    scored["rank"] = pd.to_numeric(scored["rank"], errors="coerce")
    scored["relevance_conf"] = pd.to_numeric(scored["relevance_conf"], errors="coerce")
    pool = pd.read_csv(a.pool).drop_duplicates("YT_ID")[
        ["YT_ID", "TITLE", "DESCRIPTION", "DEFAULT_AUDIO_LANG", "country_combo",
         "protest_anywhere"]]
    gold = set(pd.read_csv(a.gold)["yt_id"])

    df = scored.merge(pool, on="YT_ID", how="left", suffixes=("", "_p"))
    df = df[~df["YT_ID"].isin(gold)].copy()
    N = len(scored)
    top, bot = 0.30 * N, 0.70 * N

    # --- uncertainty tags + score ----------------------------------------- #
    df["t_conf1"]    = (df["relevance_conf"] == 1)
    df["t_indirect"] = (df["relevance_llm"] == "indirect")
    df["t_gate_fn"]  = (df["relevance_llm"] == "absent") & (df["rank"] <= top)
    df["t_lowrank"]  = (df["relevance_llm"].isin(["direct", "indirect"])) & (df["rank"] >= bot)
    df["uncertainty"] = (3 * df["t_conf1"] + 2 * df["t_indirect"]
                         + 2 * df["t_gate_fn"] + 1 * df["t_lowrank"])
    cand = df[df["uncertainty"] > 0].copy()
    # within anchor, best-first: more uncertain, then nearer the gate boundary
    cand = cand.sort_values(["uncertainty", "rank"], ascending=[False, True])

    # --- round-robin across anchors so no single anchor dominates ---------- #
    by_anchor = {k: list(v.index) for k, v in cand.groupby("primary_anchor", sort=False)}
    order = sorted(by_anchor, key=lambda k: -len(by_anchor[k]))
    picks, cursors = [], {k: 0 for k in by_anchor}
    while len(picks) < a.budget:
        progressed = False
        for k in order:
            if cursors[k] < len(by_anchor[k]):
                picks.append(by_anchor[k][cursors[k]]); cursors[k] += 1; progressed = True
                if len(picks) >= a.budget:
                    break
        if not progressed:
            break
    sel = cand.loc[picks].copy()

    def tags(r):
        return "|".join(t for t, on in [("conf1", r.t_conf1), ("indirect", r.t_indirect),
                                        ("gate_fn", r.t_gate_fn), ("kept_lowrank", r.t_lowrank)] if on)
    sel["why_selected"] = sel.apply(tags, axis=1)

    # --- 1. internal manifest (why) --------------------------------------- #
    man_cols = ["YT_ID", "primary_anchor", "relevance_llm", "relevance_conf",
                "rank", "composite_score", "uncertainty", "why_selected"]
    sel[man_cols].to_csv(out / "round2_selection_manifest.csv", index=False)

    # --- 2. blind coding sheet (NO llm label) ----------------------------- #
    sheet = pd.DataFrame({
        "protest_relevance": "",          # PI fills: direct | indirect | absent
        "coding_confidence": "",          # 1 low / 2 med / 3 high
        "coding_notes": "",
        "coder": "sulzhytski",
        "YT_ID": sel["YT_ID"].values,
        "youtube_url": "https://www.youtube.com/watch?v=" + sel["YT_ID"],
        "anchor": sel["primary_anchor"].values,
        "lang": sel["DEFAULT_AUDIO_LANG"].values,
        "country": sel["country_combo"].values,
        "protest_keyword": sel["protest_anywhere"].values,
        "TITLE": sel["TITLE"].values,
        "DESCRIPTION": sel["DESCRIPTION"].fillna("").str[:1200].values,
    })
    sheet.to_csv(out / "coding_sheet_round2.csv", index=False)

    # --- 3. self-contained HTML coder ------------------------------------- #
    items = [{
        "yt": r.YT_ID, "anchor": r.primary_anchor,
        "lang": r.DEFAULT_AUDIO_LANG if isinstance(r.DEFAULT_AUDIO_LANG, str) else "",
        "country": r.country_combo, "kw": bool(r.protest_anywhere),
        "title": r.TITLE if isinstance(r.TITLE, str) else "",
        "desc": (r.DESCRIPTION if isinstance(r.DESCRIPTION, str) else "")[:1500],
    } for r in sel.itertuples()]
    html = _HTML.replace("__ITEMS__", json.dumps(items, ensure_ascii=False))
    (out / "coding_round2.html").write_text(html, encoding="utf-8")

    # --- report ----------------------------------------------------------- #
    print(f"Selected {len(sel)}/{a.budget} of {len(cand)} uncertain items "
          f"({len(df)} uncoded, 60 already gold)")
    print("by anchor:", sel["primary_anchor"].value_counts().to_dict())
    print("by LLM label:", sel["relevance_llm"].value_counts().to_dict())
    print("tag coverage:", {t.replace("t_", ""): int(sel[t].sum())
                            for t in ["t_conf1", "t_indirect", "t_gate_fn", "t_lowrank"]})
    print(f"\nwrote {out/'coding_sheet_round2.csv'}")
    print(f"wrote {out/'round2_selection_manifest.csv'}")
    print(f"wrote {out/'coding_round2.html'}  (open in a browser to code)")


_HTML = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Stage E — round-2 coding (protest_relevance)</title>
<style>
:root{--bg:#0f1115;--panel:#1a1d24;--panel2:#22262f;--fg:#e6e8eb;--mut:#9aa0aa;--bd:#2c313b;
--direct:#2ea043;--indirect:#d29922;--absent:#6e7681;}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
header{position:sticky;top:0;background:var(--panel);border-bottom:1px solid var(--bd);padding:10px 16px;display:flex;gap:16px;align-items:center;flex-wrap:wrap;z-index:9}
header b{font-size:15px} .prog{color:var(--mut)} input,select{background:var(--panel2);color:var(--fg);border:1px solid var(--bd);border-radius:6px;padding:4px 8px}
button{cursor:pointer;border:1px solid var(--bd);border-radius:6px;background:var(--panel2);color:var(--fg);padding:6px 12px}
.exp{background:#1f6feb;border-color:#1f6feb}
main{max-width:920px;margin:0 auto;padding:16px}
.card{background:var(--panel);border:1px solid var(--bd);border-radius:10px;padding:14px 16px;margin:12px 0}
.card.done{border-color:#2ea04366}
.meta{color:var(--mut);font-size:12px;margin-bottom:6px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.chip{background:var(--panel2);border:1px solid var(--bd);border-radius:20px;padding:1px 8px}
.title{font-weight:600;font-size:15px;margin:4px 0}
.desc{white-space:pre-wrap;max-height:160px;overflow:auto;background:var(--panel2);border:1px solid var(--bd);border-radius:8px;padding:8px;color:#cfd3da;font-size:13px}
.btns{display:flex;gap:8px;margin:10px 0 6px}
.btns button{flex:0 0 auto;font-weight:600}
.b-direct.sel{background:var(--direct);border-color:var(--direct);color:#fff}
.b-indirect.sel{background:var(--indirect);border-color:var(--indirect);color:#111}
.b-absent.sel{background:var(--absent);border-color:var(--absent);color:#fff}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:6px}
.row input[type=text]{flex:1;min-width:220px}
a{color:#58a6ff}
.cb{font-size:12px;color:var(--mut);background:var(--panel);border:1px solid var(--bd);border-radius:8px;padding:8px 12px;margin:8px 0}
</style></head><body>
<header>
  <b>Stage E round-2 — protest_relevance</b>
  <span class="prog" id="prog"></span>
  <span>coder <input id="coder" value="sulzhytski" style="width:120px"></span>
  <button class="exp" onclick="exportCSV()">⤓ Export CSV</button>
  <button onclick="if(confirm('Clear all local answers?')){localStorage.removeItem(KEY);location.reload()}">Reset</button>
</header>
<main>
<div class="cb"><b>Codebook (TOPIC axis):</b> <b>direct</b> = the video is about a protest/rally/march/strike (or footage of one); arrests <i>at</i> a protest.
<b>indirect</b> = protest is peripheral — repression/arrests as the <i>aftermath</i>, court cases of protesters, counter-protest, crisis that followed protests.
<b>absent</b> = not about a protest (war, a speech, talk-show, mobilisation, elections…). TOPIC ≠ stance. You may open the video to judge. Keys: 1=direct 2=indirect 3=absent.</div>
<div id="list"></div>
</main>
<script>
const DATA = __ITEMS__;
const KEY = "stageE_round2_v1";
let state = {}; try{state = JSON.parse(localStorage.getItem(KEY)||"{}")}catch(e){state={}}
function save(){localStorage.setItem(KEY, JSON.stringify(state))}
function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}
function rec(yt){return state[yt]||(state[yt]={rel:"",conf:"",notes:""})}
function setRel(yt,v){rec(yt).rel=v;save();render()}
function setConf(yt,v){rec(yt).conf=v;save();updateProg()}
function setNotes(yt,v){rec(yt).notes=v;save()}
function updateProg(){const n=DATA.filter(d=>state[d.yt]&&state[d.yt].rel).length;
  document.getElementById("prog").textContent=`${n} / ${DATA.length} coded`}
function render(){
  const L=document.getElementById("list"); L.innerHTML="";
  DATA.forEach((d,i)=>{const r=rec(d.yt); const done=r.rel?"done":"";
    const div=document.createElement("div"); div.className="card "+done;
    div.innerHTML=`<div class="meta"><span>#${i+1}</span>
      <span class="chip">${esc(d.anchor)}</span><span class="chip">lang:${esc(d.lang)||"?"}</span>
      <span class="chip">${esc(d.country)}</span>${d.kw?'<span class="chip">keyword</span>':''}
      <a href="https://www.youtube.com/watch?v=${d.yt}" target="_blank">▶ ${d.yt}</a></div>
      <div class="title">${esc(d.title)}</div>
      <div class="desc">${esc(d.desc)||"(no description)"}</div>
      <div class="btns">
        <button class="b-direct ${r.rel=='direct'?'sel':''}" onclick="setRel('${d.yt}','direct')">direct</button>
        <button class="b-indirect ${r.rel=='indirect'?'sel':''}" onclick="setRel('${d.yt}','indirect')">indirect</button>
        <button class="b-absent ${r.rel=='absent'?'sel':''}" onclick="setRel('${d.yt}','absent')">absent</button>
      </div>
      <div class="row">conf
        <select onchange="setConf('${d.yt}',this.value)">
          <option value="">–</option><option ${r.conf=='1'?'selected':''}>1</option>
          <option ${r.conf=='2'?'selected':''}>2</option><option ${r.conf=='3'?'selected':''}>3</option></select>
        <input type="text" placeholder="notes…" value="${esc(r.notes)}" oninput="setNotes('${d.yt}',this.value)">
      </div>`;
    L.appendChild(div);
  });
  updateProg();
}
document.addEventListener("keydown",e=>{
  const t=(e.target.tagName||"").toLowerCase(); if(t=="input"||t=="textarea"||t=="select")return;
  const card=document.elementFromPoint(window.innerWidth/2,160); // nearest top card
  const idx=[...document.querySelectorAll(".card")].findIndex(c=>c.getBoundingClientRect().top>120);
  const d=DATA[Math.max(0,idx)]; if(!d)return;
  if(e.key=="1")setRel(d.yt,"direct"); if(e.key=="2")setRel(d.yt,"indirect"); if(e.key=="3")setRel(d.yt,"absent");
});
function exportCSV(){
  const coder=document.getElementById("coder").value||"sulzhytski";
  const q=s=>'"'+String(s==null?"":s).replace(/"/g,'""')+'"';
  const rows=[["yt_id","protest_relevance","coding_confidence","coding_notes","coder"].join(",")];
  DATA.forEach(d=>{const r=state[d.yt]||{};rows.push([d.yt,r.rel||"",r.conf||"",q(r.notes||""),coder].join(","))});
  const blob=new Blob([rows.join("\n")],{type:"text/csv"});
  const a=document.createElement("a");a.href=URL.createObjectURL(blob);
  a.download="coding_sheet_round2_FILLED.csv";a.click();
}
render();
</script></body></html>"""


if __name__ == "__main__":
    main()
