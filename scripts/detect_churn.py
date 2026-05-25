"""Detect privacy-churn from STATS time-series.

Per `docs/EXPORTS_ROADMAP.md` §4 (EXPORT 3). A video is treated as "churned"
when its last STATS snapshot is significantly earlier than the *global* last
observation date for its sampling cohort — meaning the scraper stopped
seeing it, which on YouTube means private / deleted / region-blocked /
copyright-stricken.

Inside `VIDEO_METADATA` every row carries PRIVACY_STATUS='public', so the
within-table signal is zero (verified 2026-05-21). STATS-gap is therefore
the only available churn signal for this corpus.

Scoped to the 21,710 v2 feed-ready videos.

Output: outputs/churn_signal.csv with one row per v2 video, columns:
  YT_ID, country_combo, first_seen, last_seen,
  churn_lag_days,  -- days between last_seen and global_max
  churned_30,      -- bool: churn_lag_days > 30
  churned_90,      -- bool: churn_lag_days > 90 (stricter / fewer false positives)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import pymysql


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--db-user",   default="sulzhytski")
    p.add_argument("--db-name",   default="metadata")
    p.add_argument("--db-socket", default="/tmp/mysql.sock")
    p.add_argument("--feed",      default="outputs/v2_feed_ready_with_tags.csv.gz")
    p.add_argument("--out",       default="outputs/churn_signal.csv")
    return p.parse_args()


def fetch_minmax(args, yt_ids: list[str]) -> pd.DataFrame:
    """Pull per-video min/max snapshot dates from STATS."""
    conn = pymysql.connect(user=args.db_user, database=args.db_name,
                           unix_socket=args.db_socket, charset="utf8mb4")
    with conn.cursor() as cur:
        cur.execute("CREATE TEMPORARY TABLE v2_ids (YT_ID VARCHAR(11) PRIMARY KEY)")
        cur.executemany("INSERT IGNORE INTO v2_ids VALUES (%s)",
                        [(y,) for y in yt_ids])
        cur.execute("""
            SELECT s.YT_ID,
                   MIN(s.DATE) AS first_seen,
                   MAX(s.DATE) AS last_seen,
                   COUNT(*)    AS n_snapshots
            FROM STATS s JOIN v2_ids v ON s.YT_ID = v.YT_ID
            GROUP BY s.YT_ID
        """)
        rows = cur.fetchall()
        cur.execute("SELECT MAX(DATE) FROM STATS")
        (global_max,) = cur.fetchone()
    df = pd.DataFrame(rows, columns=["YT_ID", "first_seen", "last_seen", "n_snapshots"])
    df["first_seen"] = pd.to_datetime(df["first_seen"])
    df["last_seen"]  = pd.to_datetime(df["last_seen"])
    df.attrs["global_max"] = pd.Timestamp(global_max)
    return df


def main():
    args = parse_args()

    print(f"[1/3] Loading v2 feed: {args.feed}")
    feed = pd.read_csv(args.feed,
                       usecols=["YT_ID", "PUBLISHED_AT", "country_combo"],
                       parse_dates=["PUBLISHED_AT"])
    feed["country_combo"] = feed["country_combo"].fillna("UNK")

    print(f"\n[2/3] Pulling per-video min/max snapshot dates")
    obs = fetch_minmax(args, feed["YT_ID"].tolist())
    global_max = obs.attrs["global_max"]
    print(f"      global max snapshot date: {global_max.date()}")
    print(f"      {len(obs):,} videos with STATS coverage")

    out = obs.merge(feed[["YT_ID", "country_combo"]], on="YT_ID", how="right")
    # videos with zero STATS rows would get NaN; in the v2 subset coverage
    # is 100%, but defend anyway
    out["churn_lag_days"] = (global_max - out["last_seen"]).dt.days
    out["churned_30"] = out["churn_lag_days"] > 30
    out["churned_90"] = out["churn_lag_days"] > 90
    out = out[["YT_ID", "country_combo", "first_seen", "last_seen",
               "n_snapshots", "churn_lag_days", "churned_30", "churned_90"]]

    print(f"\n[3/3] Writing {args.out}")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    kb = Path(args.out).stat().st_size / 1024
    print(f"      {len(out):,} rows, {kb:.0f} KB")

    print(f"\nHeadline numbers:")
    n = len(out)
    n30 = int(out["churned_30"].sum())
    n90 = int(out["churned_90"].sum())
    print(f"  total v2 videos:              {n:>6,}")
    print(f"  churned (>30 d lag):          {n30:>6,}  ({100*n30/n:.1f}%)")
    print(f"  churned (>90 d lag, strict):  {n90:>6,}  ({100*n90/n:.1f}%)")
    print(f"  churn_lag_days: median={int(out['churn_lag_days'].median())}, "
          f"p90={int(out['churn_lag_days'].quantile(0.9))}, max={int(out['churn_lag_days'].max())}")

    print(f"\nChurn rate by country_combo (>30 d threshold):")
    by_country = (out.groupby("country_combo")
                     .agg(n_videos=("YT_ID", "size"),
                          n_churned_30=("churned_30", "sum"),
                          n_churned_90=("churned_90", "sum")))
    by_country["rate_30_pct"] = (100 * by_country["n_churned_30"]
                                       / by_country["n_videos"]).round(1)
    by_country["rate_90_pct"] = (100 * by_country["n_churned_90"]
                                       / by_country["n_videos"]).round(1)
    print(by_country.to_string())


if __name__ == "__main__":
    main()
