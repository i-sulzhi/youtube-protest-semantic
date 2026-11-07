"""Stage E Task 3 — channel-prior features (description-proxy channel).

The corpus has NO channel/uploader field (not in MariaDB, not in the feed, not in
complete_video_info). As a surrogate we derive a *proxy channel* from each video's
DESCRIPTION: the social handle it promotes (Telegram t.me/…, a YouTube channel
URL, or Instagram). A promoted link is an imperfect stand-in for the uploading
channel (a video may link to a donation bot rather than its own channel, and only
~53% of the pool carries any handle) — but it cleanly surfaces the outlets the
codebook flagged as decisive (UNIAN, Belsat, FREEДОМ, Navalny LIVE, …) and lets
us test the channel-prior mechanism.

For each proxy channel we compute, over the **labelled pool** (LLM relevance from
the Stage E gate), the share of its videos that are protest-relevant. Used two
ways here:
  * a per-video **leave-one-out** channel rate → a candidate composite feature
    (LOO so a video never sees its own label);
  * channel-concentration (Gini / HHI) over the gated index → a structural
    finding for Task 5.

Outputs:
  outputs/channel_features.csv         per-video channel proxy + LOO rates
  outputs/stage_e/channel_report.md    coverage, top channels, concentration,
                                       and the gold-validated ranking lift

Run from project root (after the gate has produced protest_index_scored.csv):
    .venv_v2/bin/python scripts/build_channel_features.py
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

# proxy-channel extraction: priority order, first match wins → one key per video
_PATTERNS = [
    ("tg",   re.compile(r"(?:t\.me|telegram\.me)/(?:s/)?([A-Za-z0-9_]{3,})", re.I)),
    ("yt",   re.compile(r"youtube\.com/(channel/[\w-]+|c/[\w.-]+|user/[\w-]+|@[\w.-]+)", re.I)),
    ("ig",   re.compile(r"instagram\.com/([A-Za-z0-9_.]{2,})", re.I)),
]
# generic handles that are NOT channel identity (donation bots, aggregators, apps)
_STOP = {"joinchat", "share", "addstickers", "+", "telegram", "proxy"}


def extract_proxy(desc: str) -> str | None:
    if not isinstance(desc, str):
        return None
    for kind, pat in _PATTERNS:
        m = pat.search(desc)
        if m:
            handle = m.group(1).lower().strip("/")
            tail = handle.split("/")[-1].lstrip("@")
            if tail in _STOP or len(tail) < 3:
                continue
            return f"{kind}:{handle}"
    return None


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--pool",   default="outputs/retrieval_nway/all_sources_combined.csv")
    p.add_argument("--scored", default="outputs/stage_e/protest_index_scored.csv")
    p.add_argument("--gold",   default="mini_study/coding_layer2.csv")
    p.add_argument("--out",    default="outputs/channel_features.csv")
    p.add_argument("--report", default="outputs/stage_e/channel_report.md")
    p.add_argument("--api-csv", default=None,
                   help="outputs/video_api.csv from fetch_video_api.py — use the "
                        "REAL channel (yt:<channelId>) instead of the description "
                        "proxy where available; proxy remains the fallback")
    return p.parse_args()


def zscore(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    sd = s.std(ddof=0)
    return ((s - s.mean()) / sd).fillna(0.0) if sd and not np.isnan(sd) else pd.Series(0.0, index=s.index)


def gini(x: np.ndarray) -> float:
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    if n == 0 or x.sum() == 0:
        return float("nan")
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def auc(score, y):
    y = pd.Series(y)
    return roc_auc_score(y, score) if y.nunique() == 2 else float("nan")


def main():
    a = parse_args()

    # --- 1. channel key per video (API if provided, proxy fallback) -------- #
    pool = pd.read_csv(a.pool).drop_duplicates("YT_ID")[["YT_ID", "DESCRIPTION"]]
    pool["channel_proxy"] = pool["DESCRIPTION"].map(extract_proxy)
    pool["channel_source"] = pool["channel_proxy"].map(
        lambda v: "proxy" if isinstance(v, str) else None)
    if a.api_csv and Path(a.api_csv).exists():
        api = pd.read_csv(a.api_csv)
        api = api[api["channel_id"].notna()][["YT_ID", "channel_id", "channel_title"]]
        amap = api.set_index("YT_ID")
        hit = pool["YT_ID"].isin(amap.index)
        pool.loc[hit, "channel_proxy"] = ("yt:" + pool.loc[hit, "YT_ID"]
                                          .map(amap["channel_id"]))
        pool.loc[hit, "channel_source"] = "api"
        pool["channel_title"] = pool["YT_ID"].map(amap["channel_title"])
        print(f"[0/4] API channels: {int(hit.sum())}/{len(pool)} videos resolved via "
              f"{a.api_csv}; proxy fallback for the rest")
    elif a.api_csv:
        print(f"[0/4] ⚠ {a.api_csv} not found — falling back to description proxy "
              "(run fetch_video_api.py first for real channels)")
    n = len(pool)
    cov = pool["channel_proxy"].notna().sum()
    print(f"[1/4] Channel key: {cov}/{n} ({100*cov/n:.0f}%) videos covered; "
          f"{pool['channel_proxy'].nunique()} distinct channels "
          f"({pool['channel_source'].value_counts().to_dict()})")

    # --- 2. join LLM relevance + composite from the scored index ---------- #
    scored = pd.read_csv(a.scored)[["YT_ID", "relevance_llm", "primary_anchor",
                                    "composite_score"]]
    df = pool.merge(scored, on="YT_ID", how="inner")
    df["is_relevant"] = df["relevance_llm"].isin(["direct", "indirect"]).astype(int)
    df["is_direct"]   = (df["relevance_llm"] == "direct").astype(int)

    # --- 3. per-channel stats + leave-one-out per-video rates ------------- #
    print("[2/4] Per-channel rates (over the labelled pool) + leave-one-out")
    has = df["channel_proxy"].notna()
    grp = df[has].groupby("channel_proxy")
    ch = grp.agg(channel_n_pool=("YT_ID", "size"),
                 n_relevant=("is_relevant", "sum"),
                 n_direct=("is_direct", "sum")).reset_index()
    ch["channel_relevant_rate"] = ch["n_relevant"] / ch["channel_n_pool"]
    ch["channel_direct_rate"]   = ch["n_direct"]   / ch["channel_n_pool"]
    dom = grp["primary_anchor"].agg(lambda s: s.value_counts().idxmax()).rename("channel_dominant_anchor")
    ch = ch.merge(dom, on="channel_proxy")

    df = df.merge(ch, on="channel_proxy", how="left")
    # leave-one-out: defined only where the channel has ≥2 pool videos
    den = df["channel_n_pool"] - 1
    df["channel_relevant_rate_loo"] = np.where(
        den >= 1, (df["n_relevant"] - df["is_relevant"]) / den.replace(0, np.nan), np.nan)
    df["channel_direct_rate_loo"] = np.where(
        den >= 1, (df["n_direct"] - df["is_direct"]) / den.replace(0, np.nan), np.nan)

    out_cols = ["YT_ID", "channel_proxy", "channel_source", "channel_n_pool",
                "channel_relevant_rate", "channel_direct_rate",
                "channel_relevant_rate_loo", "channel_direct_rate_loo",
                "channel_dominant_anchor"]
    if "channel_title" in df.columns:
        out_cols.insert(3, "channel_title")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    df[out_cols].to_csv(a.out, index=False)
    print(f"      wrote {a.out} ({len(df)} rows)")

    # --- 4. validation: does the channel feature lift ranking on the gold? - #
    print("[3/4] Gold validation (composite vs composite + channel LOO)")
    gold = pd.read_csv(a.gold)[["yt_id", "protest_relevance"]].rename(columns={"yt_id": "YT_ID"})
    ordmap = {"absent": 0, "indirect": 1, "direct": 2}
    g = df.merge(gold, on="YT_ID", how="inner").copy()
    g["ord"] = g["protest_relevance"].map(ordmap)
    # channel feature, z-scored over the FULL pool, NaN→0 (neutral)
    df["chan_z"] = zscore(df["channel_relevant_rate_loo"])
    g = g.merge(df[["YT_ID", "chan_z"]], on="YT_ID", how="left")
    g_cov = int(g["channel_relevant_rate_loo"].notna().sum())

    def metrics(score):
        da = g["protest_relevance"].isin(["direct", "absent"])
        return (auc(score[da.values], (g["protest_relevance"][da] == "direct").astype(int)),
                auc(score, (g["ord"] >= 1).astype(int)),
                spearmanr(score, g["ord"]).correlation)

    base = g["composite_score"]
    rows = []
    for w in [0.0, 0.5, 1.0, 1.5, 2.0]:
        s = base + w * g["chan_z"]
        rows.append((w, *metrics(s)))
    best = max(rows, key=lambda r: (r[1] if not np.isnan(r[1]) else -1))

    # --- 5. concentration over the gated index --------------------------- #
    gated = pd.read_csv("outputs/stage_e/protest_index_gated.csv")[["YT_ID"]]
    gd = gated.merge(df[["YT_ID", "channel_proxy"]], on="YT_ID", how="left")
    gcov = gd["channel_proxy"].notna().sum()
    counts = gd["channel_proxy"].value_counts()
    hhi = float(((counts / counts.sum()) ** 2).sum()) if len(counts) else float("nan")
    gini_c = gini(counts.values) if len(counts) else float("nan")

    print("[4/4] Writing report")
    top = ch[ch["channel_n_pool"] >= 3].sort_values(
        ["channel_relevant_rate", "channel_n_pool"], ascending=False).head(15)
    L = ["# Stage E Task 3 — channel prior (description-proxy)", "",
         f"Proxy channel = the Telegram/YouTube/Instagram handle a video's "
         f"DESCRIPTION promotes (imperfect stand-in for the uploader). Coverage: "
         f"**{cov}/{n} = {100*cov/n:.0f}%** of the pool; {pool['channel_proxy'].nunique()} "
         f"distinct proxies; {int((ch['channel_n_pool']>=2).sum())} channels with ≥2 "
         f"pool videos (covering {int(ch.loc[ch['channel_n_pool']>=2,'channel_n_pool'].sum())} videos).", "",
         "## Top proxy channels by protest-relevant rate (≥3 pool videos)", "",
         "| proxy channel | n | relevant% | direct% | dominant anchor |",
         "|---|---:|---:|---:|---|"]
    for _, r in top.iterrows():
        L.append(f"| `{r['channel_proxy']}` | {int(r['channel_n_pool'])} | "
                 f"{100*r['channel_relevant_rate']:.0f}% | {100*r['channel_direct_rate']:.0f}% | "
                 f"{r['channel_dominant_anchor']} |")
    L += ["", "## Channel concentration (structural finding for Task 5)", "",
          f"Over the {len(gated)}-video gated index, {gcov} ({100*gcov/len(gated):.0f}%) "
          f"have a proxy channel across {len(counts)} channels.",
          f"- **Gini** (video-count inequality across channels): **{gini_c:.3f}**",
          f"- **HHI** (concentration): **{hhi:.3f}** "
          f"({'concentrated' if hhi>0.15 else 'moderate' if hhi>0.10 else 'diffuse'})",
          f"- top-5 channels = {100*counts.head(5).sum()/counts.sum():.0f}% of proxy-covered survivors", "",
          "## Does the channel feature lift ranking on the gold?", "",
          f"`channel_relevant_rate_loo` (leave-one-out, no self-leak), z-scored, "
          f"added to the v2 composite. Gold items with a defined LOO rate: **{g_cov}/60** "
          f"(the feature is neutral elsewhere). AUC/Spearman on the 60 gold:", "",
          "| + w·channel_z | AUC dir-abs | AUC rel-abs | Spearman |",
          "|---:|---:|---:|---:|"]
    for w, da, ra, rho in rows:
        mark = "**" if w == best[0] and w != 0 else ""
        L.append(f"| {mark}{w:.1f}{mark} | {da:.3f} | {ra:.3f} | {rho:.3f} |")
    lift = best[1] - rows[0][1]
    L += ["",
          f"Best at w={best[0]:.1f}: AUC dir-abs {best[1]:.3f} vs {rows[0][1]:.3f} at w=0 "
          f"(Δ {lift:+.3f}). " +
          ("The channel prior **adds ranking signal** on the gold."
           if lift > 0.01 else
           "No clear lift on the gold at this proxy coverage — the signal is real "
           "(see concentration + top channels) but too sparse on 60 gold items to "
           "confirm a ranking gain. Revisit with API channels (full coverage) or a "
           "larger gold (Task 4)."), "",
          "**Caveat.** Channel rates derive from the LLM gate labels; LOO removes "
          "self-leakage, but the proxy covers ~half the pool and a promoted link is "
          "not always the uploader's own channel. Treat as a lower bound on the true "
          "channel signal."]
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text("\n".join(L), encoding="utf-8")
    print(f"      wrote {a.report}")
    print(f"\n  coverage={100*cov/n:.0f}%  gold_LOO_cov={g_cov}/60  "
          f"Gini={gini_c:.3f} HHI={hhi:.3f}  best_w={best[0]} lift_dir_abs={lift:+.3f}")


if __name__ == "__main__":
    main()
