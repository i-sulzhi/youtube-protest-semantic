"""Block 4.1 — backfill metadata for the 261K Politics videos without snapshots.

The corpus funnel (ARCHITECTURE §2): 282,809 Politics-topic videos discovered,
only 21,710 (7.7%) metadata-captured; 2022 — the antiwar/mobilisation year —
covered at 1.6%. This fetches title/description/channel via the API for the
missing 261,099, prioritising publish-years 2020–2022 (the protest waves).

Quota: 261,099 ids ≈ 5,222 requests ≈ 5,222 units — UNDER one daily quota
(10,000). Checkpointed: interrupt/resume anytime; --quota-budget caps a run.
Bonus: ids the API no longer returns measure pre-2024 survivorship directly.

WAITS FOR INPUT: the YT_API_KEY env var. `--dry-run` works without it
(builds + caches the prioritised id list from MariaDB).

Run from project root (MariaDB up):
    .venv_v2/bin/python scripts/fetch_metadata_bulk.py --dry-run
    YT_API_KEY=... .venv_v2/bin/python scripts/fetch_metadata_bulk.py --quota-budget 5000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from yt_api import BATCH, fetch_videos, load_checkpoint, require_key  # noqa: E402

POLITICS = "https://en.wikipedia.org/wiki/Politics"
PRIORITY_YEARS = [2022, 2021, 2020, 2023, 2019, 2024]  # protest waves first

SQL = f"""
SELECT v.YT_ID, YEAR(v.PUBLISHED_AT) AS yr
FROM VIDEOS v
JOIN VID_TOPICS vt ON vt.YT_ID = v.YT_ID
JOIN TOPICS t ON t.id = vt.TOPIC_ID
LEFT JOIN VIDEO_METADATA vm ON vm.YT_ID = v.YT_ID
WHERE t.TOPIC = '{POLITICS}' AND vm.YT_ID IS NULL
GROUP BY v.YT_ID, yr
"""


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--ids-cache", default="outputs/missing_politics_ids.csv")
    p.add_argument("--checkpoint", default="outputs/metadata_bulk_checkpoint.jsonl")
    p.add_argument("--out", default="outputs/metadata_bulk.csv")
    p.add_argument("--quota-budget", type=int, default=9000,
                   help="max requests this run (daily quota is 10,000)")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def build_id_list(cache: Path) -> pd.DataFrame:
    if cache.exists():
        ids = pd.read_csv(cache)
        print(f"[1/3] Cached id list: {len(ids):,} ids ({cache})")
        return ids
    import pymysql
    print("[1/3] Building prioritised id list from MariaDB …")
    conn = pymysql.connect(user="sulzhytski", unix_socket="/tmp/mysql.sock",
                           database="metadata", charset="utf8mb4")
    try:
        ids = pd.read_sql(SQL, conn)
    finally:
        conn.close()
    order = {y: i for i, y in enumerate(PRIORITY_YEARS)}
    ids["prio"] = ids["yr"].map(order).fillna(99)
    ids = ids.sort_values(["prio", "yr"]).drop(columns="prio")
    cache.parent.mkdir(parents=True, exist_ok=True)
    ids.to_csv(cache, index=False)
    print(f"      {len(ids):,} missing-metadata Politics ids "
          f"(by year: {ids['yr'].value_counts().sort_index().to_dict()})")
    return ids


def main():
    a = parse_args()
    ids_df = build_id_list(Path(a.ids_cache))
    ids = ids_df["YT_ID"].tolist()
    n_req = (len(ids) + BATCH - 1) // BATCH
    done = load_checkpoint(Path(a.checkpoint))
    print(f"[2/3] {len(ids):,} ids ≈ {n_req:,} requests total; "
          f"{len(done):,} already checkpointed; priority order: "
          f"{PRIORITY_YEARS}")
    if a.dry_run:
        print("      dry-run: OK, nothing fetched")
        return

    key = require_key()
    done = fetch_videos(ids, key, Path(a.checkpoint),
                        parts="snippet,status",
                        quota_budget=a.quota_budget)

    recs = [done[i] for i in ids if i in done]
    df = pd.DataFrame(recs).rename(columns={"yt_id": "YT_ID"})
    df.to_csv(a.out, index=False)
    n_gone = int((~df["found"].astype(bool)).sum()) if len(df) else 0
    print(f"[3/3] wrote {a.out}: {len(df):,} rows "
          f"({n_gone:,} no longer on YouTube = pre-2024 survivorship measure)")
    if len(df) < len(ids):
        print(f"      {len(ids)-len(df):,} remaining — rerun tomorrow "
              "(checkpoint resumes)")
    print("\nNext: extend the feed with the fetched titles/descriptions, embed "
          "(Stage A), pre-gate with the distilled classifier "
          "(train_distilled_gate.py), LLM-gate only the top.")


if __name__ == "__main__":
    main()
