"""Country-cohort analysis — how the pipeline treats B/U/R content.

Per country_combo: feed→pool→gated funnel, gate-survival, engagement,
churn — the quantitative backbone for any claim about national asymmetries
(Belarus-centric discovery, U-vs-B churn delta, …).

Run:  .venv_v2/bin/python analytics/an_cohorts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.lib import load_master, md_table, provenance, write_report  # noqa: E402

NAME = "cohorts"


def run(m: pd.DataFrame):
    rows = []
    for c, grp in m.groupby("country_combo"):
        pool = grp[grp["in_pool"]]
        gated = grp[grp["in_gated_index"]]
        rows.append({
            "cohort": c,
            "feed_n": len(grp),
            "pool_n": len(pool),
            "gated_n": len(gated),
            "pool_rate": len(pool) / len(grp),
            "gate_survival": len(gated) / len(pool) if len(pool) else float("nan"),
            "keyword_rate": grp["protest_anywhere"].mean(),
            "median_views": grp["views_total"].median(),
            "churned_90_rate": grp["churned_90"].mean(),
            "captions_rate": grp.get("has_captions",
                                     pd.Series(dtype=float)).mean(),
        })
    t = (pd.DataFrame(rows)
         .sort_values("gated_n", ascending=False))

    over = (t.assign(gated_share=t["gated_n"] / t["gated_n"].sum(),
                     feed_share=t["feed_n"] / t["feed_n"].sum())
              .assign(rep=lambda d: d["gated_share"] / d["feed_share"]))

    L = ["# Cohorts — the feed→pool→gated funnel by country_combo", "",
         *md_table(t, floatfmt="{:.3f}"), "",
         "## Representation in the index vs the feed", "",
         *md_table(over[["cohort", "feed_share", "gated_share", "rep"]]),
         "",
         "`rep` > 1 = over-represented in the clean index relative to corpus "
         "presence. Read together with the Belarus-centric discovery bias "
         "(63% of search events) and the capture-funnel table before any "
         "substantive claim.", "",
         provenance()]
    path = write_report(NAME, L)
    top = over.loc[over["rep"].idxmax()]
    return path, (f"most over-represented cohort: {top['cohort']} "
                  f"(rep {top['rep']:.1f})")


if __name__ == "__main__":
    p, s = run(load_master())
    print(f"wrote {p} — {s}")
