"""Derive per-video engagement features from STATS time-series.

Per `docs/EXPORTS_ROADMAP.md` §3 (EXPORT 4). Scoped to the 21,710 v2
feed-ready videos: all of them have ≥1 STATS snapshot (verified 2026-05-21),
giving ~1.6M rows that fit comfortably in pandas.

Output: outputs/engagement_features.csv with one row per v2 video.

Columns (the velocity_z column is the headline Stage E feature — z-scoring
per country_combo prevents a viral RU video from dominating a quiet BY one):

  YT_ID, country_combo, n_snapshots, first_obs, last_obs, days_observed,
  age_at_first_obs_days,
  views_total, views_d7, views_d30,
  velocity_d7, velocity_d30,
  likes_total, comments_total,
  like_rate, comment_rate,
  velocity_d7_z, velocity_d30_z

The roadmap originally proposed a CSV intermediate; with the MariaDB
instance reloaded we pull directly via pymysql. STATS column is `DATE`,
not `SNAPSHOT_DATE` as the roadmap pre-supposed.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pymysql


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--db-user",    default="sulzhytski")
    p.add_argument("--db-name",    default="metadata")
    p.add_argument("--db-socket",  default="/tmp/mysql.sock")
    p.add_argument("--feed",       default="outputs/v2_feed_ready_with_tags.csv.gz")
    p.add_argument("--out",        default="outputs/engagement_features.csv")
    return p.parse_args()


def fetch_stats(args, yt_ids: list[str]) -> pd.DataFrame:
    """Pull STATS rows for the supplied YT_ID list via temp-table join."""
    conn = pymysql.connect(user=args.db_user, database=args.db_name,
                           unix_socket=args.db_socket, charset="utf8mb4")
    with conn.cursor() as cur:
        cur.execute("CREATE TEMPORARY TABLE v2_ids (YT_ID VARCHAR(11) PRIMARY KEY)")
        cur.executemany("INSERT IGNORE INTO v2_ids VALUES (%s)",
                        [(y,) for y in yt_ids])
        cur.execute("""
            SELECT s.YT_ID, s.DATE, s.VIEW_COUNT, s.LIKE_COUNT, s.COMMENT_COUNT
            FROM STATS s JOIN v2_ids v ON s.YT_ID = v.YT_ID
        """)
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=["YT_ID", "DATE", "VIEW_COUNT",
                                      "LIKE_COUNT", "COMMENT_COUNT"])
    df["DATE"] = pd.to_datetime(df["DATE"])
    for col in ("VIEW_COUNT", "LIKE_COUNT", "COMMENT_COUNT"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("int64")
    return df


def cumulative_at_age(g: pd.DataFrame, max_age_days: int) -> float:
    """Largest VIEW_COUNT observed by `max_age_days` after publish; NaN if no
    snapshot fell within the window."""
    in_window = g[g["age_days"] <= max_age_days]
    return float(in_window["VIEW_COUNT"].max()) if len(in_window) else np.nan


def main():
    args = parse_args()

    print(f"[1/4] Loading v2 feed: {args.feed}")
    feed = pd.read_csv(args.feed,
                       usecols=["YT_ID", "PUBLISHED_AT", "country_combo"],
                       parse_dates=["PUBLISHED_AT"])
    feed["country_combo"] = feed["country_combo"].fillna("UNK")
    print(f"      {len(feed):,} videos")

    print(f"\n[2/4] Pulling STATS via MariaDB temp-table join")
    stats = fetch_stats(args, feed["YT_ID"].tolist())
    print(f"      {len(stats):,} stats rows for {stats['YT_ID'].nunique():,} videos")

    print(f"\n[3/4] Computing per-video features")
    merged = stats.merge(feed, on="YT_ID", how="left")
    merged["age_days"] = (merged["DATE"] - merged["PUBLISHED_AT"]).dt.days

    # Aggregate scalars first (vectorised, fast)
    agg = merged.groupby("YT_ID").agg(
        n_snapshots    = ("DATE",         "size"),
        first_obs      = ("DATE",         "min"),
        last_obs       = ("DATE",         "max"),
        first_age_days = ("age_days",     "min"),
        views_total    = ("VIEW_COUNT",   "max"),
        likes_total    = ("LIKE_COUNT",   "max"),
        comments_total = ("COMMENT_COUNT","max"),
    ).reset_index()
    agg["days_observed"] = (agg["last_obs"] - agg["first_obs"]).dt.days

    # views-by-age windows: need filtered max per group
    def windowed_max(window: int) -> pd.Series:
        sub = merged[merged["age_days"] <= window]
        return sub.groupby("YT_ID")["VIEW_COUNT"].max()

    agg["views_d7"]  = agg["YT_ID"].map(windowed_max(7)).astype("Float64")
    agg["views_d30"] = agg["YT_ID"].map(windowed_max(30)).astype("Float64")
    agg["velocity_d7"]  = agg["views_d7"]  / 7
    agg["velocity_d30"] = agg["views_d30"] / 30

    # Engagement rates — guard against div-by-zero
    agg["like_rate"]    = np.where(agg["views_total"] > 0,
                                   agg["likes_total"]    / agg["views_total"], 0.0)
    agg["comment_rate"] = np.where(agg["views_total"] > 0,
                                   agg["comments_total"] / agg["views_total"], 0.0)

    # Re-join country_combo for z-scoring
    agg = agg.merge(feed[["YT_ID", "country_combo"]], on="YT_ID", how="left")

    # z-score velocity within country_combo; NaN-tolerant; one-element groups
    # become 0 (no spread) which is the right default
    def zscore(s: pd.Series) -> pd.Series:
        m, sd = s.mean(), s.std()
        if not sd or np.isnan(sd):
            return pd.Series(0.0, index=s.index)
        return (s - m) / sd

    agg["velocity_d7_z"]  = (agg.groupby("country_combo")["velocity_d7"]
                                .transform(zscore).astype("Float64"))
    agg["velocity_d30_z"] = (agg.groupby("country_combo")["velocity_d30"]
                                .transform(zscore).astype("Float64"))

    # Rename `first_age_days` for clarity
    agg = agg.rename(columns={"first_age_days": "age_at_first_obs_days"})

    out_cols = [
        "YT_ID", "country_combo",
        "n_snapshots", "first_obs", "last_obs", "days_observed",
        "age_at_first_obs_days",
        "views_total", "views_d7", "views_d30",
        "velocity_d7", "velocity_d30",
        "likes_total", "comments_total",
        "like_rate", "comment_rate",
        "velocity_d7_z", "velocity_d30_z",
    ]
    out = agg[out_cols]

    print(f"\n[4/4] Writing {args.out}")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    kb = Path(args.out).stat().st_size / 1024
    print(f"      {len(out):,} rows, {kb:.0f} KB")

    print(f"\nDistribution checks:")
    print(f"  n_snapshots:   median={int(out['n_snapshots'].median())}, "
          f"p90={int(out['n_snapshots'].quantile(0.9))}, max={int(out['n_snapshots'].max())}")
    print(f"  days_observed: median={int(out['days_observed'].median())}, "
          f"p90={int(out['days_observed'].quantile(0.9))}, max={int(out['days_observed'].max())}")
    print(f"  views_total:   median={int(out['views_total'].median()):,}, "
          f"p90={int(out['views_total'].quantile(0.9)):,}, max={int(out['views_total'].max()):,}")
    vd7 = out["velocity_d7"].dropna()
    if len(vd7):
        print(f"  velocity_d7:   median={vd7.median():.1f}, "
              f"p90={vd7.quantile(0.9):.0f}, max={vd7.max():,.0f} "
              f"(based on {len(vd7):,} videos with day-7 coverage)")
    print(f"  d7 coverage:   {out['views_d7'].notna().sum():,} / {len(out):,} "
          f"({100*out['views_d7'].notna().mean():.1f}%)")
    print(f"  d30 coverage:  {out['views_d30'].notna().sum():,} / {len(out):,} "
          f"({100*out['views_d30'].notna().mean():.1f}%)")

    print(f"\nBy country_combo (velocity_d7 z-score sanity — mean ~0, std ~1):")
    sanity = out.groupby("country_combo")["velocity_d7_z"].agg(
        n="size", mean="mean", std="std", min="min", max="max"
    ).round(3)
    print(sanity.to_string())


if __name__ == "__main__":
    main()
