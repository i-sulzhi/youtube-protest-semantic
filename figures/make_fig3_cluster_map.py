"""Figure 3 — language vs framing (the talk's central thesis).

Two panels:
  (left)  t-SNE 2-D projection of the 2,045 protest-mentioning videos,
          colour = cluster (event/sense), marker = language group.
  (right) 8×8 centroid cosine heatmap with the Belarus-2020 cross-language
          block and the Russian-language block annotated.

Reads embeddings from LanceDB + cluster_assignments + centroid_cosine.csv.

Output: figures/fig3_cluster_map.png
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import lancedb
from sklearn.manifold import TSNE

REPO = Path(__file__).resolve().parent.parent
LANCE = REPO / "outputs" / "v2_lancedb"
CLUSTERS = REPO / "outputs" / "polysemy_e5large" / "cluster_assignments.csv"
CENTROID = REPO / "mini_study" / "centroid_cosine.csv"
OUT = REPO / "figures" / "fig3_cluster_map.png"

CLUSTER_SENSE = {
    0: "BY-2020 (DE)", 1: "Belarus opp (RU)", 2: "Russia/Navalny (EN)",
    3: "BY-2020 (EN)", 4: "War analysis (EN)", 5: "RU/UA war (RU)",
    6: "Belsat opp (BE)", 7: "RU opposition (RU)",
}
# tab10-ish palette
PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
           "#8c564b", "#e377c2", "#7f7f7f"]


def lang_bucket(s):
    if not s or pd.isna(s) or str(s).strip() in ("", "nan"):
        return "unset"
    return str(s).lower().split("-")[0]


def main():
    db = lancedb.connect(str(LANCE))
    tbl = db.open_table("videos_e5large")
    df = (tbl.search().where("protest_anywhere = True").limit(100000)
          .select(["YT_ID", "DEFAULT_AUDIO_LANG", "vector"]).to_pandas())
    cl = pd.read_csv(CLUSTERS, dtype={"YT_ID": str})
    cl["cluster"] = cl["cluster"].astype(int)
    df = df.merge(cl[["YT_ID", "cluster"]], on="YT_ID", how="inner")
    X = np.vstack([np.asarray(v, dtype=np.float32) for v in df["vector"].values])
    df["lang"] = df["DEFAULT_AUDIO_LANG"].apply(lang_bucket)

    print("Running t-SNE on", X.shape, "...")
    xy = TSNE(n_components=2, random_state=42, perplexity=30, init="pca",
              metric="cosine").fit_transform(X)
    df["x"], df["y"] = xy[:, 0], xy[:, 1]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Left: t-SNE coloured by cluster
    for k in sorted(df["cluster"].unique()):
        sub = df[df["cluster"] == k]
        ax1.scatter(sub["x"], sub["y"], s=10, alpha=0.55, color=PALETTE[k % 10],
                    label=f"C{k} {CLUSTER_SENSE.get(k,'')}", edgecolors="none")
    ax1.set_title("t-SNE of 2,045 protest videos — coloured by inferred sense\n"
                  "Belarus-2020 in DE / EN / RU lands in adjacent regions",
                  fontsize=11, loc="left")
    ax1.set_xticks([]); ax1.set_yticks([])
    ax1.legend(loc="upper left", fontsize=7.5, framealpha=0.9, markerscale=1.6)
    for s in ax1.spines.values():
        s.set_visible(False)

    # Right: centroid cosine heatmap
    cm = pd.read_csv(CENTROID, index_col=0)
    short = [f"C{i}" for i in range(len(cm))]
    M = cm.values
    im = ax2.imshow(M, cmap="magma", vmin=0.88, vmax=1.0)
    ax2.set_xticks(range(len(short))); ax2.set_xticklabels(short, fontsize=9)
    ax2.set_yticks(range(len(short)))
    ax2.set_yticklabels([f"C{i} {CLUSTER_SENSE.get(i,'')}" for i in range(len(short))], fontsize=8)
    for i in range(len(short)):
        for j in range(len(short)):
            ax2.text(j, i, f"{M[i,j]:.2f}", ha="center", va="center",
                     color="white" if M[i, j] < 0.96 else "black", fontsize=7)
    ax2.set_title("Centroid cosine — RU-language clusters (C1/C5/C7)\n"
                  "bind tighter (0.97-0.98) than cross-language BY-2020 (0.94)",
                  fontsize=11, loc="left")
    fig.colorbar(im, ax=ax2, fraction=0.046, pad=0.04, label="cosine similarity")

    fig.tight_layout()
    fig.savefig(OUT, dpi=150, bbox_inches="tight")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
