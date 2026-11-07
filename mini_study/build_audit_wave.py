"""Stage E — random audit wave: unbiased gate accuracy on the expanded pool.

All 60 round-1 gold items come from the original 496-video e5-large pool, so
the gate's κ on the 603 expansion videos (esp. tags-surfaced, text-poor ones)
is extrapolated, not measured (raw-dataset validation, 2026-06-10). Round-2 is
uncertainty-selected and cannot fix this — it is adversarial by design.

This selects a RANDOM wave, stratified by retrieval provenance:

  * tags_only    — found only by the with-tags embedding tables (the new,
                   unvalidated pool region; gets the largest allocation),
  * mixed        — found by both no-tags and with-tags sources,
  * no_tags_only — found only by the no-tags tables (the validated region;
                   serves as the within-wave control).

Selection is seeded (reproducible) and excludes everything already coded or
queued for coding (round-1 gold, round-2 wave, gold v2 if present). Outputs a
BLIND sheet (no LLM label) + manifest + self-contained HTML coder, mirroring
the round-2 instrument. It does NOT fabricate labels.

After the PI codes (Export CSV → coding_sheet_audit_FILLED.csv):
    .venv_v2/bin/python mini_study/merge_round2_gold.py \
        --filled mini_study/coding_sheet_audit_FILLED.csv \
        --round1 mini_study/coding_gold_v2.csv --round-label 3 \
        --out mini_study/coding_gold_v3.csv
    .venv_v2/bin/python scripts/stage_e_gate.py --gold mini_study/coding_gold_v3.csv

Run from project root:
    .venv_v2/bin/python mini_study/build_audit_wave.py --budget 20
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_active_learning_sheet import _HTML  # noqa: E402  (shared coder UI)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--scored", default="outputs/stage_e/protest_index_scored.csv")
    p.add_argument("--pool",   default="outputs/retrieval_nway/all_sources_combined.csv")
    p.add_argument("--gold",   default="mini_study/coding_layer2.csv")
    p.add_argument("--round2-manifest", default="mini_study/round2_selection_manifest.csv")
    p.add_argument("--gold-v2", default="mini_study/coding_gold_v2.csv",
                   help="excluded too if it exists (post round-2 merge)")
    p.add_argument("--budget", type=int, default=20)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out-dir", default="mini_study")
    return p.parse_args()


def stratum(sources: set) -> str:
    if all("with_tags" in s for s in sources):
        return "tags_only"
    if all("with_tags" not in s for s in sources):
        return "no_tags_only"
    return "mixed"


def main():
    a = parse_args()
    out = Path(a.out_dir)

    pool = pd.read_csv(a.pool)
    src = pool.groupby("YT_ID")["__source__"].apply(set).rename("sources")
    meta = pool.drop_duplicates("YT_ID").set_index("YT_ID")[
        ["TITLE", "DESCRIPTION", "DEFAULT_AUDIO_LANG", "country_combo",
         "protest_anywhere"]].join(src)
    meta["stratum"] = meta["sources"].apply(stratum)

    scored = pd.read_csv(a.scored).set_index("YT_ID")
    meta = meta.join(scored[["primary_anchor", "relevance_llm", "relevance_conf",
                             "rank", "composite_score"]])

    # exclude everything already coded or queued
    excluded = set(pd.read_csv(a.gold)["yt_id"])
    for f, col in [(a.round2_manifest, "YT_ID"), (a.gold_v2, "yt_id")]:
        if Path(f).exists():
            excluded |= set(pd.read_csv(f)[col])
    cand = meta[~meta.index.isin(excluded)].copy()

    # allocation: priority to the unvalidated tags-only region
    alloc = {"tags_only": round(0.4 * a.budget),
             "mixed": round(0.3 * a.budget)}
    alloc["no_tags_only"] = a.budget - sum(alloc.values())
    picks = []
    short = 0
    for st, k in alloc.items():
        grp = cand[cand["stratum"] == st]
        take = min(k, len(grp))
        short += k - take
        picks.append(grp.sample(take, random_state=a.seed))
    if short:  # redistribute shortfall randomly over the remainder
        rest = cand[~cand.index.isin(pd.concat(picks).index)]
        picks.append(rest.sample(min(short, len(rest)), random_state=a.seed))
    sel = pd.concat(picks).sample(frac=1, random_state=a.seed)  # shuffle order
    sel = sel.reset_index().rename(columns={"index": "YT_ID"})

    # --- 1. internal manifest --------------------------------------------- #
    man = sel[["YT_ID", "stratum", "primary_anchor", "relevance_llm",
               "relevance_conf", "rank", "composite_score"]].copy()
    man["sources"] = sel["sources"].apply(lambda s: "|".join(sorted(s)))
    man.to_csv(out / "audit_selection_manifest.csv", index=False)

    # --- 2. blind coding sheet (NO llm label, NO stratum) ------------------ #
    sheet = pd.DataFrame({
        "protest_relevance": "",
        "coding_confidence": "",
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
    sheet.to_csv(out / "coding_sheet_audit.csv", index=False)

    # --- 3. self-contained HTML coder (shared template, audit branding) ---- #
    items = [{
        "yt": r.YT_ID, "anchor": r.primary_anchor,
        "lang": r.DEFAULT_AUDIO_LANG if isinstance(r.DEFAULT_AUDIO_LANG, str) else "",
        "country": r.country_combo, "kw": bool(r.protest_anywhere),
        "title": r.TITLE if isinstance(r.TITLE, str) else "",
        "desc": (r.DESCRIPTION if isinstance(r.DESCRIPTION, str) else "")[:1500],
    } for r in sel.itertuples()]
    html = (_HTML
            .replace("Stage E — round-2 coding (protest_relevance)",
                     "Stage E — audit coding (protest_relevance)")
            .replace("Stage E round-2 — protest_relevance",
                     "Stage E audit wave — protest_relevance")
            .replace("stageE_round2_v1", "stageE_audit_v1")
            .replace("coding_sheet_round2_FILLED.csv",
                     "coding_sheet_audit_FILLED.csv")
            .replace("__ITEMS__", json.dumps(items, ensure_ascii=False)))
    (out / "coding_audit.html").write_text(html, encoding="utf-8")

    # --- report ------------------------------------------------------------ #
    print(f"Selected {len(sel)}/{a.budget} random items (seed={a.seed}); "
          f"{len(cand)} candidates after excluding {len(excluded)} coded/queued")
    print("by stratum:", sel["stratum"].value_counts().to_dict())
    print("by anchor: ", sel["primary_anchor"].value_counts().to_dict())
    print("by LLM label (manifest only, sheet is blind):",
          sel["relevance_llm"].value_counts().to_dict())
    print(f"\nwrote {out/'coding_sheet_audit.csv'}")
    print(f"wrote {out/'audit_selection_manifest.csv'}")
    print(f"wrote {out/'coding_audit.html'}  (open in a browser to code)")
    print("\nAfter coding, merge as round 3 (see module docstring).")


if __name__ == "__main__":
    main()
