"""Stage C — quantify polysemy of the «протест» / «protest» tag.

For every video that contains a protest-keyword in title or description,
take its embedding from LanceDB and cluster the embedding space. The
clusters are word-sense induction over the tag: each cluster is a
distinct usage-context.

We expect (from EDA) that clusters will align with country-combo and
historical event windows: BY-2020, RU-antiwar-2022, UA-Maidan, etc.
If they do, that empirically demonstrates polysemy of «протест» across
the corpus.

Output:
  outputs/polysemy/
    cluster_assignments.csv   per-video cluster id + summary fields
    cluster_summary.csv       per-cluster top languages, country combos,
                              year ranges, exemplar titles
"""
from __future__ import annotations

import os, argparse
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd
import lancedb
from sklearn.cluster import KMeans, MiniBatchKMeans


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--lancedb", default="outputs/v2_lancedb")
    p.add_argument("--table",   default="videos")
    p.add_argument("--out-dir", default="outputs/polysemy")
    p.add_argument("--n-clusters", type=int, default=8)
    p.add_argument("--seed",       type=int, default=42)
    return p.parse_args()


def main():
    args = parse_args()
    Path(args.out_dir).mkdir(parents=True, exist_ok=True)

    print(f"[C.1] Loading LanceDB at {args.lancedb}/{args.table}")
    db = lancedb.connect(args.lancedb)
    tbl = db.open_table(args.table)
    print(f"      table size: {len(tbl):,} rows")

    print(f"\n[C.2] Filtering to protest-mentioning videos")
    df = (tbl.search().where("protest_anywhere = True").limit(100000)
          .select(["YT_ID","TITLE","DEFAULT_AUDIO_LANG","PUBLISHED_AT",
                   "country_combo","protest_in_title","protest_in_desc",
                   "vector"])
          .to_pandas())
    print(f"      protest-mentioning videos: {len(df):,}")

    # KMeans on the 1024-dim embeddings
    X = np.vstack([np.asarray(v, dtype=np.float32) for v in df["vector"].values])
    print(f"      embedding matrix shape: {X.shape}")

    print(f"\n[C.3] Running KMeans with k={args.n_clusters}, seed={args.seed}")
    km = KMeans(n_clusters=args.n_clusters, random_state=args.seed, n_init=10)
    df["cluster"] = km.fit_predict(X)

    # Per-cluster summary
    print(f"\n[C.4] Per-cluster summary")
    print(f"      (each cluster = one inferred sense of the protest tag)\n")
    rows = []
    for k in range(args.n_clusters):
        sub = df[df["cluster"] == k]
        years = pd.to_datetime(sub["PUBLISHED_AT"], errors="coerce").dt.year
        langs = sub["DEFAULT_AUDIO_LANG"].fillna("(unset)").value_counts().head(3)
        combos = sub["country_combo"].value_counts().head(3)
        # 5 nearest videos to centroid
        c = km.cluster_centers_[k]
        d = np.linalg.norm(X[df["cluster"] == k].astype(np.float32) - c, axis=1)
        nearest_idx = np.argsort(d)[:5]
        exemplars = sub.iloc[nearest_idx]["TITLE"].tolist()

        print(f"      Cluster {k} (n={len(sub):,}):")
        print(f"        years: {int(years.min()) if len(years.dropna()) else '-'}-"
              f"{int(years.max()) if len(years.dropna()) else '-'}, "
              f"median {int(years.median()) if len(years.dropna()) else '-'}")
        print(f"        languages: {langs.to_dict()}")
        print(f"        country combos: {combos.to_dict()}")
        print(f"        exemplar titles:")
        for t in exemplars:
            print(f"          • {t[:120]}")
        print()

        rows.append({
            "cluster": k,
            "n_videos": len(sub),
            "year_min": int(years.min()) if len(years.dropna()) else None,
            "year_max": int(years.max()) if len(years.dropna()) else None,
            "year_median": int(years.median()) if len(years.dropna()) else None,
            "top_langs": str(langs.to_dict()),
            "top_country_combos": str(combos.to_dict()),
            "exemplar_titles": " | ".join(t[:80] for t in exemplars),
        })

    summary = pd.DataFrame(rows)
    out_summary = os.path.join(args.out_dir, "cluster_summary.csv")
    summary.to_csv(out_summary, index=False)
    print(f"      wrote {out_summary}")

    out_assign = os.path.join(args.out_dir, "cluster_assignments.csv")
    df_save = df.drop(columns=["vector"])
    df_save.to_csv(out_assign, index=False)
    print(f"      wrote {out_assign}")


if __name__ == "__main__":
    main()
