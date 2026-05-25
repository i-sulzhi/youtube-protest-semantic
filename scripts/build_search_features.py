"""Derive per-video search-discovery features from SEARCH_RESULTS.

Per `docs/EXPORTS_ROADMAP.md` §5 (EXPORT 5). Scoped to the 21,710 v2
feed-ready videos: 100% are present in SEARCH_RESULTS, 1.68M rows total.

Three column-name corrections vs the roadmap (verified against MariaDB
schema 2026-05-21):
  - SEARCH_RESULTS column is `RANK`, not `RANK_POSITION`.
  - SEARCHES PK is composite `(DATE, SEARCH_ID)`; the same SEARCH_ID does
    NOT map 1:1 to SEARCH_TERM (it's positional within a day) — so the
    join needs *both* DATE and SEARCH_ID.
  - SEARCH_RESULTS column is `DATE`, not `SEARCH_DATE`.

Term canonicalisation reuses `scripts/canonical_tags.py` so that the four
spellings of Lukashenko, three of Russia/Ukraine, etc., collapse onto
their anchor form. After collapse, the 17 raw terms become 7 canonical
clusters that align directly with the anchor vocabulary.

Output: outputs/search_features.csv, one row per v2 video, columns:
  YT_ID, n_search_terms_raw, n_search_terms_canon,
  best_rank, median_rank, mean_rank,
  first_search_date, last_search_date,
  visibility_days_top10, visibility_days_top50,
  primary_term_canon, n_top10_events
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pymysql

from canonical_tags import apply_synonyms, canonicalise, load_synonym_table


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--db-user",   default="sulzhytski")
    p.add_argument("--db-name",   default="metadata")
    p.add_argument("--db-socket", default="/tmp/mysql.sock")
    p.add_argument("--feed",      default="outputs/v2_feed_ready_with_tags.csv.gz")
    p.add_argument("--synonyms",  default="data/tag_synonyms.csv")
    p.add_argument("--out",       default="outputs/search_features.csv")
    return p.parse_args()


def fetch_rows(args, yt_ids: list[str]) -> pd.DataFrame:
    """Pull (YT_ID, DATE, SEARCH_TERM, RANK) for v2 videos via temp-table."""
    conn = pymysql.connect(user=args.db_user, database=args.db_name,
                           unix_socket=args.db_socket, charset="utf8mb4")
    with conn.cursor() as cur:
        cur.execute("CREATE TEMPORARY TABLE v2_ids (YT_ID VARCHAR(11) PRIMARY KEY)")
        cur.executemany("INSERT IGNORE INTO v2_ids VALUES (%s)",
                        [(y,) for y in yt_ids])
        cur.execute("""
            SELECT sr.YT_ID, sr.DATE, s.SEARCH_TERM, sr.RANK
            FROM SEARCH_RESULTS sr
            JOIN v2_ids v ON sr.YT_ID = v.YT_ID
            JOIN SEARCHES s
              ON s.DATE = sr.DATE AND s.SEARCH_ID = sr.SEARCH_ID
        """)
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=["YT_ID", "DATE", "SEARCH_TERM", "RANK"])
    df["DATE"] = pd.to_datetime(df["DATE"])
    df["RANK"] = pd.to_numeric(df["RANK"], errors="coerce").astype("Int64")
    return df


def main():
    args = parse_args()

    print(f"[1/5] Loading v2 feed: {args.feed}")
    feed = pd.read_csv(args.feed, usecols=["YT_ID"])
    print(f"      {len(feed):,} videos")

    print(f"\n[2/5] Loading synonym table: {args.synonyms}")
    synonyms = load_synonym_table(args.synonyms)
    print(f"      {len(synonyms):,} variant→canonical entries")

    print(f"\n[3/5] Pulling SEARCH_RESULTS ⋈ SEARCHES rows")
    sr = fetch_rows(args, feed["YT_ID"].tolist())
    print(f"      {len(sr):,} rows for {sr['YT_ID'].nunique():,} videos")

    print(f"\n[4/5] Canonicalising search terms")
    sr["term_canon"] = (sr["SEARCH_TERM"].map(canonicalise)
                                          .map(lambda t: apply_synonyms(t, synonyms)))
    raw_n = sr["SEARCH_TERM"].nunique()
    can_n = sr["term_canon"].nunique()
    print(f"      {raw_n} raw terms → {can_n} canonical terms")
    print(f"      canonical term frequencies:")
    for term, n in sr["term_canon"].value_counts().items():
        print(f"        {term:<14} {n:>10,}")

    print(f"\n[5/5] Computing per-video features")

    # Vectorised aggregations
    sr_valid = sr.dropna(subset=["RANK"])
    by_vid = sr_valid.groupby("YT_ID")

    agg = pd.DataFrame({
        "n_search_terms_raw":   sr.groupby("YT_ID")["SEARCH_TERM"].nunique(),
        "n_search_terms_canon": sr.groupby("YT_ID")["term_canon"].nunique(),
        "best_rank":            by_vid["RANK"].min(),
        "median_rank":          by_vid["RANK"].median(),
        "mean_rank":            by_vid["RANK"].mean().round(1),
        "first_search_date":    sr.groupby("YT_ID")["DATE"].min(),
        "last_search_date":     sr.groupby("YT_ID")["DATE"].max(),
    })

    # visibility — distinct dates with rank <= threshold
    def vis_days(threshold: int) -> pd.Series:
        sub = sr_valid[sr_valid["RANK"] <= threshold]
        return sub.groupby("YT_ID")["DATE"].nunique()

    agg["visibility_days_top10"] = vis_days(10).reindex(agg.index, fill_value=0)
    agg["visibility_days_top50"] = vis_days(50).reindex(agg.index, fill_value=0)
    agg["n_top10_events"] = (sr_valid[sr_valid["RANK"] <= 10]
                             .groupby("YT_ID").size()
                             .reindex(agg.index, fill_value=0))

    # primary canonical term — mode per video; tie broken by frequency in
    # the whole dataset (so popular terms win ties, deterministic)
    global_freq = sr["term_canon"].value_counts().to_dict()
    def primary(g: pd.Series) -> str:
        vc = g.value_counts()
        top_n = vc.iloc[0]
        winners = vc[vc == top_n].index
        return max(winners, key=lambda t: global_freq.get(t, 0))
    agg["primary_term_canon"] = sr.groupby("YT_ID")["term_canon"].agg(primary)

    out = (agg.reset_index()
              .merge(feed[["YT_ID"]], on="YT_ID", how="right"))

    out_cols = [
        "YT_ID",
        "n_search_terms_raw", "n_search_terms_canon",
        "best_rank", "median_rank", "mean_rank",
        "first_search_date", "last_search_date",
        "visibility_days_top10", "visibility_days_top50", "n_top10_events",
        "primary_term_canon",
    ]
    out = out[out_cols]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    kb = Path(args.out).stat().st_size / 1024
    print(f"      wrote {args.out}  ({len(out):,} rows, {kb:.0f} KB)")

    print(f"\nDistribution checks:")
    print(f"  best_rank:             median={int(out['best_rank'].median())}, "
          f"p10={int(out['best_rank'].quantile(0.1))}, p90={int(out['best_rank'].quantile(0.9))}")
    print(f"  n_search_terms_canon:  median={int(out['n_search_terms_canon'].median())}, "
          f"p90={int(out['n_search_terms_canon'].quantile(0.9))}, max={int(out['n_search_terms_canon'].max())}")
    n_ever_top10 = int((out["visibility_days_top10"] > 0).sum())
    print(f"  ever-top10 videos:     {n_ever_top10:,} / {len(out):,} ({100*n_ever_top10/len(out):.1f}%)")

    print(f"\nPrimary canonical term — distribution across v2 videos:")
    print(out["primary_term_canon"].value_counts().to_string())


if __name__ == "__main__":
    main()
