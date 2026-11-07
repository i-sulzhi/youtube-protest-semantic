"""Build the stratified 200-video sample for the AGH mini-study framing pilot.

Preference order:
  1. If `outputs/retrieval_e5large/topk_per_anchor.csv` exists → sample from
     the war/protest-core anchors with stratification by (anchor × language).
     This is the preferred mode because it puts the LLM and the human coder
     on the same videos the talk's empirical claim is built on.
  2. Else if `outputs/polysemy_e5large/cluster_assignments.csv` exists →
     sample from the war/protest-relevant clusters with stratification by
     (cluster × language).
  3. Else → fall back to protest_anywhere=True with stratification by
     (country_combo × language).

Output:
  mini_study/sample.csv — N≈200 rows ready for LLM classification and
  human coding. Columns:
    YT_ID, source (anchor|cluster|protest), strat_bucket, language_norm,
    country_combo, protest_anywhere, TITLE, DESCRIPTION, feed_text, dur_sec,
    PUBLISHED_AT
"""
from __future__ import annotations

import os
import random
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
FEED = REPO / "outputs" / "v2_feed_ready.csv.gz"
RETRIEVAL = REPO / "outputs" / "retrieval_e5large" / "topk_per_anchor.csv"
CLUSTERS = REPO / "outputs" / "polysemy_e5large" / "cluster_assignments.csv"
OUT = REPO / "mini_study" / "sample.csv"

# Core war/protest anchors for the mini-study. Avoid UA-Maidan-2014 (historical,
# capture window biases coverage retrospectively) and Navalny (single-event,
# narrows framing diversity).
CORE_ANCHORS = [
    "BY-2020-protest",
    "RU-antiwar-2022",
    "RU-mobilisation-2022",
    "UA-current-protest",
    "general-protest-action",
]

TARGET_N = 200
SEED = 42


def normalize_language(lang: str) -> str:
    """Map DEFAULT_AUDIO_LANG to a coarse bucket for stratification."""
    if not lang or pd.isna(lang) or str(lang).strip() in ("", "nan", "(unset)"):
        return "unset"
    lang = str(lang).lower().split("-")[0]
    if lang in {"ru"}:
        return "ru"
    if lang in {"uk"}:
        return "uk"
    if lang in {"be"}:
        return "be"
    if lang in {"en"}:
        return "en"
    if lang in {"de"}:
        return "de"
    if lang in {"pl"}:
        return "pl"
    return "other"


def stratified_sample(df: pd.DataFrame, bucket_col: str, n: int, seed: int = SEED) -> pd.DataFrame:
    """Round-robin sampling across buckets, dropping empties along the way."""
    rng = random.Random(seed)
    buckets = {k: df[df[bucket_col] == k] for k in df[bucket_col].unique()}
    # Shuffle each bucket
    for k in list(buckets.keys()):
        idx = list(buckets[k].index)
        rng.shuffle(idx)
        buckets[k] = buckets[k].loc[idx].reset_index(drop=True)
    picked = []
    order = list(buckets.keys())
    rng.shuffle(order)
    cursors = {k: 0 for k in order}
    while len(picked) < n:
        empty = True
        for k in order:
            if cursors[k] < len(buckets[k]):
                picked.append(buckets[k].iloc[cursors[k]])
                cursors[k] += 1
                empty = False
                if len(picked) >= n:
                    break
        if empty:
            break
    return pd.DataFrame(picked).reset_index(drop=True)


def main():
    feed = pd.read_csv(FEED, dtype=str, keep_default_na=False, na_values=[""])
    feed["language_norm"] = feed["DEFAULT_AUDIO_LANG"].apply(normalize_language)
    feed["protest_anywhere"] = feed["protest_anywhere"].astype(str).str.lower() == "true"
    print(f"[load] feed: {len(feed):,} rows  |  languages: {feed['language_norm'].value_counts().to_dict()}")

    if RETRIEVAL.exists():
        print(f"[mode] retrieval — using {RETRIEVAL}")
        ret = pd.read_csv(RETRIEVAL, dtype=str, keep_default_na=False, na_values=[""])
        ret = ret[ret["anchor"].isin(CORE_ANCHORS)].copy()
        # similarity rank within anchor
        ret["rank"] = ret.groupby("anchor").cumcount()
        # join language + country + protest from feed (canonical metadata)
        ret = ret.merge(
            feed[
                [
                    "YT_ID",
                    "language_norm",
                    "country_combo",
                    "protest_anywhere",
                    "TITLE",
                    "DESCRIPTION",
                    "feed_text",
                    "dur_sec",
                    "PUBLISHED_AT",
                ]
            ],
            on="YT_ID",
            how="left",
            suffixes=("_anchor", ""),
        )
        ret["source"] = "anchor"
        ret["strat_bucket"] = ret["anchor"] + "::" + ret["language_norm"]
        # one row per YT_ID (best rank across anchors); keep anchor info on first match
        ret = ret.sort_values("rank").drop_duplicates(subset="YT_ID", keep="first")
        print(f"[mode] retrieval rows after dedup: {len(ret):,}")
        sample = stratified_sample(ret, "strat_bucket", TARGET_N)
    elif CLUSTERS.exists():
        print(f"[mode] cluster — using {CLUSTERS}")
        cl = pd.read_csv(CLUSTERS, dtype=str, keep_default_na=False, na_values=[""])
        merged = feed.merge(cl[["YT_ID", "cluster"]], on="YT_ID", how="inner")
        merged["source"] = "cluster"
        merged["strat_bucket"] = "C" + merged["cluster"].astype(str) + "::" + merged["language_norm"]
        # restrict to protest-mentioning videos (cluster space)
        merged = merged[merged["protest_anywhere"]].copy()
        sample = stratified_sample(merged, "strat_bucket", TARGET_N)
    else:
        print(f"[mode] fallback — protest_anywhere=True × (country_combo × language)")
        sub = feed[feed["protest_anywhere"]].copy()
        sub["source"] = "protest"
        sub["strat_bucket"] = sub["country_combo"] + "::" + sub["language_norm"]
        sample = stratified_sample(sub, "strat_bucket", TARGET_N)

    keep = [
        "YT_ID",
        "source",
        "strat_bucket",
        "language_norm",
        "country_combo",
        "protest_anywhere",
        "TITLE",
        "DESCRIPTION",
        "feed_text",
        "dur_sec",
        "PUBLISHED_AT",
    ]
    if "anchor" in sample.columns:
        keep = ["anchor", "rank", "similarity"] + keep
    sample = sample[[c for c in keep if c in sample.columns]]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(OUT, index=False)
    print(f"\n[done] wrote {OUT}  ({len(sample)} rows)")
    print("\n[strat_bucket counts]")
    print(sample["strat_bucket"].value_counts().to_string())


if __name__ == "__main__":
    main()
