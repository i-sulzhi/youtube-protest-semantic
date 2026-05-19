"""Enrich the text-ready feed CSV with the per-video tags column.

Reads:
  outputs/v2_feed_ready.csv.gz           (21,710 rows produced by EDA notebook)
  complete_video_info_202404251556.csv   (350K rows, YT_ID + tags + PUBLISHED_AT)

Writes:
  outputs/v2_feed_ready_with_tags.csv.gz (same rows, +tags column)

Tags are comma-separated single strings. Coverage on the politics subset
is reported at the end.

Run from the project root:
    .venv_v2/bin/python scripts/enrich_with_tags.py
"""
from __future__ import annotations

import pandas as pd
from pathlib import Path


FEED_IN   = "outputs/v2_feed_ready.csv.gz"
TAGS_CSV  = "complete_video_info_202404251556.csv"
FEED_OUT  = "outputs/v2_feed_ready_with_tags.csv.gz"


def main():
    print(f"[1/4] Reading feed: {FEED_IN}")
    feed = pd.read_csv(FEED_IN, dtype=str, keep_default_na=False, na_values=[""])
    print(f"      {len(feed):,} rows, {len(feed.columns)} columns")

    print(f"\n[2/4] Reading tags: {TAGS_CSV}")
    # Read only the two columns we need — saves ~100 MB of memory
    tags = pd.read_csv(TAGS_CSV, usecols=["YT_ID", "tags"], dtype=str,
                       keep_default_na=False, na_values=[""])
    print(f"      {len(tags):,} rows in source")
    tags = tags.drop_duplicates(subset=["YT_ID"], keep="first")
    print(f"      {len(tags):,} rows after dedup on YT_ID")

    print(f"\n[3/4] LEFT JOIN feed ⊳ tags on YT_ID")
    enriched = feed.merge(tags, on="YT_ID", how="left")
    n_with_tags    = enriched["tags"].notna().sum()
    n_without_tags = enriched["tags"].isna().sum()
    print(f"      videos with tags:    {n_with_tags:>6,}  ({100*n_with_tags/len(enriched):.1f}%)")
    print(f"      videos without tags: {n_without_tags:>6,}  ({100*n_without_tags/len(enriched):.1f}%)")

    # Fill NaN with empty string so Stage A doesn't crash
    enriched["tags"] = enriched["tags"].fillna("")

    # Quick stats on tag length
    tag_lens = enriched.loc[enriched["tags"] != "", "tags"].str.len()
    if len(tag_lens):
        print(f"      tag string length: median={int(tag_lens.median())},  "
              f"p90={int(tag_lens.quantile(0.9))},  max={int(tag_lens.max())}")
    tag_counts = enriched.loc[enriched["tags"] != "", "tags"].str.count(",") + 1
    if len(tag_counts):
        print(f"      tags per video:    median={int(tag_counts.median())},  "
              f"p90={int(tag_counts.quantile(0.9))},  max={int(tag_counts.max())}")

    print(f"\n[4/4] Writing enriched feed: {FEED_OUT}")
    Path(FEED_OUT).parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(FEED_OUT, index=False, compression="gzip")
    size_mb = Path(FEED_OUT).stat().st_size / 1024 / 1024
    print(f"      wrote {size_mb:.1f} MB, {len(enriched.columns)} columns "
          f"(was {len(feed.columns)})")


if __name__ == "__main__":
    main()
