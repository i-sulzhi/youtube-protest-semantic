"""Block 1.3 — channel as a retrieval expander.

Channels whose pool videos the gate confirms as protest-heavy probably uploaded
MORE protest videos that the embedding retrieval missed (text-poor titles, no
keywords — exactly the codebook's 87%-extratextual blind spot). This pulls the
rest of those channels' videos from the 21,710 feed as gate candidates.

Works NOW with the description-proxy channel (degraded recall: ~57% of the feed
carries a handle) and automatically upgrades when outputs/video_api.csv exists
(--api-csv; full channel coverage incl. text-poor videos — the main payoff).

Output: outputs/channel_expansion_candidates.csv — briefing-ready rows
(`__source__ = channel_expansion`, anchor = the channel's dominant anchor).
Then run the incremental gate exactly like the Task-1 expansions:

    .venv_v2/bin/python scripts/build_relevance_briefings.py \
        --pool outputs/channel_expansion_candidates.csv \
        --exclude-pred-glob 'outputs/stage_e/relevance_pred/*.jsonl' \
        --chunk-offset 15
    # → sub-agents label the new chunks → stage_e_gate.py
    # ⚠ then ALWAYS diff briefing-vs-JSONL (the gate now does this automatically)

Run from project root:
    .venv_v2/bin/python scripts/channel_expand_pool.py
    .venv_v2/bin/python scripts/channel_expand_pool.py --api-csv outputs/video_api.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_channel_features import extract_proxy  # noqa: E402


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--channel-features", default="outputs/channel_features.csv")
    p.add_argument("--feed", default="outputs/v2_feed_ready.csv.gz")
    p.add_argument("--pool", default="outputs/retrieval_nway/all_sources_combined.csv")
    p.add_argument("--gold", default="mini_study/coding_layer2.csv")
    p.add_argument("--api-csv", default=None,
                   help="outputs/video_api.csv with --scope feed for full coverage")
    p.add_argument("--min-rate", type=float, default=0.7,
                   help="min channel_relevant_rate to expand from")
    p.add_argument("--min-n", type=int, default=3,
                   help="min labelled pool videos per channel")
    p.add_argument("--max-new", type=int, default=200)
    p.add_argument("--out", default="outputs/channel_expansion_candidates.csv")
    return p.parse_args()


def main():
    a = parse_args()

    ch = pd.read_csv(a.channel_features)
    rates = (ch.drop_duplicates("channel_proxy")
               .dropna(subset=["channel_proxy"])
               .set_index("channel_proxy")
             [["channel_n_pool", "channel_relevant_rate", "channel_dominant_anchor"]])
    good = rates[(rates["channel_relevant_rate"] >= a.min_rate)
                 & (rates["channel_n_pool"] >= a.min_n)]
    print(f"[1/3] {len(good)} protest-heavy channels "
          f"(rate ≥ {a.min_rate}, n ≥ {a.min_n}) of {len(rates)}")
    if len(good) == 0:
        raise SystemExit("No channels pass the threshold — lower --min-rate/--min-n.")

    feed = pd.read_csv(a.feed)
    if a.api_csv and Path(a.api_csv).exists():
        api = pd.read_csv(a.api_csv)
        amap = api[api["channel_id"].notna()].set_index("YT_ID")["channel_id"]
        feed["channel_key"] = ("yt:" + feed["YT_ID"].map(amap)).where(
            feed["YT_ID"].isin(amap.index))
        src = "api"
    else:
        if a.api_csv:
            print(f"      ⚠ {a.api_csv} not found — using description proxy "
                  "(57% feed coverage; rerun with the API fetch for full power)")
        feed["channel_key"] = feed["DESCRIPTION"].map(extract_proxy)
        src = "proxy"
    cov = feed["channel_key"].notna().mean()
    print(f"[2/3] Feed channel coverage via {src}: {100*cov:.0f}%")

    pool_ids = set(pd.read_csv(a.pool, usecols=["YT_ID"])["YT_ID"])
    gold_ids = set(pd.read_csv(a.gold)["yt_id"])
    cand = feed[feed["channel_key"].isin(good.index)
                & ~feed["YT_ID"].isin(pool_ids | gold_ids)].copy()
    cand = cand.join(good, on="channel_key")
    # most promising first: high-rate channels, then videos with protest keyword
    cand = cand.sort_values(["channel_relevant_rate", "protest_anywhere"],
                            ascending=False).head(a.max_new)

    out = pd.DataFrame({
        "anchor": cand["channel_dominant_anchor"].values,
        "YT_ID": cand["YT_ID"].values,
        "TITLE": cand["TITLE"].values,
        "DESCRIPTION": cand["DESCRIPTION"].values,
        "DEFAULT_AUDIO_LANG": cand["DEFAULT_AUDIO_LANG"].values,
        "PUBLISHED_AT": cand["PUBLISHED_AT"].values,
        "country_combo": cand["country_combo"].values,
        "protest_anywhere": cand["protest_anywhere"].values,
        "protest_in_title": cand["protest_in_title"].values,
        "protest_in_desc": cand["protest_in_desc"].values,
        "dur_sec": cand["dur_sec"].values,
        "feed_text": cand["feed_text"].values,
        "similarity": float("nan"),
        "__source__": "channel_expansion",
        "channel_key": cand["channel_key"].values,
        "channel_relevant_rate": cand["channel_relevant_rate"].values,
    })
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(a.out, index=False)
    print(f"[3/3] wrote {a.out}: {len(out)} candidates from "
          f"{out['channel_key'].nunique()} channels "
          f"(keyword-bearing: {int(out['protest_anywhere'].sum())})")
    print("\nNext: incremental gate (see module docstring), then re-rank + re-gate.")


if __name__ == "__main__":
    main()
