"""Channel analysis — who publishes the indexed protest content?

Top channels in the gated index, concentration (Gini/HHI), and channel ×
anchor structure. Proxy-resolution now; upgrades automatically when
channel_features.csv is rebuilt with --api-csv (real channels).

Run:  .venv_v2/bin/python analytics/an_channels.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.lib import (gini, hhi, load_master, md_table, provenance,  # noqa: E402
                           write_report)

NAME = "channels"


def run(m: pd.DataFrame):
    g = m[m["in_gated_index"]]
    src = (g["channel_source"].value_counts().to_dict()
           if "channel_source" in g else {})
    cov = g["channel_proxy"].notna().sum()
    counts = g["channel_proxy"].value_counts()

    top = (g.dropna(subset=["channel_proxy"])
            .groupby("channel_proxy")
            .agg(n_gated=("YT_ID", "size"),
                 direct=("relevance_llm", lambda s: (s == "direct").sum()),
                 dom_anchor=("primary_anchor",
                             lambda s: s.value_counts().idxmax()),
                 median_views=("views_total", "median"))
            .sort_values("n_gated", ascending=False).head(15).reset_index())

    # channel × anchor: how many channels serve >1 anchor inside the index?
    ca = (g.dropna(subset=["channel_proxy"])
           .groupby("channel_proxy")["primary_anchor"].nunique())
    multi = int((ca > 1).sum())

    L = ["# Channels — who publishes the indexed protest content?", "",
         f"Gated index: {len(g)} videos; channel key for {cov} "
         f"({100*cov/len(g):.0f}%), source {src}; {len(counts)} channels.", "",
         f"Concentration: Gini **{gini(counts.values):.3f}**, "
         f"HHI **{hhi(counts):.3f}** "
         f"({'concentrated' if hhi(counts) > 0.15 else 'diffuse'}); "
         f"top-5 = {100*counts.head(5).sum()/max(counts.sum(),1):.0f}% of covered.",
         "",
         f"**{multi}/{len(ca)}** covered channels span >1 anchor inside the "
         "index (cross-event outlets — the channel-level analogue of the "
         "hypergraph brokers).", "",
         "## Top channels in the gated index", "",
         *md_table(top, floatfmt="{:,.0f}"), "",
         "Upgrade path: rebuild with API channels "
         "(`make api-video && make channels && make analytics-master`).", "",
         provenance()]
    path = write_report(NAME, L)
    return path, (f"{len(counts)} channels, Gini {gini(counts.values):.2f}, "
                  f"HHI {hhi(counts):.3f}, {multi} multi-anchor")


if __name__ == "__main__":
    p, s = run(load_master())
    print(f"wrote {p} — {s}")
