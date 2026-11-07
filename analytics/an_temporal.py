"""Temporal analysis — when was the indexed protest content published?

Monthly publish-date density of the gated index against the protest-event
calendar, plus the capture-corrected yearly view (the honest version: raw
counts are dominated by the Jan–Feb-2024 capture window, ARCHITECTURE §2).

Run:  .venv_v2/bin/python analytics/an_temporal.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.lib import (REPO, capture_weight, load_master, md_table,  # noqa: E402
                           provenance, save_fig, write_report)

NAME = "temporal"


def run(m: pd.DataFrame):
    cal = pd.read_csv(REPO / "data" / "event_calendar.csv",
                      parse_dates=["event_date"])
    g = m[m["in_gated_index"]].copy()
    g["pub"] = pd.to_datetime(g["PUBLISHED_AT"], errors="coerce", utc=True
                              ).dt.tz_localize(None)
    monthly = g.set_index("pub").resample("MS")["YT_ID"].count()

    # capture-corrected yearly intensity (gated index)
    yearly = g.groupby("publish_year")["YT_ID"].count().rename("gated_n").to_frame()
    yearly["weight"] = capture_weight(
        pd.Series(yearly.index, index=yearly.index)).values
    yearly["corrected_n"] = (yearly["gated_n"] * yearly["weight"]).round(0)
    yearly["raw_share"] = (yearly["gated_n"] / yearly["gated_n"].sum())
    yearly["corrected_share"] = (yearly["corrected_n"] / yearly["corrected_n"].sum())

    fig_line = None
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(2, 1, figsize=(10, 7))
        monthly.plot(ax=axes[0], drawstyle="steps-mid")
        for d in cal["event_date"]:
            axes[0].axvline(d, color="crimson", alpha=0.35, lw=1)
        axes[0].set_title("Gated index: publish-month density (red = protest events)")
        axes[0].set_ylabel("videos / month")
        yearly[["raw_share", "corrected_share"]].plot.bar(ax=axes[1])
        axes[1].set_title("Yearly share: raw vs capture-corrected (≈, see caveat)")
        fig.tight_layout()
        fig_line = save_fig(fig, "temporal_density")
        plt.close(fig)
    except Exception as e:  # noqa: BLE001 — figures are optional
        print(f"      (figure skipped: {e})")

    peak_m = monthly.idxmax()
    L = ["# Temporal — when was indexed protest content published?", "",
         f"Gated index: {len(g)} videos, publish range "
         f"{g['pub'].min():%Y-%m} … {g['pub'].max():%Y-%m}; "
         f"peak month **{peak_m:%Y-%m}** ({monthly.max()} videos).", "",
         "## Yearly: raw vs capture-corrected", "",
         *md_table(yearly.reset_index()[["publish_year", "gated_n",
                                         "corrected_n", "raw_share",
                                         "corrected_share"]]),
         "",
         "**Caveat.** Correction = count ÷ per-year capture rate "
         "(`data/capture_rates.csv`); assumes capture ⊥ protest-ness within a "
         "year — survivorship (deleted protest videos) makes corrected values "
         "a LOWER bound for the protest waves.",
         "" if fig_line is None else f"\n![]({fig_line.relative_to(REPO)})", "",
         provenance()]
    path = write_report(NAME, L)
    raw_top = yearly["raw_share"].idxmax()
    cor_top = yearly["corrected_share"].idxmax()
    return path, (f"peak month {peak_m:%Y-%m}; raw share peaks {raw_top}, "
                  f"capture-corrected peaks {cor_top}")


if __name__ == "__main__":
    p, s = run(load_master())
    print(f"wrote {p} — {s}")
