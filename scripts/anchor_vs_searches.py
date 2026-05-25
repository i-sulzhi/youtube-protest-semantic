"""Cross-validate anchor retrievals against actual YouTube search-discovery channels.

Per `docs/EXPORTS_ROADMAP.md` §5 (EXPORT 5 final part). The 7 v2 anchors
are *hypotheses* about how protest content groups; SEARCHES are the
*observed* discovery vocabulary used by the YouTube scraper. This script
asks: for the videos a given anchor retrieves, what search term(s)
actually surfaced them on YouTube?

If an anchor retrieves videos predominantly surfaced by an unrelated
search term, the anchor wording is off (or the embedding model is finding
something the scraper missed — equally interesting).

Inputs:
  outputs/retrieval_nway/all_sources_combined.csv  (anchor, YT_ID, ...)
  outputs/search_features.csv                       (YT_ID, primary_term_canon, ...)

Output:
  outputs/anchor_vs_searches.csv  long format:
    anchor, primary_term_canon, n_videos, share_pct
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--retrievals", default="outputs/retrieval_nway/all_sources_combined.csv")
    p.add_argument("--features",   default="outputs/search_features.csv")
    p.add_argument("--out",        default="outputs/anchor_vs_searches.csv")
    return p.parse_args()


def main():
    args = parse_args()

    print(f"[1/3] Loading anchor retrievals: {args.retrievals}")
    ret = pd.read_csv(args.retrievals, usecols=["anchor", "YT_ID"])
    ret = ret.drop_duplicates(subset=["anchor", "YT_ID"])
    print(f"      {len(ret):,} (anchor, YT_ID) pairs; {ret['anchor'].nunique()} anchors")

    print(f"\n[2/3] Loading search features: {args.features}")
    feat = pd.read_csv(args.features, usecols=["YT_ID", "primary_term_canon"])
    print(f"      {len(feat):,} videos")

    print(f"\n[3/3] Joining and summarising")
    j = ret.merge(feat, on="YT_ID", how="left")
    coverage = j["primary_term_canon"].notna().mean()
    print(f"      {100*coverage:.1f}% of (anchor, video) pairs joined with a search-term row")

    # Per-anchor distribution
    counts = (j.dropna(subset=["primary_term_canon"])
                .groupby(["anchor", "primary_term_canon"])
                .size().rename("n_videos").reset_index())
    totals = counts.groupby("anchor")["n_videos"].transform("sum")
    counts["share_pct"] = (100 * counts["n_videos"] / totals).round(1)
    counts = counts.sort_values(["anchor", "n_videos"], ascending=[True, False])

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    counts.to_csv(args.out, index=False)
    print(f"      wrote {args.out}  ({len(counts):,} rows)")

    print(f"\nPer-anchor search-term breakdown:")
    for anchor, sub in counts.groupby("anchor"):
        print(f"\n  {anchor}  (n_videos={int(totals[counts.anchor == anchor].iloc[0]):,}):")
        for _, row in sub.iterrows():
            print(f"    {row['primary_term_canon']:<14} "
                  f"{int(row['n_videos']):>6,}  ({row['share_pct']:>5.1f}%)")


if __name__ == "__main__":
    main()
