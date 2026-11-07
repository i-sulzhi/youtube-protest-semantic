"""Language-vs-framing test — the talk's central empirical claim (slide 8).

Question: is the multilingual embedding space organised by LANGUAGE or by
political FRAMING/EVENT?

Operationalisations (all reported honestly, whatever the data shows):

  (1) Within-group mean cosine similarity.
      For each grouping variable G ∈ {language, cluster(=event/sense), country_combo},
      compute the mean pairwise cosine similarity of videos that share the same G.
      If within-cluster > within-language, the space tracks framing/event more
      than language.

  (2) Cluster-centroid cosine heatmap.
      Centroid of each of the 8 KMeans senses; pairwise cosine. Test the
      headline claim: the Belarus-2020 clusters in DE / EN / RU sit closer to
      each other than the two Russian-language clusters (C1, C7) sit to each
      other — i.e. shared EVENT beats shared LANGUAGE.

  (3) Nearest-neighbour label concordance.
      For each video, is its nearest neighbour (excl. self) more often the same
      LANGUAGE or the same CLUSTER? A direct, model-free statistic.

Reads embeddings + metadata from LanceDB (videos_e5large) joined to
outputs/polysemy_e5large/cluster_assignments.csv.

Outputs:
  mini_study/language_vs_framing.md           — narrative report with numbers
  mini_study/centroid_cosine.csv              — 8×8 centroid cosine matrix
  figures/data/lang_vs_framing_within.csv     — within-group similarity table
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import lancedb

REPO = Path(__file__).resolve().parent.parent
LANCE = REPO / "outputs" / "v2_lancedb"
CLUSTERS = REPO / "outputs" / "polysemy_e5large" / "cluster_assignments.csv"
OUT_MD = REPO / "mini_study" / "language_vs_framing.md"
OUT_CENTROID = REPO / "mini_study" / "centroid_cosine.csv"
FIG_DATA = REPO / "figures" / "data"

# human-readable cluster sense labels (from Stage C exemplars, see DAY1_INSIGHTS §12.3)
CLUSTER_SENSE = {
    0: "BY-2020 (DE)",
    1: "Belarus opp. (RU)",
    2: "Russia/Navalny (EN)",
    3: "BY-2020 (EN)",
    4: "War analysis (EN/US)",
    5: "RU/UA war commentary (RU)",
    6: "Belsat opp. (BE/RU)",
    7: "RU opposition/anti-war (RU)",
}


def lang_bucket(s):
    if not s or pd.isna(s) or str(s).strip() in ("", "nan", "(unset)"):
        return "unset"
    return str(s).lower().split("-")[0]


def mean_within_group_cosine(X, labels, max_pairs_per_group=20000, seed=42):
    """Mean cosine similarity of pairs sharing a label. X must be L2-normalised."""
    rng = np.random.default_rng(seed)
    sims = []
    for g in pd.unique(labels):
        idx = np.where(labels == g)[0]
        if len(idx) < 2:
            continue
        # sample pairs to bound cost
        n_pairs = min(max_pairs_per_group, len(idx) * (len(idx) - 1) // 2)
        a = rng.choice(idx, size=n_pairs)
        b = rng.choice(idx, size=n_pairs)
        keep = a != b
        a, b = a[keep], b[keep]
        s = np.sum(X[a] * X[b], axis=1)  # cosine = dot for normalised
        sims.append(s)
    if not sims:
        return np.nan
    return float(np.concatenate(sims).mean())


def main():
    FIG_DATA.mkdir(parents=True, exist_ok=True)

    db = lancedb.connect(str(LANCE))
    tbl = db.open_table("videos_e5large")
    df = (
        tbl.search().where("protest_anywhere = True").limit(100000)
        .select(["YT_ID", "DEFAULT_AUDIO_LANG", "country_combo", "vector"])
        .to_pandas()
    )
    print(f"protest-mentioning videos: {len(df):,}")

    cl = pd.read_csv(CLUSTERS, dtype={"YT_ID": str})
    cl["cluster"] = cl["cluster"].astype(int)
    df = df.merge(cl[["YT_ID", "cluster"]], on="YT_ID", how="inner")
    print(f"joined with clusters: {len(df):,}")

    X = np.vstack([np.asarray(v, dtype=np.float32) for v in df["vector"].values])
    # ensure normalised (e5 vectors were stored normalised; re-normalise to be safe)
    X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)

    df["lang"] = df["DEFAULT_AUDIO_LANG"].apply(lang_bucket)

    # ---- (1) within-group mean cosine ----
    overall = mean_within_group_cosine(X, np.zeros(len(df)))  # all in one group = baseline
    within_lang = mean_within_group_cosine(X, df["lang"].values)
    within_cluster = mean_within_group_cosine(X, df["cluster"].values)
    within_country = mean_within_group_cosine(X, df["country_combo"].values)

    within_tbl = pd.DataFrame([
        {"grouping": "overall (baseline)", "mean_cosine": overall},
        {"grouping": "same language", "mean_cosine": within_lang},
        {"grouping": "same country_combo", "mean_cosine": within_country},
        {"grouping": "same cluster (event/sense)", "mean_cosine": within_cluster},
    ])
    within_tbl.to_csv(FIG_DATA / "lang_vs_framing_within.csv", index=False)

    # ---- (2) centroid cosine heatmap ----
    centroids = {}
    for k in sorted(df["cluster"].unique()):
        c = X[df["cluster"].values == k].mean(axis=0)
        c = c / (np.linalg.norm(c) + 1e-9)
        centroids[k] = c
    ks = sorted(centroids.keys())
    M = np.zeros((len(ks), len(ks)))
    for i, ki in enumerate(ks):
        for j, kj in enumerate(ks):
            M[i, j] = float(np.dot(centroids[ki], centroids[kj]))
    labels = [f"C{k} {CLUSTER_SENSE.get(k,'?')}" for k in ks]
    cm = pd.DataFrame(M, index=labels, columns=labels)
    cm.to_csv(OUT_CENTROID)

    # ---- (3) nearest-neighbour concordance ----
    # cosine NN via full matmul (2045×2045 is fine)
    S = X @ X.T
    np.fill_diagonal(S, -1)
    nn = np.argmax(S, axis=1)
    lang_arr = df["lang"].values
    clus_arr = df["cluster"].values
    nn_same_lang = float(np.mean(lang_arr == lang_arr[nn]))
    nn_same_cluster = float(np.mean(clus_arr == clus_arr[nn]))

    # ---- headline tests on centroids ----
    def cos(a, b):
        return float(np.dot(centroids[a], centroids[b]))

    # Belarus-2020 across languages: C0 (DE), C3 (EN), C1 (RU mixed), C6 (BE/RU Belsat)
    by_de_en = cos(0, 3)      # DE vs EN, same event
    by_ru_en = cos(1, 3)      # RU vs EN, same event(ish)
    by_de_ru = cos(0, 1)      # DE vs RU, same event(ish)
    # Russian-language different events: C1 (Belarus RU) vs C7 (RU opposition) vs C5 (RU/UA war)
    ru_ru_diff_event_1 = cos(1, 7)   # both RU, different framing
    ru_ru_diff_event_2 = cos(1, 5)
    ru_ru_diff_event_3 = cos(5, 7)

    R = []
    R.append("# Language vs framing — the talk's central empirical test\n")
    R.append(f"N = {len(df):,} protest-mentioning videos (e5-large embeddings, 8 KMeans senses).\n")
    R.append("All embeddings L2-normalised; cosine = dot product.\n")

    R.append("## (1) Within-group mean cosine similarity\n")
    R.append("| Grouping | Mean cosine |")
    R.append("|---|---:|")
    for _, r in within_tbl.iterrows():
        R.append(f"| {r['grouping']} | {r['mean_cosine']:.4f} |")
    R.append("")
    verdict1 = "FRAMING/EVENT" if within_cluster > within_lang else "LANGUAGE"
    R.append(f"**Reading:** videos sharing a *cluster (event/sense)* are "
             f"{'more' if within_cluster>within_lang else 'less'} similar "
             f"(cos={within_cluster:.4f}) than videos sharing a *language* "
             f"(cos={within_lang:.4f}). → semantic space is organised more by "
             f"**{verdict1}** than by the other axis on this metric.\n")

    R.append("## (2) Nearest-neighbour concordance\n")
    R.append(f"- Each video's single nearest neighbour shares its **language** in "
             f"**{100*nn_same_lang:.1f}%** of cases.")
    R.append(f"- Each video's single nearest neighbour shares its **cluster (event/sense)** in "
             f"**{100*nn_same_cluster:.1f}%** of cases.")
    verdict3 = "EVENT/FRAMING" if nn_same_cluster > nn_same_lang else "LANGUAGE"
    R.append(f"- → nearest-neighbour structure is dominated by **{verdict3}**.\n")

    R.append("## (3) Centroid cosine — headline pairs\n")
    R.append("Belarus-2020 coverage across **different languages**:")
    R.append(f"- C0 (DE) ↔ C3 (EN): **{by_de_en:.4f}**")
    R.append(f"- C1 (RU) ↔ C3 (EN): **{by_ru_en:.4f}**")
    R.append(f"- C0 (DE) ↔ C1 (RU): **{by_de_ru:.4f}**")
    R.append("")
    R.append("Russian-language clusters with **different framing/event**:")
    R.append(f"- C1 (Belarus-RU) ↔ C7 (RU-opposition): **{ru_ru_diff_event_1:.4f}**")
    R.append(f"- C1 (Belarus-RU) ↔ C5 (RU/UA-war): **{ru_ru_diff_event_2:.4f}**")
    R.append(f"- C5 (RU/UA-war) ↔ C7 (RU-opposition): **{ru_ru_diff_event_3:.4f}**")
    R.append("")
    same_event_mean = np.mean([by_de_en, by_ru_en, by_de_ru])
    same_lang_mean = np.mean([ru_ru_diff_event_1, ru_ru_diff_event_2, ru_ru_diff_event_3])
    R.append(f"- Mean centroid cosine, **same event / different language**: **{same_event_mean:.4f}**")
    R.append(f"- Mean centroid cosine, **same language (RU) / different event**: **{same_lang_mean:.4f}**")
    if same_event_mean > same_lang_mean:
        R.append(f"\n> **FINDING (supports the thesis):** Belarus-2020 clusters in DE/EN/RU are "
                 f"on average *more* similar to each other ({same_event_mean:.3f}) than the "
                 f"Russian-language clusters are to each other ({same_lang_mean:.3f}). "
                 f"**Shared framing/event binds the embedding space more tightly than shared language.**")
    else:
        R.append(f"\n> **FINDING (qualifies the thesis):** on centroids, shared *language* "
                 f"({same_lang_mean:.3f}) binds at least as tightly as shared *event* "
                 f"({same_event_mean:.3f}). This is a presentable, honest counter-result — "
                 f"the model partly organises by language, marking a boundary where validation matters.")
    R.append("")

    R.append("## Full centroid cosine matrix\n")
    R.append("See `mini_study/centroid_cosine.csv` and `figures/fig3_cluster_map.png`.\n")
    R.append("```")
    R.append(cm.round(3).to_string())
    R.append("```")

    OUT_MD.write_text("\n".join(R), encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_CENTROID}")
    print(f"\n>>> within-language={within_lang:.4f}  within-cluster={within_cluster:.4f}")
    print(f">>> NN same-language={100*nn_same_lang:.1f}%  NN same-cluster={100*nn_same_cluster:.1f}%")
    print(f">>> same-event centroids={same_event_mean:.4f}  same-language centroids={same_lang_mean:.4f}")


if __name__ == "__main__":
    main()
