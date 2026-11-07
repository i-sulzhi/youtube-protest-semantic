"""EXPORT trajectory — curve-shape features from STATS + rank dynamics.

Closes DATA_GAPS №9–10. The engagement EXPORT used window aggregates
(views_d7/d30, velocity); this extracts the SHAPE of each video's life:

  From STATS (per-video view time-series):
    burst_ratio       max single-interval daily gain / total views (0–1;
                      1 = everything arrived in one burst)
    t50_days          days from first snapshot to 50% of final observed views
    growth_after_d30  share of views gained after observation day 30
                      (evergreen/archival consumption)
    revival           a second growth peak ≥25% of the first, ≥30 d later
                      (news-cycle resurrection — e.g. old protest footage
                      resurfacing around a new event)
    revival_gap_days  distance between the two peaks (NaN if no revival)

  From SEARCH_RESULTS (per-video rank time-series):
    rank_slope        OLS slope of RANK over days (negative = climbing
                      into visibility; positive = sinking)
    rank_volatility   std of RANK across appearances

Output: outputs/trajectory_features.csv (one row per feed video) — joins into
the master via `make analytics-master`; candidate ranking features for
stage_e_ltr.py.

Run from project root (MariaDB up):
    .venv_v2/bin/python scripts/build_trajectory_features.py
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
import pymysql


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--feed", default="outputs/v2_feed_ready.csv.gz")
    p.add_argument("--out", default="outputs/trajectory_features.csv")
    return p.parse_args()


def stats_shapes(stats: pd.DataFrame) -> pd.DataFrame:
    stats = stats.sort_values(["YT_ID", "DATE"])
    g = stats.groupby("YT_ID", sort=False)
    stats["dv"] = g["VIEW_COUNT"].diff()
    stats["dt"] = g["DATE"].diff().dt.days
    stats["daily_gain"] = (stats["dv"] / stats["dt"]).clip(lower=0)
    stats["day_idx"] = (stats["DATE"] - g["DATE"].transform("min")).dt.days

    rows = []
    for vid, s in stats.groupby("YT_ID", sort=False):
        total = s["VIEW_COUNT"].iloc[-1]
        gains = s.dropna(subset=["daily_gain"])
        rec = {"YT_ID": vid, "burst_ratio": np.nan, "t50_days": np.nan,
               "growth_after_d30": np.nan, "revival": False,
               "revival_gap_days": np.nan}
        if total and total > 0 and len(gains):
            grew = (gains["dv"].clip(lower=0)).sum()
            rec["burst_ratio"] = float(gains["dv"].clip(lower=0).max() / grew) \
                if grew > 0 else np.nan
            # t50: first day_idx where cumulative observed views ≥ 50% of final
            half = s[s["VIEW_COUNT"] >= 0.5 * total]
            rec["t50_days"] = float(half["day_idx"].iloc[0]) if len(half) else np.nan
            late = gains.loc[gains["day_idx"] > 30, "dv"].clip(lower=0).sum()
            rec["growth_after_d30"] = float(late / grew) if grew > 0 else np.nan
            # revival: two separated daily-gain peaks
            if len(gains) >= 3:
                peak1_i = gains["daily_gain"].idxmax()
                peak1_day = gains.loc[peak1_i, "day_idx"]
                peak1 = gains.loc[peak1_i, "daily_gain"]
                far = gains[abs(gains["day_idx"] - peak1_day) >= 30]
                if len(far) and peak1 > 0:
                    peak2 = far["daily_gain"].max()
                    if peak2 >= 0.25 * peak1:
                        rec["revival"] = True
                        rec["revival_gap_days"] = float(
                            abs(far.loc[far["daily_gain"].idxmax(), "day_idx"]
                                - peak1_day))
        rows.append(rec)
    return pd.DataFrame(rows)


def rank_dynamics(sr: pd.DataFrame) -> pd.DataFrame:
    sr["t"] = (sr["DATE"] - sr["DATE"].min()).dt.days.astype(float)
    g = sr.groupby("YT_ID")
    n = g["RANK"].count().rename("n")
    # vectorised OLS slope: cov(t, rank) / var(t) per video
    means = g[["t", "RANK"]].mean().rename(columns={"t": "mt", "RANK": "mr"})
    sr = sr.join(means, on="YT_ID")
    sr["ctr"] = (sr["t"] - sr["mt"]) * (sr["RANK"] - sr["mr"])
    sr["vt"] = (sr["t"] - sr["mt"]) ** 2
    agg = sr.groupby("YT_ID").agg(ctr=("ctr", "sum"), vt=("vt", "sum"),
                                  rank_volatility=("RANK", "std"))
    agg["rank_slope"] = np.where(agg["vt"] > 0, agg["ctr"] / agg["vt"], np.nan)
    out = agg.join(n)
    out.loc[out["n"] < 3, ["rank_slope", "rank_volatility"]] = np.nan
    return out[["rank_slope", "rank_volatility"]].reset_index()


def main():
    a = parse_args()
    ids = pd.read_csv(a.feed, usecols=["YT_ID"])["YT_ID"]
    print(f"[1/4] Feed scope: {len(ids):,} videos")

    conn = pymysql.connect(user="sulzhytski", unix_socket="/tmp/mysql.sock",
                           database="metadata", charset="utf8mb4")
    try:
        with conn.cursor() as c:
            c.execute("CREATE TEMPORARY TABLE scope (YT_ID varchar(11) PRIMARY KEY)")
            c.executemany("INSERT INTO scope VALUES (%s)", ids.tolist())
        conn.commit()
        print("[2/4] STATS time-series …")
        stats = pd.read_sql(
            "SELECT s.YT_ID, s.DATE, s.VIEW_COUNT FROM STATS s "
            "JOIN scope USING (YT_ID)", conn, parse_dates=["DATE"])
        print(f"      {len(stats):,} snapshots")
        print("[3/4] SEARCH_RESULTS rank series …")
        sr = pd.read_sql(
            "SELECT sr.YT_ID, sr.DATE, sr.RANK FROM SEARCH_RESULTS sr "
            "JOIN scope ON scope.YT_ID = sr.YT_ID", conn, parse_dates=["DATE"])
        print(f"      {len(sr):,} rank observations")
    finally:
        conn.close()

    shapes = stats_shapes(stats)
    ranks = rank_dynamics(sr)
    out = (pd.DataFrame({"YT_ID": ids})
           .merge(shapes, on="YT_ID", how="left")
           .merge(ranks, on="YT_ID", how="left"))
    out.to_csv(a.out, index=False)

    print(f"[4/4] wrote {a.out}: {len(out):,} rows")
    d = out.describe()
    print(f"      burst_ratio median {d.loc['50%','burst_ratio']:.2f}; "
          f"t50 median {d.loc['50%','t50_days']:.0f} d; "
          f"revival {int(out['revival'].sum()):,} videos "
          f"({100*out['revival'].mean():.1f}%); "
          f"rank improving (slope<0): "
          f"{int((out['rank_slope'] < 0).sum()):,}")


if __name__ == "__main__":
    main()
