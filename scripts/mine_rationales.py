"""Block 2.6 — mine the gate's rationales for systematic decision modes.

Every one of the 1,099 LLM labels carries a one-sentence rationale. Embedding
and clustering them surfaces the gate's recurring decision patterns ("war
coverage ≠ protest", "memorial content about Navalny", "talk-show about
Lukashenko" …). Clusters that concentrate gold disagreements = systematic
error modes → input for codebook v0.3 and for targeting the next human wave.

Output:
  outputs/stage_e/rationale_clusters.csv   per-video cluster assignment
  outputs/stage_e/rationale_clusters.md    cluster profiles + error modes

Run from project root (~30 s on MPS):
    .venv_v2/bin/python scripts/mine_rationales.py --k 12
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--pred-glob",
                   default="outputs/stage_e/relevance_pred/claude_chunk*.jsonl")
    p.add_argument("--gold", default="mini_study/coding_layer2.csv")
    p.add_argument("--k", type=int, default=12)
    p.add_argument("--model", default="intfloat/multilingual-e5-small")
    p.add_argument("--out-csv", default="outputs/stage_e/rationale_clusters.csv")
    p.add_argument("--report", default="outputs/stage_e/rationale_clusters.md")
    return p.parse_args()


def main():
    a = parse_args()
    rows = []
    for f in sorted(glob.glob(a.pred_glob)):
        for line in open(f, encoding="utf-8"):
            if line.strip():
                rows.append(json.loads(line))
    df = pd.DataFrame(rows).drop_duplicates("yt_id", keep="first")
    df["rationale"] = df["rationale"].fillna("").astype(str)
    print(f"[1/4] {len(df)} rationales "
          f"(median {df['rationale'].str.len().median():.0f} chars)")

    print(f"[2/4] Embedding with {a.model} …")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(a.model)
    emb = model.encode(("query: " + df["rationale"]).tolist(),
                       normalize_embeddings=True, show_progress_bar=False)

    print(f"[3/4] KMeans k={a.k} …")
    from sklearn.cluster import KMeans
    km = KMeans(n_clusters=a.k, n_init=10, random_state=42)
    df["cluster"] = km.fit_predict(emb)

    gold = pd.read_csv(a.gold)[["yt_id", "protest_relevance"]].rename(
        columns={"protest_relevance": "human"})
    df = df.merge(gold, on="yt_id", how="left")
    df["gold_error"] = (df["human"].notna()
                        & (df["human"] != df["protest_relevance"]))

    # nearest rationales to each centroid as the cluster's exemplar
    L = ["# Rationale clusters — the gate's recurring decision modes", "",
         f"{len(df)} rationales, k={a.k} (e5-small embeddings). "
         "`gold_err` = gold items in the cluster the gate got wrong "
         "(systematic-error candidates).", ""]
    summary = []
    for c, grp in df.groupby("cluster"):
        idx = grp.index.values
        d = emb[idx] @ km.cluster_centers_[c]
        exemplars = grp.loc[idx[np.argsort(-d)][:3], "rationale"].tolist()
        n_gold = int(grp["human"].notna().sum())
        n_err = int(grp["gold_error"].sum())
        dist = grp["protest_relevance"].value_counts(normalize=True).round(2)
        summary.append({"cluster": c, "n": len(grp),
                        "top_label": dist.index[0], "top_share": dist.iloc[0],
                        "gold_n": n_gold, "gold_err": n_err})
        L += [f"## Cluster {c} — n={len(grp)}, labels {dist.to_dict()}, "
              f"gold {n_err}/{n_gold} wrong", "",
              *[f"> {e}" for e in exemplars], ""]
    s = pd.DataFrame(summary).sort_values("gold_err", ascending=False)
    worst = s.iloc[0]
    L += ["## Summary (sorted by gold errors)", "",
          "| cluster | n | top label | share | gold n | gold errors |",
          "|---:|---:|---|---:|---:|---:|",
          *[f"| {r.cluster} | {r.n} | {r.top_label} | {r.top_share} "
            f"| {r.gold_n} | {r.gold_err} |" for r in s.itertuples()]]

    df[["yt_id", "protest_relevance", "confidence", "cluster",
        "human", "gold_error"]].to_csv(a.out_csv, index=False)
    Path(a.report).write_text("\n".join(L), encoding="utf-8")
    print(f"[4/4] wrote {a.report}\n      wrote {a.out_csv}")
    print(f"      most error-prone cluster: #{worst.cluster} "
          f"({worst.gold_err}/{worst.gold_n} gold wrong, n={worst.n})")


if __name__ == "__main__":
    main()
