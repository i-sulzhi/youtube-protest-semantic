"""Block 3.2 — event-window features from the protest-event calendar.

Computes, per pool video, the distance from PUBLISHED_AT to the nearest known
protest event (`data/event_calendar.csv`):

  * days_to_event_any     — nearest event of any anchor;
  * days_to_event_anchor  — nearest event of the video's own primary_anchor
                            (NaN where the anchor has no calendar events);
  * event_window_7 / _30  — published within ±7/±30 days of an anchor event.

Contemporaneous protest coverage clusters tightly around event dates; archival
/ anniversary content does not. Candidate ranking feature for stage_e_ltr.py —
NOT wired into the production composite until it earns its weight on gold v2.

⚠ Interpretation caveat: the corpus capture window biases publish dates
(ARCHITECTURE §2 funnel table) — event proximity is a *content* signal, not a
sampling-corrected intensity measure.

Run from project root:
    .venv_v2/bin/python scripts/build_event_features.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--index", default="outputs/stage_e/protest_index.csv")
    p.add_argument("--pool", default="outputs/retrieval_nway/all_sources_combined.csv")
    p.add_argument("--calendar", default="data/event_calendar.csv")
    p.add_argument("--out", default="outputs/event_features.csv")
    return p.parse_args()


def main():
    a = parse_args()
    cal = pd.read_csv(a.calendar, parse_dates=["event_date"])
    print(f"[1/3] Calendar: {len(cal)} events, "
          f"{cal['anchor'].nunique()} anchors covered")

    idx = pd.read_csv(a.index, usecols=["YT_ID", "primary_anchor"])
    pub = (pd.read_csv(a.pool, usecols=["YT_ID", "PUBLISHED_AT"])
             .drop_duplicates("YT_ID"))
    df = idx.merge(pub, on="YT_ID", how="left")
    df["pub"] = pd.to_datetime(df["PUBLISHED_AT"], errors="coerce", utc=True
                               ).dt.tz_localize(None)
    n_bad = int(df["pub"].isna().sum())
    print(f"[2/3] {len(df)} pool videos; {n_bad} unparseable publish dates")

    all_dates = cal["event_date"].values.astype("datetime64[D]")
    by_anchor = {k: g["event_date"].values.astype("datetime64[D]")
                 for k, g in cal.groupby("anchor")}

    pubs = df["pub"].values.astype("datetime64[D]")
    df["days_to_event_any"] = np.abs(
        pubs[:, None] - all_dates[None, :]).min(axis=1).astype("timedelta64[D]"
                                                               ).astype(float)
    danch = np.full(len(df), np.nan)
    for k, dates in by_anchor.items():
        m = (df["primary_anchor"] == k).values & ~df["pub"].isna().values
        if m.any():
            danch[m] = np.abs(pubs[m][:, None] - dates[None, :]
                              ).min(axis=1).astype("timedelta64[D]").astype(float)
    df["days_to_event_anchor"] = danch
    df["event_window_7"] = df["days_to_event_anchor"] <= 7
    df["event_window_30"] = df["days_to_event_anchor"] <= 30

    out_cols = ["YT_ID", "primary_anchor", "days_to_event_any",
                "days_to_event_anchor", "event_window_7", "event_window_30"]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    df[out_cols].to_csv(a.out, index=False)
    print(f"[3/3] wrote {a.out}: {len(df)} rows; "
          f"in ±7d window {int(df['event_window_7'].sum())}, "
          f"±30d {int(df['event_window_30'].sum())}; "
          f"median |days_to_anchor_event| = "
          f"{df['days_to_event_anchor'].median():.0f}")


if __name__ == "__main__":
    main()
