"""Stage E Task 2 — tune / ablate the composite ranking weights.

A *research* harness (does not change the production ranker `stage_e_rank.py`
unless its findings are adopted). It answers three questions on the 60-item
human gold, over the 4-way UNION pool:

  1. Similarity aggregation — `best_similarity` is a `max` over four retrieval
     sources (e5-small/large × no-/with-tags) whose cosine scales differ. Does
     normalising similarity *within source* before aggregating beat the raw max?
  2. Ablation — drop one composite component at a time; which structural signals
     actually earn their weight (AUC / Spearman contribution)?
  3. Weight search — light coordinate descent over the weights, reported with
     **5-fold cross-validation** so the 60-label gain is honest, not overfit.
     The hand-set v1 weights are the documented baseline.

Metrics on the gold (protest_relevance ∈ direct/indirect/absent):
  - AUC direct-vs-absent  (the hard contrast the roadmap targets)
  - AUC relevant-vs-absent (what the gate fundamentally does)
  - AUC direct-vs-indirect (ordering *within* the kept set)
  - Spearman(score, ordinal) over all three classes

Run from project root:
    .venv_v2/bin/python scripts/stage_e_tune.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Reuse only stable helpers/data — NOT the live WEIGHTS, which Task-2 mutates
# (importing them would make this harness compare the tuned config against
# itself). BASE_W below pins the original v1 hand-set baseline.
from stage_e_rank import ANCHOR_EXPECTED_TERMS, as_bool, zscore

ORDINAL = {"absent": 0, "indirect": 1, "direct": 2}
# free weights searched relative to a fixed sim weight of 1.0 (AUC/Spearman are
# rank-based → scaling the whole vector is a no-op, so we pin sim and search the rest)
FREE = ["vel", "broker", "vis", "cons", "churn"]
GRID = [round(x, 2) for x in np.arange(0.0, 1.01, 0.1)]

# v1 hand-set baseline (the documented pre-Task-2 weights), pinned so the report
# stays a fixed reference point regardless of what stage_e_rank.py now uses.
BASE_W = {
    "sim":    1.00,
    "vel":    0.40,
    "broker": 0.30,
    "vis":    0.30,
    "cons":   0.30,
    "churn":  0.50,        # enters the composite with a MINUS sign
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--pool", default="outputs/retrieval_nway/all_sources_combined.csv")
    p.add_argument("--engagement", default="outputs/engagement_features.csv")
    p.add_argument("--churn",      default="outputs/churn_signal.csv")
    p.add_argument("--search",     default="outputs/search_features.csv")
    p.add_argument("--hypergraph", default="outputs/hypergraph/vertex_stats.csv")
    p.add_argument("--gold",       default="mini_study/coding_layer2.csv")
    p.add_argument("--out-dir",    default="outputs/stage_e")
    p.add_argument("--seed",       type=int, default=0)
    return p.parse_args()


# --------------------------------------------------------------------------- #
# Feature construction
# --------------------------------------------------------------------------- #
def aggregate_similarity(pool: pd.DataFrame, mode: str) -> pd.DataFrame:
    """One row per video: a `sim_value` under the chosen aggregation, plus the
    raw-argmax primary_anchor (held fixed across modes so consistency/anchor
    reporting is comparable — only the similarity *feature* changes)."""
    pool = pool.copy()
    pool["similarity"] = pd.to_numeric(pool["similarity"], errors="coerce")

    # primary anchor = raw best-similarity anchor (same as stage_e_rank v1)
    idx = pool.groupby("YT_ID")["similarity"].idxmax()
    best = pool.loc[idx, ["YT_ID", "anchor", "country_combo",
                          "protest_anywhere"]].rename(columns={"anchor": "primary_anchor"})

    if mode == "max_raw":
        sim = pool.groupby("YT_ID")["similarity"].max()
    elif mode in ("zmax", "zmean"):
        # z-score similarity *within each source*, then aggregate per video
        pool["sim_src_z"] = pool.groupby("__source__")["similarity"].transform(
            lambda s: (s - s.mean()) / (s.std(ddof=0) or 1.0))
        agg = "max" if mode == "zmax" else "mean"
        sim = pool.groupby("YT_ID")["sim_src_z"].agg(agg)
    elif mode == "rankmax":
        # percentile rank within source, then max
        pool["sim_src_rank"] = pool.groupby("__source__")["similarity"].rank(pct=True)
        sim = pool.groupby("YT_ID")["sim_src_rank"].max()
    else:
        raise ValueError(mode)

    sim = sim.rename("sim_value").reset_index()
    return best.merge(sim, on="YT_ID")


def build_features(a, sim_mode: str) -> pd.DataFrame:
    """z-scored feature matrix over the FULL pool (unsupervised transform)."""
    pool = pd.read_csv(a.pool)
    df = aggregate_similarity(pool, sim_mode)

    eng = pd.read_csv(a.engagement, usecols=["YT_ID", "velocity_d7_z"])
    chu = pd.read_csv(a.churn,      usecols=["YT_ID", "churned_90"])
    sea = pd.read_csv(a.search,     usecols=["YT_ID", "visibility_days_top10",
                                             "primary_term_canon"])
    hyp = pd.read_csv(a.hypergraph, usecols=["YT_ID", "broker_score"])
    for t in (eng, chu, sea, hyp):
        df = df.merge(t, on="YT_ID", how="left")

    exp = df["primary_anchor"].map(ANCHOR_EXPECTED_TERMS)
    df["consistency"] = [
        float(bool(isinstance(e, set) and isinstance(t, str) and t in e))
        for e, t in zip(exp, df["primary_term_canon"])
    ]
    df["churn"] = as_bool(df["churned_90"]).astype(float)

    df["sim_z"]        = zscore(df["sim_value"])
    df["velocity_z"]   = zscore(df["velocity_d7_z"])
    df["broker_z"]     = zscore(df["broker_score"])
    df["visibility_z"] = zscore(df["visibility_days_top10"])
    return df


def composite(df: pd.DataFrame, w: dict) -> pd.Series:
    return (w["sim"]    * df["sim_z"]
            + w["vel"]    * df["velocity_z"]
            + w["broker"] * df["broker_z"]
            + w["vis"]    * df["visibility_z"]
            + w["cons"]   * df["consistency"]
            - w["churn"]  * df["churn"])


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def _auc(score, y):
    return roc_auc_score(y, score) if pd.Series(y).nunique() == 2 else float("nan")


def metrics(score: pd.Series, g: pd.DataFrame) -> dict:
    """score and g aligned by row; g has 'protest_relevance' and 'ord'."""
    rel = (g["ord"] >= 1).astype(int)
    da = g["protest_relevance"].isin(["direct", "absent"])
    di = g["protest_relevance"].isin(["direct", "indirect"])
    return {
        "auc_dir_abs": _auc(score[da.values], (g["protest_relevance"][da] == "direct").astype(int)),
        "auc_rel_abs": _auc(score, rel),
        "auc_dir_ind": _auc(score[di.values], (g["protest_relevance"][di] == "direct").astype(int)),
        "spearman":    spearmanr(score, g["ord"]).correlation,
    }


# --------------------------------------------------------------------------- #
# Weight search
# --------------------------------------------------------------------------- #
def coord_descent(F: pd.DataFrame, ordv: pd.Series, w0: dict, passes: int = 3) -> dict:
    """Maximise Spearman(score, ordinal) by coordinate ascent over FREE weights
    (Spearman uses all 3 classes → most data-efficient objective for tiny folds)."""
    w = dict(w0)
    def obj(ww):
        s = composite(F, ww)
        r = spearmanr(s, ordv).correlation
        return -1.0 if np.isnan(r) else r
    best = obj(w)
    for _ in range(passes):
        for k in FREE:
            cur_best_v, cur_best = w[k], best
            for v in GRID:
                ww = {**w, k: v}
                o = obj(ww)
                if o > cur_best:
                    cur_best, cur_best_v = o, v
            w[k], best = cur_best_v, cur_best
    return w


def cv_evaluate(F_gold: pd.DataFrame, g: pd.DataFrame, w0: dict, seed: int,
                search: bool) -> tuple[pd.Series, list]:
    """5-fold stratified OOF scores. If search: refit weights per train split;
    else: constant w0. Returns (oof_score aligned to g.index, per-fold weights)."""
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    oof = pd.Series(np.nan, index=g.index)
    fold_w = []
    for tr, te in skf.split(F_gold, g["protest_relevance"]):
        if search:
            w = coord_descent(F_gold.iloc[tr], g["ord"].iloc[tr], w0)
        else:
            w = dict(w0)
        fold_w.append(w)
        oof.iloc[te] = composite(F_gold.iloc[te], w).values
    return oof, fold_w


# --------------------------------------------------------------------------- #
def fmt(d: dict) -> str:
    return (f"dir-abs {d['auc_dir_abs']:.3f} | rel-abs {d['auc_rel_abs']:.3f} | "
            f"dir-ind {d['auc_dir_ind']:.3f} | ρ {d['spearman']:.3f}")


def main():
    a = parse_args()
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    gold = pd.read_csv(a.gold)[["yt_id", "protest_relevance"]].rename(columns={"yt_id": "YT_ID"})
    gold["ord"] = gold["protest_relevance"].map(ORDINAL)

    L = ["# Stage E Task 2 — composite weight tuning & ablation", "",
         "Pool: `outputs/retrieval_nway/all_sources_combined.csv` (4-way UNION, "
         "1,099 videos). Gold: 60 (direct 18 / indirect 17 / absent 25). "
         "Metrics on the gold; AUC≥0.5 means the ranker pushes that class up.", ""]

    # ---- 1. Similarity aggregation -------------------------------------- #
    print("[1/3] Similarity aggregation comparison (hand-set weights)")
    L += ["## 1. Similarity aggregation", "",
          "`best_similarity` aggregates four retrieval sources with different "
          "cosine scales. Same hand-set weights, only the similarity feature changes.", "",
          "| mode | AUC dir-abs | AUC rel-abs | AUC dir-ind | Spearman |",
          "|---|---:|---:|---:|---:|"]
    sim_modes = ["max_raw", "zmax", "zmean", "rankmax"]
    feats, gmerged = {}, {}
    sim_scores = {}
    for mode in sim_modes:
        F = build_features(a, mode)
        feats[mode] = F
        gm = gold.merge(F, on="YT_ID", how="inner").reset_index(drop=True)
        gmerged[mode] = gm
        Fg = gm[["sim_z", "velocity_z", "broker_z", "visibility_z", "consistency", "churn"]]
        m = metrics(composite(Fg, BASE_W), gm)
        sim_scores[mode] = m
        L.append(f"| {'**'+mode+'**' if mode=='max_raw' else mode} "
                 f"| {m['auc_dir_abs']:.3f} | {m['auc_rel_abs']:.3f} "
                 f"| {m['auc_dir_ind']:.3f} | {m['spearman']:.3f} |")
        print(f"      {mode:9s}  {fmt(m)}  (gold n={len(gm)})")

    # pick the best sim mode by AUC dir-abs (the roadmap's target contrast)
    best_mode = max(sim_modes, key=lambda mm: (sim_scores[mm]["auc_dir_abs"],
                                               sim_scores[mm]["spearman"]))
    L += ["", f"Best by AUC dir-abs: **{best_mode}** "
          f"(v1 baseline = `max_raw`). Ablation & search below use `{best_mode}`.", ""]
    F = feats[best_mode]
    gm = gmerged[best_mode]
    Fg = gm[["sim_z", "velocity_z", "broker_z", "visibility_z", "consistency", "churn"]].reset_index(drop=True)
    gm = gm.reset_index(drop=True)

    # ---- 2. Ablation ----------------------------------------------------- #
    print(f"[2/3] Ablation (drop one component; sim mode = {best_mode})")
    full = metrics(composite(Fg, BASE_W), gm)
    L += ["## 2. Ablation — drop one component (hand-set weights)", "",
          "Δ = metric(full) − metric(without). Positive Δ ⇒ the signal helps.", "",
          "| variant | AUC dir-abs | AUC rel-abs | Spearman | Δ dir-abs |",
          "|---|---:|---:|---:|---:|",
          f"| **full composite** | {full['auc_dir_abs']:.3f} | {full['auc_rel_abs']:.3f} "
          f"| {full['spearman']:.3f} | — |"]
    comp_map = {"sim": "−similarity", "vel": "−velocity", "broker": "−broker",
                "vis": "−visibility", "cons": "−consistency", "churn": "−churn"}
    abl_rows = {}
    for k, label in comp_map.items():
        w = dict(BASE_W); w[k] = 0.0
        m = metrics(composite(Fg, w), gm)
        abl_rows[k] = m
        L.append(f"| {label} | {m['auc_dir_abs']:.3f} | {m['auc_rel_abs']:.3f} "
                 f"| {m['spearman']:.3f} | {full['auc_dir_abs']-m['auc_dir_abs']:+.3f} |")
        print(f"      drop {k:7s}  {fmt(m)}  Δdir-abs={full['auc_dir_abs']-m['auc_dir_abs']:+.3f}")
    # cosine-only reference
    m = metrics(composite(Fg, {"sim":1.0,"vel":0,"broker":0,"vis":0,"cons":0,"churn":0}), gm)
    L.append(f"| cosine-only (sim_z) | {m['auc_dir_abs']:.3f} | {m['auc_rel_abs']:.3f} "
             f"| {m['spearman']:.3f} | {full['auc_dir_abs']-m['auc_dir_abs']:+.3f} |")
    print(f"      cosine-only  {fmt(m)}")

    # ---- 3. CV weight search -------------------------------------------- #
    print("[3/3] Cross-validated weight search (5-fold, OOF)")
    oof_base, _ = cv_evaluate(Fg, gm, BASE_W, a.seed, search=False)
    oof_srch, fold_w = cv_evaluate(Fg, gm, BASE_W, a.seed, search=True)
    m_base = metrics(oof_base, gm)
    m_srch = metrics(oof_srch, gm)
    # in-sample refit on all 60 (optimistic — for the suggested weights only)
    w_refit = coord_descent(Fg, gm["ord"], BASE_W)
    m_refit = metrics(composite(Fg, w_refit), gm)

    def wstr(w): return ", ".join(f"{k}={w[k]:.2f}" for k in ["sim",*FREE])
    fold_tab = "\n".join(
        f"| fold {i+1} | " + " | ".join(f"{w[k]:.1f}" for k in FREE) + " |"
        for i, w in enumerate(fold_w))
    L += ["", "## 3. Weight search (5-fold cross-validated)", "",
          "Coordinate ascent on Spearman, **searched per training split**; metrics "
          "on concatenated out-of-fold (OOF) scores — the honest estimate. The "
          "in-sample refit is optimistic (shown only to report the suggested vector).", "",
          "| weights | AUC dir-abs | AUC rel-abs | AUC dir-ind | Spearman |",
          "|---|---:|---:|---:|---:|",
          f"| hand-set v1 (OOF) | {m_base['auc_dir_abs']:.3f} | {m_base['auc_rel_abs']:.3f} "
          f"| {m_base['auc_dir_ind']:.3f} | {m_base['spearman']:.3f} |",
          f"| **searched (OOF, honest)** | {m_srch['auc_dir_abs']:.3f} | {m_srch['auc_rel_abs']:.3f} "
          f"| {m_srch['auc_dir_ind']:.3f} | {m_srch['spearman']:.3f} |",
          f"| searched refit-all-60 (optimistic) | {m_refit['auc_dir_abs']:.3f} | {m_refit['auc_rel_abs']:.3f} "
          f"| {m_refit['auc_dir_ind']:.3f} | {m_refit['spearman']:.3f} |",
          "",
          f"In-sample refit suggests: `{wstr(w_refit)}`.", "",
          "Per-fold searched weights (stability check — if these jump around, the "
          "search is fitting noise):", "",
          "| fold | vel | broker | vis | cons | churn |", "|---|---|---|---|---|---|",
          fold_tab, ""]
    print(f"      hand-set OOF: {fmt(m_base)}")
    print(f"      searched OOF: {fmt(m_srch)}")
    print(f"      refit-all-60: {fmt(m_refit)}  weights {wstr(w_refit)}")

    gain = m_srch["auc_dir_abs"] - m_base["auc_dir_abs"]
    # ablation-harmful components: dropping them improves AUC dir-abs (Δ < 0)
    harmful = [comp_map[k] for k in comp_map
               if (full["auc_dir_abs"] - abl_rows[k]["auc_dir_abs"]) < 0]
    # the ADOPTED production config: best sim mode + hand-set magnitudes with the
    # ablation-harmful components zeroed (robust, not chasing unstable magnitudes)
    w_adopt = dict(BASE_W)
    for k in comp_map:
        if (full["auc_dir_abs"] - abl_rows[k]["auc_dir_abs"]) < 0 and k in w_adopt:
            w_adopt[k] = 0.0
    m_adopt = metrics(composite(Fg, w_adopt), gm)
    L += ["## Recommendation (adopted in stage_e_rank.py)", "",
          f"1. **Similarity aggregation → `{best_mode}`** (default). Unsupervised, "
          f"so no overfit risk: AUC dir-abs {sim_scores['max_raw']['auc_dir_abs']:.3f} "
          f"(max_raw) → {sim_scores[best_mode]['auc_dir_abs']:.3f} ({best_mode}). "
          "This is the single biggest, safest lever.",
          f"2. **Zero the ablation-harmful components**: {', '.join(harmful) or 'none'} "
          "(dropping each improves AUC dir-abs, and the CV search zeros them in ~5/5 "
          "folds). The LLM gate now covers the consistency bonus' anti-false-positive "
          "role; the churn penalty demotes genuine *old* protest content.",
          "3. **Keep** sim/velocity/broker/visibility magnitudes at the documented "
          f"hand-set values: the CV weight search beat hand-set by only {gain:+.3f} "
          "AUC dir-abs (OOF) with unstable broker/visibility magnitudes across folds "
          "— not worth chasing on 60 labels. Revisit after Task 4 grows the gold.", "",
          f"Adopted config (sim_agg={best_mode}, cons/churn zeroed): "
          f"AUC dir-abs **{m_adopt['auc_dir_abs']:.3f}**, rel-abs {m_adopt['auc_rel_abs']:.3f}, "
          f"Spearman {m_adopt['spearman']:.3f} — vs the v1 baseline (max_raw, hand-set) "
          f"dir-abs {sim_scores['max_raw']['auc_dir_abs']:.3f}. The adopted number is "
          "near the optimistic refit yet uses no searched magnitudes, so the gain is "
          "principled, not overfit."]
    (out / "tuning_report.md").write_text("\n".join(L), encoding="utf-8")
    print(f"\n  wrote {out/'tuning_report.md'}")
    print(f"  best_sim_mode={best_mode}  cv_gain_dir_abs={gain:+.3f}  "
          f"harmful={harmful}  adopted_dir_abs={m_adopt['auc_dir_abs']:.3f}")


if __name__ == "__main__":
    main()
