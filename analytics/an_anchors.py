"""Anchor × discovery-channel analysis — cross-border media flows.

The anchor (what the embedding looked for) crossed with primary_term_canon
(which search cluster surfaced the video). Off-diagonal mass = content about
one country's protests circulating in another's discovery channel — the
generalisation of the 'UA-Maidan ⟵ lukashenko 18.6%' finding (EXPORT 5).

Run:  .venv_v2/bin/python analytics/an_anchors.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.lib import load_master, md_table, provenance, write_report  # noqa: E402

NAME = "anchors"

# which discovery clusters are 'expected' per anchor
EXPECTED = {
    "BY-2020-protest": {"lukashenko", "belarus"},
    "RU-Navalny": {"navalny", "putin", "russia"},
    "RU-antiwar-2022": {"putin", "russia", "navalny", "ukraine"},
    "RU-mobilisation-2022": {"putin", "russia", "navalny", "ukraine"},
    "UA-Maidan-2014": {"ukraine"},
    "UA-current-protest": {"ukraine"},
    "general-protest-action": {"lukashenko", "belarus", "navalny", "putin",
                               "russia", "ukraine"},
}


def crosstab(df: pd.DataFrame) -> pd.DataFrame:
    ct = pd.crosstab(df["primary_anchor"], df["primary_term_canon"],
                     normalize="index").round(3)
    return ct


def run(m: pd.DataFrame):
    pool = m[m["in_pool"]].dropna(subset=["primary_term_canon"])
    gated = pool[pool["in_gated_index"]]

    anomalies = []
    ct = crosstab(gated)
    for anchor in ct.index:
        for term in ct.columns:
            share = ct.loc[anchor, term]
            if share >= 0.10 and term not in EXPECTED.get(anchor, set()):
                n = int(((gated["primary_anchor"] == anchor)
                         & (gated["primary_term_canon"] == term)).sum())
                anomalies.append({"anchor": anchor, "discovery_term": term,
                                  "share": share, "n": n})
    an = pd.DataFrame(anomalies).sort_values("share", ascending=False) \
        if anomalies else pd.DataFrame(columns=["anchor", "discovery_term",
                                                "share", "n"])

    L = ["# Anchors × discovery channels — cross-border flows", "",
         f"Gated index, {len(gated)} videos with a primary discovery term.", "",
         "## Row-normalised anchor × term shares (gated index)", "",
         *md_table(ct.reset_index()), "",
         "## Off-diagonal anomalies (≥10% from an unexpected cluster)", "",
         *(md_table(an) if len(an) else ["(none at the 10% threshold)"]), "",
         "Each anomaly row = candidate cross-border circulation pattern; "
         "qualitatively check 5–10 videos before claiming "
         "(slice: `analytics/slice.py --where \"in_gated_index and "
         "primary_anchor=='<a>' and primary_term_canon=='<t>'\"`).", "",
         provenance()]
    path = write_report(NAME, L)
    return path, (f"{len(an)} off-diagonal anomalies ≥10% in the gated index")


if __name__ == "__main__":
    p, s = run(load_master())
    print(f"wrote {p} — {s}")
