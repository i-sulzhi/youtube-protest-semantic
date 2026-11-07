"""Broker analysis — cross-channel videos × the gated index (EXPORT 7 follow-up).

The hypergraph found 132 videos touching ≥3 canonical discovery clusters
(6 four-term + 1 five-term = the structural brokers). Question: does the
protest index capture them, and are brokers more protest-relevant than the
corpus baseline?

Run:  .venv_v2/bin/python analytics/an_brokers.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.lib import load_master, md_table, provenance, write_report  # noqa: E402

NAME = "brokers"


def run(m: pd.DataFrame):
    m = m.copy()
    m["broker_tier"] = pd.cut(m["hyper_unique_terms"],
                              bins=[0, 1, 2, 6],
                              labels=["1 term", "2 terms", "3+ terms (brokers)"])
    t = (m.groupby("broker_tier", observed=True)
          .agg(n=("YT_ID", "size"),
               in_pool=("in_pool", "sum"),
               in_gated=("in_gated_index", "sum"),
               pool_rate=("in_pool", "mean"),
               gated_rate=("in_gated_index", "mean"),
               keyword_rate=("protest_anywhere", "mean"))
          .reset_index())

    brokers = m[m["hyper_unique_terms"] >= 3]
    bg = brokers[brokers["in_gated_index"]]
    cols = ["YT_ID", "TITLE", "hyper_unique_terms", "hyper_degree",
            "primary_anchor", "relevance_llm", "country_combo"]
    top = (brokers.sort_values(["hyper_unique_terms", "hyper_degree"],
                               ascending=False).head(10)[cols])
    top["TITLE"] = top["TITLE"].str.slice(0, 60)

    base = m["in_gated_index"].mean()
    brate = brokers["in_gated_index"].mean()
    L = ["# Brokers — cross-channel videos × the protest index", "",
         "## Index capture by broker tier", "",
         *md_table(t), "",
         f"Corpus baseline gated-rate {100*base:.1f}% vs brokers (3+ terms) "
         f"**{100*brate:.1f}%** — brokers are "
         f"{'over' if brate > base else 'under'}-represented "
         f"({brate/base:.1f}× the baseline). {len(bg)}/{len(brokers)} brokers "
         "are in the clean index.", "",
         "## Top brokers (by terms, then degree)", "",
         *md_table(top), "",
         "NaN relevance_llm = the broker never entered the retrieval pool — "
         "candidate blind spot of the semantic modality (cf. stage_f "
         "modalities report).", "",
         provenance()]
    path = write_report(NAME, L)
    return path, (f"brokers gated at {100*brate:.0f}% vs baseline "
                  f"{100*base:.1f}%; {len(bg)}/{len(brokers)} in index")


if __name__ == "__main__":
    p, s = run(load_master())
    print(f"wrote {p} — {s}")
