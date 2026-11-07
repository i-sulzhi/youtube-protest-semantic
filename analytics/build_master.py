"""Build the master analytical dataset — ONE row per feed video, everything joined.

The canonical input for every analytical task. Joins, with explicit prefixes
where source tables collide on column names:

  feed            v2_feed_ready.csv.gz       (text flags, country, publish date)
  engagement      engagement_features.csv    (views, velocity, z-scores)
  churn           churn_signal.csv           (churn_ prefix for first/last_seen)
  search          search_features.csv        (search_ prefix for rank cols)
  hypergraph      hypergraph/vertex_stats.csv (hyper_ prefix)
  static flags    static_flags.csv           (topics, captions, license …)
  distilled gate  distilled_relevance_feed.csv
  pool/Stage E    protest_index*.csv + relevance JSONLs (pool rows only)
  channels        channel_features.csv        (pool rows only)
  events          event_features.csv          (pool rows only)
  gold            coding_gold_v2.csv if present, else coding_layer2.csv
  modalities      stage_f/modality_sets.csv if present

Output: outputs/analytics/master.csv.gz + a coverage inventory printed.

Run from project root:
    .venv_v2/bin/python analytics/build_master.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.lib import MASTER, OUT, REPO  # noqa: E402

O = REPO / "outputs"


def _merge(base: pd.DataFrame, path: Path, cols: dict[str, str] | list[str],
           how: str = "left") -> pd.DataFrame:
    """Merge selected columns; dict = {src: renamed}."""
    if not path.exists():
        print(f"      ⚠ skip (missing): {path.relative_to(REPO)}")
        return base
    if isinstance(cols, dict):
        df = pd.read_csv(path, usecols=["YT_ID"] + list(cols)).rename(columns=cols)
    else:
        df = pd.read_csv(path, usecols=["YT_ID"] + cols)
    return base.merge(df.drop_duplicates("YT_ID"), on="YT_ID", how=how)


def main():
    print("[1/4] Feed base …")
    m = pd.read_csv(O / "v2_feed_ready.csv.gz",
                    usecols=["YT_ID", "PUBLISHED_AT", "DEFAULT_AUDIO_LANG",
                             "dur_sec", "TITLE", "meaningful_len",
                             "protest_anywhere", "protest_in_title",
                             "protest_in_desc", "country_combo", "n_urls"])
    m["publish_year"] = pd.to_datetime(m["PUBLISHED_AT"], errors="coerce",
                                       utc=True).dt.year

    print("[2/4] Corpus-wide features …")
    m = _merge(m, O / "engagement_features.csv",
               ["n_snapshots", "views_total", "views_d7", "velocity_d7",
                "velocity_d7_z", "velocity_d30_z", "like_rate", "comment_rate"])
    m = _merge(m, O / "churn_signal.csv",
               {"first_seen": "churn_first_seen", "last_seen": "churn_last_seen",
                "churn_lag_days": "churn_lag_days",
                "churned_30": "churned_30", "churned_90": "churned_90"})
    m = _merge(m, O / "search_features.csv",
               {"best_rank": "search_best_rank", "median_rank": "search_median_rank",
                "n_search_terms_canon": "n_search_terms_canon",
                "visibility_days_top10": "visibility_days_top10",
                "n_top10_events": "n_top10_events",
                "primary_term_canon": "primary_term_canon"})
    m = _merge(m, O / "hypergraph" / "vertex_stats.csv",
               {"hyperedge_degree": "hyper_degree", "unique_terms": "hyper_unique_terms",
                "broker_score": "broker_score", "best_rank": "hyper_best_rank"})
    static = O / "static_flags.csv"
    if static.exists():
        st = pd.read_csv(static).drop(columns=["default_lang"], errors="ignore")
        m = m.merge(st.drop_duplicates("YT_ID"), on="YT_ID", how="left")
    m = _merge(m, O / "trajectory_features.csv",
               ["burst_ratio", "t50_days", "growth_after_d30", "revival",
                "revival_gap_days", "rank_slope", "rank_volatility"])
    m = _merge(m, O / "distilled_relevance_feed.csv",
               ["distilled_label", "p_direct", "p_indirect", "p_absent"])

    print("[3/4] Pool / Stage E layers (NaN outside the 1,099 pool) …")
    m = _merge(m, O / "stage_e" / "protest_index.csv",
               ["primary_anchor", "n_anchors", "sim_agg", "composite_score", "rank"])
    m = _merge(m, O / "stage_e" / "protest_index_scored.csv",
               ["relevance_llm", "relevance_conf"])
    gated = set(pd.read_csv(O / "stage_e" / "protest_index_gated.csv",
                            usecols=["YT_ID"])["YT_ID"])
    m["in_pool"] = m["primary_anchor"].notna()
    m["in_gated_index"] = m["YT_ID"].isin(gated)
    m = _merge(m, O / "channel_features.csv",
               ["channel_proxy", "channel_source", "channel_n_pool",
                "channel_relevant_rate", "channel_relevant_rate_loo"])
    m = _merge(m, O / "event_features.csv",
               ["days_to_event_any", "days_to_event_anchor",
                "event_window_7", "event_window_30"])

    gold_path = (REPO / "mini_study" / "coding_gold_v2.csv")
    if not gold_path.exists():
        gold_path = REPO / "mini_study" / "coding_layer2.csv"
    gold = pd.read_csv(gold_path)
    gcols = {"protest_relevance": "gold_label"}
    if "round" in gold.columns:
        gcols["round"] = "gold_round"
    gold = gold.rename(columns={"yt_id": "YT_ID", **gcols})
    m = m.merge(gold[["YT_ID"] + list(gcols.values())].drop_duplicates("YT_ID"),
                on="YT_ID", how="left")

    mod = O / "stage_f" / "modality_sets.csv"
    if mod.exists():
        ms = pd.read_csv(mod).rename(columns={
            "semantic": "mod_semantic", "hypergraph": "mod_hypergraph",
            "channel": "mod_channel"})
        m = m.merge(ms[["YT_ID", "mod_semantic", "mod_hypergraph", "mod_channel"]],
                    on="YT_ID", how="left")
        for c in ["mod_semantic", "mod_hypergraph", "mod_channel"]:
            m[c] = m[c].fillna(False)

    print("[4/4] Write + inventory …")
    assert m["YT_ID"].is_unique and len(m) == 21710, \
        f"master integrity broken: {len(m)} rows, unique={m['YT_ID'].is_unique}"
    OUT.mkdir(parents=True, exist_ok=True)
    m.to_csv(MASTER, index=False, compression="gzip")
    print(f"      wrote {MASTER}: {len(m):,} rows × {len(m.columns)} cols")
    cov = {
        "in_pool": int(m["in_pool"].sum()),
        "in_gated_index": int(m["in_gated_index"].sum()),
        "relevance_llm": int(m["relevance_llm"].notna().sum()),
        "gold_label": int(m["gold_label"].notna().sum()),
        "channel_proxy": int(m["channel_proxy"].notna().sum()),
        "distilled_label": int(m["distilled_label"].notna().sum())
        if "distilled_label" in m else 0,
    }
    print("      coverage: " + ", ".join(f"{k}={v:,}" for k, v in cov.items()))


if __name__ == "__main__":
    main()
