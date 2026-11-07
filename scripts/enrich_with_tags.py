"""Enrich the text-ready feed CSV with the per-video tags column.

Two tag sources (output schema identical):

  default   complete_video_info_202404251556.csv (350K rows, 174 MB local CSV)
  --from-db MariaDB VID_TAGS ⋈ TAGS — covers 19,624 v2 videos (≥ the CSV's
            19,623; DB audit 2026-06-11), removing the big-CSV dependency.
            ⚠ tag ORDER inside the string may differ from the CSV (the DB has
            no order column; we sort alphabetically for determinism), so
            re-embedding from a --from-db feed is a (tiny) embedding change —
            do it at the next planned re-embed, not mid-cycle.

Reads:
  outputs/v2_feed_ready.csv.gz           (21,710 rows)
Writes:
  outputs/v2_feed_ready_with_tags.csv.gz (same rows, +tags column)

Run from the project root:
    .venv_v2/bin/python scripts/enrich_with_tags.py
    .venv_v2/bin/python scripts/enrich_with_tags.py --from-db
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

FEED_IN = "outputs/v2_feed_ready.csv.gz"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--from-db", action="store_true",
                   help="pull tags from MariaDB instead of the local CSV")
    p.add_argument("--tags-csv", default="complete_video_info_202404251556.csv")
    p.add_argument("--out", default="outputs/v2_feed_ready_with_tags.csv.gz")
    return p.parse_args()


def tags_from_csv(path: str) -> pd.DataFrame:
    print(f"\n[2/4] Reading tags: {path}")
    tags = pd.read_csv(path, usecols=["YT_ID", "tags"], dtype=str,
                       keep_default_na=False, na_values=[""])
    print(f"      {len(tags):,} rows in source")
    tags = tags.drop_duplicates(subset=["YT_ID"], keep="first")
    print(f"      {len(tags):,} rows after dedup on YT_ID")
    return tags


def tags_from_db(feed_ids: pd.Series) -> pd.DataFrame:
    import pymysql
    print("\n[2/4] Pulling tags from MariaDB (VID_TAGS ⋈ TAGS) …")
    conn = pymysql.connect(user="sulzhytski", unix_socket="/tmp/mysql.sock",
                           database="metadata", charset="utf8mb4")
    try:
        with conn.cursor() as c:
            c.execute("CREATE TEMPORARY TABLE scope (YT_ID varchar(11) PRIMARY KEY)")
            c.executemany("INSERT INTO scope VALUES (%s)", feed_ids.tolist())
        conn.commit()
        long = pd.read_sql(
            "SELECT vt.YT_ID, t.TAG FROM VID_TAGS vt "
            "JOIN TAGS t ON t.ID = vt.TAG_ID "
            "JOIN scope ON scope.YT_ID = vt.YT_ID", conn)
    finally:
        conn.close()
    print(f"      {len(long):,} (video, tag) pairs for "
          f"{long['YT_ID'].nunique():,} videos")
    # deterministic order: the DB stores no tag order — sort alphabetically
    tags = (long.dropna(subset=["TAG"]).astype({"TAG": str})
                .sort_values(["YT_ID", "TAG"])
                .groupby("YT_ID")["TAG"].agg(",".join)
                .rename("tags").reset_index())
    return tags


def main():
    a = parse_args()
    print(f"[1/4] Reading feed: {FEED_IN}")
    feed = pd.read_csv(FEED_IN, dtype=str, keep_default_na=False, na_values=[""])
    print(f"      {len(feed):,} rows, {len(feed.columns)} columns")

    tags = tags_from_db(feed["YT_ID"]) if a.from_db else tags_from_csv(a.tags_csv)

    print("\n[3/4] LEFT JOIN feed ⊳ tags on YT_ID")
    enriched = feed.merge(tags, on="YT_ID", how="left")
    n_with = enriched["tags"].notna().sum()
    print(f"      videos with tags:    {n_with:>6,}  "
          f"({100*n_with/len(enriched):.1f}%)")
    print(f"      videos without tags: {len(enriched)-n_with:>6,}  "
          f"({100*(len(enriched)-n_with)/len(enriched):.1f}%)")
    enriched["tags"] = enriched["tags"].fillna("")

    tl = enriched.loc[enriched["tags"] != "", "tags"].str.len()
    tc = enriched.loc[enriched["tags"] != "", "tags"].str.count(",") + 1
    if len(tl):
        print(f"      tag string length: median={int(tl.median())},  "
              f"p90={int(tl.quantile(0.9))},  max={int(tl.max())}")
        print(f"      tags per video:    median={int(tc.median())},  "
              f"p90={int(tc.quantile(0.9))},  max={int(tc.max())}")

    print(f"\n[4/4] Writing enriched feed: {a.out}")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(a.out, index=False, compression="gzip")
    size_mb = Path(a.out).stat().st_size / 1024 / 1024
    print(f"      wrote {size_mb:.1f} MB, {len(enriched.columns)} columns "
          f"(was {len(feed.columns)})")


if __name__ == "__main__":
    main()
