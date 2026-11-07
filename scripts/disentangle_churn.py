"""Block 1.4 — disentangle the churn signal with live-API availability.

EXPORT 3 shipped with an explicit conflation caveat: the 81.4% "churned_30"
headline mixes (1) search-term decommissioning, (2) top-K eviction, and
(3) genuine deletion/privacy. The YouTube API tells us which videos are gone
NOW — that splits every churn bucket into "scraper lost interest, video alive"
vs "video actually unavailable", and turns the U=94% vs B=62% cohort delta
into an attributable claim.

WAITS FOR INPUT: outputs/video_api.csv (run fetch_video_api.py first; use
--scope feed for the full 21,710 attribution, --scope pool for a quick pass).

Timing caveat (stated in the report): availability is measured at fetch time
(2026), capture ended 2024-04-23 — a video may have died after capture, so
"unavailable now" is an upper bound on deletion-during-capture.

Run from project root:
    .venv_v2/bin/python scripts/disentangle_churn.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--api-csv", default="outputs/video_api.csv")
    p.add_argument("--churn", default="outputs/churn_signal.csv")
    p.add_argument("--out", default="outputs/churn_attribution.csv")
    p.add_argument("--report", default="outputs/stage_e/churn_attribution_report.md")
    return p.parse_args()


def bucket(row) -> str:
    if row["churned_90"]:
        return "churned_90"
    if row["churned_30"]:
        return "churned_30_only"
    return "active_to_end"


def main():
    a = parse_args()
    api_path = Path(a.api_csv)
    if not api_path.exists():
        raise SystemExit(
            f"{a.api_csv} not found — this script WAITS for the API fetch.\n"
            "Run first:  YT_API_KEY=... scripts/fetch_video_api.py --scope feed\n"
            "(or --scope pool for a quick 1,099-video pass)")

    api = pd.read_csv(api_path)[["YT_ID", "available", "privacy_status"]]
    churn = pd.read_csv(a.churn)
    df = churn.merge(api, on="YT_ID", how="inner")
    n = len(df)
    print(f"[1/3] Joined: {n:,} videos with both churn signal and API status "
          f"(of {len(churn):,} churn / {len(api):,} API)")
    if n == 0:
        raise SystemExit("Empty join — check the API fetch scope.")

    df["bucket"] = df.apply(bucket, axis=1)
    df["gone_now"] = ~df["available"].astype(bool)

    # --- attribution table ------------------------------------------------- #
    tab = (df.groupby("bucket")
             .agg(n=("YT_ID", "size"), gone_now=("gone_now", "sum"))
             .assign(gone_rate=lambda t: t["gone_now"] / t["n"])
             .reindex(["active_to_end", "churned_30_only", "churned_90"]))
    print("[2/3] Attribution by churn bucket:")
    print(tab.to_string())

    # per-cohort deletion among churned_90 (the U-vs-B question)
    c90 = df[df["bucket"] == "churned_90"]
    coh = (c90.groupby("country_combo")
              .agg(n=("YT_ID", "size"), gone_now=("gone_now", "sum"))
              .assign(gone_rate=lambda t: t["gone_now"] / t["n"])
              .sort_values("gone_rate", ascending=False))

    df[["YT_ID", "country_combo", "bucket", "churn_lag_days", "n_snapshots",
        "available", "privacy_status", "gone_now"]].to_csv(a.out, index=False)

    overall_gone = df["gone_now"].mean()
    # scraper-loss share: churned by STATS-gap but alive now
    churned = df[df["bucket"] != "active_to_end"]
    scraper_loss = 1 - churned["gone_now"].mean() if len(churned) else float("nan")

    print("[3/3] Writing report")
    head = pd.read_csv(api_path, nrows=1)
    fetched = head["fetched_at"].iloc[0] if "fetched_at" in head.columns else "fetch time"
    L = ["# Churn attribution — STATS-gap × live API availability", "",
         f"Scope: {n:,} videos. Availability measured {fetched}; "
         "capture ended 2024-04-23 → 'gone now' is an **upper bound** on "
         "deletion-during-capture.", "",
         "## By churn bucket", "",
         "| bucket | n | gone now | gone rate |", "|---|---:|---:|---:|",
         *[f"| {b} | {int(r['n'])} | {int(r['gone_now'])} | {100*r['gone_rate']:.1f}% |"
           for b, r in tab.iterrows()],
         "",
         f"**Headline:** of the videos the scraper lost (churned_30/90), "
         f"**{100*scraper_loss:.0f}% are still alive** — that share of the old "
         f"81.4% 'churn' was scraper attention, not deletion. Overall "
         f"{100*overall_gone:.1f}% of the scope is gone now.", "",
         "## churned_90 by country_combo (the U-vs-B delta, attributed)", "",
         "| cohort | n | gone now | gone rate |", "|---|---:|---:|---:|",
         *[f"| {c} | {int(r['n'])} | {int(r['gone_now'])} | {100*r['gone_rate']:.1f}% |"
           for c, r in coh.iterrows()],
         "",
         "Full per-video table: `outputs/churn_attribution.csv` "
         "(`gone_now` + `privacy_status`).",
         ]
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text("\n".join(L), encoding="utf-8")
    print(f"      wrote {a.out}\n      wrote {a.report}")


if __name__ == "__main__":
    main()
