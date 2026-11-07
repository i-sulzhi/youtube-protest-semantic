"""Recall mine — gate candidates from the distilled classifier's corpus scan.

train_distilled_gate.py scores ALL 21,710 feed videos. Videos OUTSIDE the
retrieval pool with high P(direct) are exactly what the anchor-based semantic
retrieval missed (different phrasing, no anchor proximity) — the third
expansion source next to channels (Block 1.3) and the hypergraph (Stage F).

Output: outputs/distill_expansion_candidates.csv — briefing-ready
(`__source__ = distill_expansion`), same incremental-gate workflow as
channel_expand_pool.py.

Run from project root (after train_distilled_gate.py):
    .venv_v2/bin/python scripts/distill_expand_pool.py --min-p 0.5 --max-new 200
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--scores", default="outputs/distilled_relevance_feed.csv")
    p.add_argument("--feed", default="outputs/v2_feed_ready.csv.gz")
    p.add_argument("--pool", default="outputs/retrieval_nway/all_sources_combined.csv")
    p.add_argument("--gold", default="mini_study/coding_layer2.csv")
    p.add_argument("--min-p", type=float, default=0.5, help="min P(direct)")
    p.add_argument("--max-new", type=int, default=200)
    p.add_argument("--out", default="outputs/distill_expansion_candidates.csv")
    return p.parse_args()


def main():
    a = parse_args()
    sc = Path(a.scores)
    if not sc.exists():
        raise SystemExit(f"{a.scores} not found — run train_distilled_gate.py "
                         "(make distill) first.")
    s = pd.read_csv(sc)
    pool_ids = set(pd.read_csv(a.pool, usecols=["YT_ID"])["YT_ID"])
    gold_ids = set(pd.read_csv(a.gold)["yt_id"])
    cand = s[(s["p_direct"] >= a.min_p)
             & ~s["YT_ID"].isin(pool_ids | gold_ids)]
    print(f"[1/2] {len(cand)} outside-pool videos with P(direct) ≥ {a.min_p} "
          f"(of {len(s):,} scored)")
    if len(cand) == 0:
        raise SystemExit("No candidates at this threshold — lower --min-p.")
    cand = cand.sort_values("p_direct", ascending=False).head(a.max_new)

    feed = pd.read_csv(a.feed).set_index("YT_ID")
    f = feed.loc[cand["YT_ID"]]
    out = pd.DataFrame({
        "anchor": "distill-mined",
        "YT_ID": cand["YT_ID"].values,
        "TITLE": f["TITLE"].values,
        "DESCRIPTION": f["DESCRIPTION"].values,
        "DEFAULT_AUDIO_LANG": f["DEFAULT_AUDIO_LANG"].values,
        "PUBLISHED_AT": f["PUBLISHED_AT"].values,
        "country_combo": f["country_combo"].values,
        "protest_anywhere": f["protest_anywhere"].values,
        "protest_in_title": f["protest_in_title"].values,
        "protest_in_desc": f["protest_in_desc"].values,
        "dur_sec": f["dur_sec"].values,
        "feed_text": f["feed_text"].values,
        "similarity": float("nan"),
        "__source__": "distill_expansion",
        "p_direct": cand["p_direct"].values,
    })
    out.to_csv(a.out, index=False)
    kw = int(out["protest_anywhere"].sum())
    print(f"[2/2] wrote {a.out}: {len(out)} candidates "
          f"(p_direct {out['p_direct'].min():.2f}–{out['p_direct'].max():.2f}; "
          f"{kw} carry a protest keyword — the {len(out)-kw} without one are "
          "the pure embedding-blind-spot finds)")
    print("\nNext: incremental gate (build_relevance_briefings.py --pool "
          f"{a.out} --exclude-pred-glob …), then re-rank + re-gate.")


if __name__ == "__main__":
    main()
