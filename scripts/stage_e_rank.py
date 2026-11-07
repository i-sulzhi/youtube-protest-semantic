"""Stage E v1 — precision/ranking layer over the retrieval candidate pool.

Turns a wide, recall-maximised candidate pool (Stage B/D output) into a
*ranked protest-video index* by fusing the semantic-similarity score with the
structural per-video signals built by the multi-signal EXPORTs (engagement,
search-discovery, hypergraph centrality, churn).

This is the precision counterpart to the recall-oriented 4-way UNION. The
codebook experiment (mini_study/) showed that ~70% of retrieved videos are not
*directly* about protest — Stage E re-orders the pool so that protest-direct
material floats to the top, and flags topic-noise / dead videos.

v1 scope (deliberately simple):
  * No learned weights — the 60-item human gold is too small to fit on.
    The composite is a transparent, documented z-scored weighted sum.
  * No LLM relevance gate yet — that is the next increment. v1 instead *tests*
    whether the structural composite already separates protest-direct from
    topic-absent on the human gold, beating raw cosine similarity.

Inputs (all keyed on YT_ID over the same 21,710 v2 subset):
  --pool      retrieval pool with columns [anchor, YT_ID, similarity, TITLE, ...]
              default: outputs/retrieval_e5large/topk_per_anchor.csv (496 videos)
  outputs/engagement_features.csv      velocity_d7_z, views_total
  outputs/churn_signal.csv             churned_90, churn_lag_days
  outputs/search_features.csv          visibility_days_top10, primary_term_canon
  outputs/hypergraph/vertex_stats.csv  broker_score, unique_terms, hyperedge_degree
  --gold      human protest_relevance labels for validation
              default: mini_study/coding_layer2.csv

Outputs:
  outputs/stage_e/protest_index.csv     ranked index, one row per video
  outputs/stage_e/validation_report.md  AUC / rank-separation vs the human gold

Run from project root:
    .venv_v2/bin/python scripts/stage_e_rank.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

# --- Composite weights (v2, Task-2 tuned — see outputs/stage_e/tuning_report.md)
# Each z_* component is z-scored within the pool before weighting; consistency
# and churn are bounded 0/1 flags added raw. Tuned with scripts/stage_e_tune.py
# (ablation + 5-fold CV on the 60-item gold over the 4-way UNION pool).
#
# Task-2 findings:
#   * Similarity AGGREGATION matters most. `best_similarity` is a max over four
#     retrieval sources whose cosine scales differ; z-scoring cosine WITHIN each
#     source before the cross-source max (--sim-agg zmax, the new default) lifts
#     AUC(direct-vs-absent) 0.740 -> 0.802. Unsupervised → no overfit risk.
#   * similarity dominates (ablation Δ +0.204); velocity earns its weight
#     (+0.022); broker a little (+0.004); visibility ≈ neutral but kept for the
#     full-pool discovery-prominence rationale.
#   * consistency_bonus and churn_penalty do NOT earn their weight — both are
#     zeroed in ~5/5 CV folds and ablation-negative, so set to 0. The LLM gate
#     now handles the false-positive role the consistency bonus proxied for; and
#     the churn penalty demotes genuine *old* protest content (2020-Belarus etc.
#     churn as much as topic-noise on the gold), which is wrong for this index.
#   * CV weight search beat hand-set by only +0.020 AUC (OOF) with unstable
#     broker/vis magnitudes → keep the documented sim/vel/broker/vis magnitudes
#     rather than chase noise. Revisit after Task 4 enlarges the gold.
# v1 baseline was sim 1.0 / vel 0.4 / broker 0.3 / vis 0.3 / consistency 0.3 /
# churn 0.5 with --sim-agg max_raw (reproducible via those flags).
WEIGHTS = {
    "sim_z":        1.00,   # semantic similarity (zmax-aggregated) — primary signal
    "velocity_z":   0.40,   # engagement velocity, per-cohort z (virality in peer group)
    "broker_z":     0.30,   # hypergraph cross-channel centrality (broker > celebrity)
    "visibility_z": 0.30,   # days the video sat in search top-10 (discovery prominence)
}
CONSISTENCY_BONUS = 0.00    # Task-2: redundant with the LLM gate; zeroed in 5/5 CV folds
CHURN_PENALTY     = 0.00    # Task-2: demotes genuine old protest content; ablation-negative

# Task-3 channel prior — z(channel_relevant_rate) from the description-proxy
# channel (scripts/build_channel_features.py). OFF by default: on the 60 gold it
# lifts AUC dir-abs only +0.020 (best at w=0.5) and the proxy covers ~57% of the
# pool / 16 of 60 gold items — too sparse to reshape the production index on
# (same noise band Task 2 rejected). The qualitative signal is strong (DW, SOTA,
# Belsat, UNIAN, Vot-Tak rank highest). Turn on with `--channel-weight 0.5` once
# API channels give full coverage or Task 4 enlarges the gold.
CHANNEL_WEIGHT = 0.00

# Anchor -> expected canonical discovery term(s), from EXPORT 5 cross-validation
# (RESULTS_LOG: BY-2020 <- lukashenko/belarus 98.9%, RU-Navalny <- navalny 93.6%, ...).
# A video is "consistent" if its primary search-discovery channel is one the
# anchor is expected to draw from — a cheap anti-false-positive signal.
ANCHOR_EXPECTED_TERMS = {
    "BY-2020-protest":        {"lukashenko", "belarus"},
    "RU-Navalny":             {"navalny", "putin"},
    "RU-antiwar-2022":        {"putin", "navalny", "ukraine"},
    "RU-mobilisation-2022":   {"navalny", "ukraine", "putin"},
    "UA-Maidan-2014":         {"ukraine", "lukashenko"},
    "UA-current-protest":     {"ukraine", "belarus"},
    "general-protest-action": {"belarus", "ukraine", "lukashenko", "navalny"},
}


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pool", default="outputs/retrieval_e5large/topk_per_anchor.csv")
    p.add_argument("--engagement", default="outputs/engagement_features.csv")
    p.add_argument("--churn",      default="outputs/churn_signal.csv")
    p.add_argument("--search",     default="outputs/search_features.csv")
    p.add_argument("--hypergraph", default="outputs/hypergraph/vertex_stats.csv")
    p.add_argument("--gold",       default="mini_study/coding_layer2.csv")
    p.add_argument("--out-dir",    default="outputs/stage_e")
    p.add_argument("--sim-agg", default="zmax", choices=["zmax", "max_raw"],
                   help="how to fuse per-source cosine into one similarity feature. "
                        "zmax (default, Task-2): z-score cosine within each retrieval "
                        "source, then take the cross-source max — corrects the "
                        "encoder scale mismatch. max_raw: v1 behaviour (raw max).")
    p.add_argument("--channel-features", default="outputs/channel_features.csv")
    p.add_argument("--channel-weight", type=float, default=CHANNEL_WEIGHT,
                   help="weight on z(channel_relevant_rate) — Task-3 channel prior. "
                        "Default 0 (off); 0.5 is the gold-validated value, enable once "
                        "channel coverage improves (API channels / larger gold).")
    return p.parse_args()


def aggregate_similarity(pool: pd.DataFrame, mode: str) -> pd.Series:
    """One similarity feature value per YT_ID. `zmax` z-scores cosine within each
    `__source__` before the cross-source max so e5-small/large (different cosine
    scales) contribute on equal footing; falls back to a plain max when the pool
    has no `__source__` column (single-source pools)."""
    if mode == "zmax" and "__source__" in pool.columns:
        z = pool.groupby("__source__")["similarity"].transform(
            lambda s: (s - s.mean()) / (s.std(ddof=0) or 1.0))
        return z.groupby(pool["YT_ID"]).max().rename("sim_agg")
    return pool.groupby("YT_ID")["similarity"].max().rename("sim_agg")


def zscore(s: pd.Series) -> pd.Series:
    """Z-score within the pool; NaN -> 0 (cohort/pool average = neutral)."""
    s = pd.to_numeric(s, errors="coerce")
    mu, sd = s.mean(), s.std(ddof=0)
    if not sd or np.isnan(sd):
        return pd.Series(0.0, index=s.index)
    return ((s - mu) / sd).fillna(0.0)


def as_bool(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def main():
    a = parse_args()
    out_dir = Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)

    # --- 1. Collapse the pool to one row per video -------------------------
    print(f"[1/6] Loading candidate pool: {a.pool}")
    pool = pd.read_csv(a.pool)
    pool["similarity"] = pd.to_numeric(pool["similarity"], errors="coerce")
    # the anchor each video matched best, and how many anchors it appears under
    idx = pool.groupby("YT_ID")["similarity"].idxmax()
    best = pool.loc[idx, ["YT_ID", "anchor", "similarity", "TITLE",
                          "country_combo", "protest_anywhere"]].copy()
    best = best.rename(columns={"anchor": "primary_anchor",
                                "similarity": "best_similarity"})
    n_anchors = pool.groupby("YT_ID")["anchor"].nunique().rename("n_anchors")
    df = best.merge(n_anchors, on="YT_ID")
    # similarity feature fed to the composite (Task-2: zmax by default)
    sim_agg = aggregate_similarity(pool, a.sim_agg)
    df = df.merge(sim_agg, on="YT_ID", how="left")
    print(f"      {len(pool):,} pool rows -> {len(df):,} distinct videos "
          f"({df['primary_anchor'].nunique()} anchors); sim_agg={a.sim_agg}")

    # --- 2. Join the structural feature tables -----------------------------
    print("[2/6] Joining EXPORT feature tables on YT_ID")
    eng = pd.read_csv(a.engagement, usecols=["YT_ID", "velocity_d7_z", "views_total"])
    chu = pd.read_csv(a.churn,      usecols=["YT_ID", "churned_90", "churn_lag_days"])
    sea = pd.read_csv(a.search,     usecols=["YT_ID", "visibility_days_top10",
                                             "n_top10_events", "primary_term_canon"])
    hyp = pd.read_csv(a.hypergraph, usecols=["YT_ID", "broker_score", "unique_terms",
                                             "hyperedge_degree"])
    for name, t in [("engagement", eng), ("churn", chu),
                    ("search", sea), ("hypergraph", hyp)]:
        before = len(df)
        df = df.merge(t, on="YT_ID", how="left")
        miss = df[t.columns[1]].isna().sum()
        print(f"      + {name:11s}: {miss} of {before} videos missing this signal")

    # Optional Task-3 channel prior (off unless --channel-weight > 0)
    df["channel_relevant_rate"] = np.nan
    if a.channel_weight and Path(a.channel_features).exists():
        chan = pd.read_csv(a.channel_features, usecols=["YT_ID", "channel_relevant_rate"])
        df = df.drop(columns=["channel_relevant_rate"]).merge(chan, on="YT_ID", how="left")
        print(f"      + channel    : {df['channel_relevant_rate'].isna().sum()} of "
              f"{len(df)} videos missing this signal (weight {a.channel_weight})")

    # --- 3. Anchor <-> discovery-channel consistency -----------------------
    print("[3/6] Computing anchor<->channel consistency")
    exp = df["primary_anchor"].map(ANCHOR_EXPECTED_TERMS)
    df["anchor_channel_consistent"] = [
        bool(isinstance(e, set) and isinstance(t, str) and t in e)
        for e, t in zip(exp, df["primary_term_canon"])
    ]
    print(f"      consistent: {df['anchor_channel_consistent'].sum()} / {len(df)}")

    # --- 4. Composite score ------------------------------------------------
    print("[4/6] Building composite score")
    df["churned_90"] = as_bool(df["churned_90"])
    comp = (
        WEIGHTS["sim_z"]        * zscore(df["sim_agg"])
        + WEIGHTS["velocity_z"]   * zscore(df["velocity_d7_z"])
        + WEIGHTS["broker_z"]     * zscore(df["broker_score"])
        + WEIGHTS["visibility_z"] * zscore(df["visibility_days_top10"])
        + CONSISTENCY_BONUS * df["anchor_channel_consistent"].astype(float)
        - CHURN_PENALTY     * df["churned_90"].astype(float)
        + a.channel_weight  * zscore(df["channel_relevant_rate"])
    )
    df["composite_score"] = comp
    df = df.sort_values("composite_score", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", np.arange(1, len(df) + 1))

    cols = ["rank", "YT_ID", "primary_anchor", "n_anchors", "best_similarity",
            "sim_agg", "composite_score", "velocity_d7_z", "broker_score", "unique_terms",
            "hyperedge_degree", "visibility_days_top10", "n_top10_events",
            "primary_term_canon", "anchor_channel_consistent", "churned_90",
            "views_total", "country_combo", "protest_anywhere", "TITLE"]
    if a.channel_weight:
        cols.insert(cols.index("composite_score") + 1, "channel_relevant_rate")
    index_path = out_dir / "protest_index.csv"
    df[cols].to_csv(index_path, index=False)
    print(f"      wrote {index_path}  ({len(df):,} rows)")

    # --- 5. Validate against the human protest_relevance gold --------------
    print("[5/6] Validating against human gold")
    gold = pd.read_csv(a.gold)[["yt_id", "protest_relevance"]].rename(
        columns={"yt_id": "YT_ID"})
    v = df.merge(gold, on="YT_ID", how="inner")
    n_gold = len(v)
    ordinal = {"absent": 0, "indirect": 1, "direct": 2}
    v["rel_ord"] = v["protest_relevance"].map(ordinal)
    v["relevant"] = (v["rel_ord"] >= 1).astype(int)            # direct|indirect vs absent

    def auc(score, y):
        return roc_auc_score(y, score) if y.nunique() == 2 else float("nan")

    auc_comp = auc(v["composite_score"], v["relevant"])
    auc_sim  = auc(v["best_similarity"], v["relevant"])
    # harder contrast: direct vs absent only (drop indirect)
    da = v[v["protest_relevance"].isin(["direct", "absent"])]
    auc_comp_da = auc(da["composite_score"], (da["protest_relevance"] == "direct").astype(int))
    auc_sim_da  = auc(da["best_similarity"], (da["protest_relevance"] == "direct").astype(int))
    rho, p_rho = spearmanr(v["composite_score"], v["rel_ord"])
    mean_rank = v.groupby("protest_relevance")["rank"].mean().reindex(
        ["direct", "indirect", "absent"])

    # --- 6. Write the report ----------------------------------------------
    print("[6/6] Writing validation report")
    lines = [
        "# Stage E v1 — validation against human protest_relevance gold", "",
        f"Pool: `{a.pool}` — {len(df):,} videos. "
        f"Gold overlap: **{n_gold}** items "
        f"(direct {int((v.protest_relevance=='direct').sum())}, "
        f"indirect {int((v.protest_relevance=='indirect').sum())}, "
        f"absent {int((v.protest_relevance=='absent').sum())}).", "",
        "## Does the structural composite beat raw cosine similarity?", "",
        "AUC for predicting protest-relevant (direct∪indirect vs absent):", "",
        "| Ranker | AUC relevant-vs-absent | AUC direct-vs-absent |",
        "|---|---:|---:|",
        f"| cosine similarity (baseline) | {auc_sim:.3f} | {auc_sim_da:.3f} |",
        f"| **composite (Stage E)** | **{auc_comp:.3f}** | **{auc_comp_da:.3f}** |",
        "",
        f"Spearman(composite, relevance ordinal) = **{rho:.3f}** (p={p_rho:.3f}).", "",
        "## Mean index rank by relevance class (lower = nearer the top)", "",
        "| protest_relevance | n | mean rank |",
        "|---|---:|---:|",
    ]
    for cls in ["direct", "indirect", "absent"]:
        sub = v[v["protest_relevance"] == cls]
        if len(sub):
            lines.append(f"| {cls} | {len(sub)} | {sub['rank'].mean():.0f} |")
    lines += [
        "", "## Composite weights (v1, documented, not learned)", "",
        "```", *[f"{k:14s} {val}" for k, val in WEIGHTS.items()],
        f"consistency_bonus {CONSISTENCY_BONUS}",
        f"churn_penalty     {CHURN_PENALTY}", "```", "",
        "Interpretation: AUC > 0.5 means the ranker pushes protest material above "
        "topic-noise. If composite AUC > similarity AUC, the structural signals add "
        "precision on top of the embedding. This harness is the place to tune weights "
        "and, next, to slot in the LLM relevance gate.",
    ]
    report_path = out_dir / "validation_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n  AUC relevant-vs-absent:  similarity {auc_sim:.3f}  ->  composite {auc_comp:.3f}")
    print(f"  AUC direct-vs-absent:    similarity {auc_sim_da:.3f}  ->  composite {auc_comp_da:.3f}")
    print(f"  Spearman(composite, relevance) = {rho:.3f} (p={p_rho:.3f})")
    print(f"  mean rank  direct={mean_rank['direct']:.0f}  "
          f"indirect={mean_rank['indirect']:.0f}  absent={mean_rank['absent']:.0f}")
    print(f"  wrote {report_path}")


if __name__ == "__main__":
    main()
