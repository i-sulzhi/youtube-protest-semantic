"""Block 2.4 — distil the LLM gate into a local, deterministic classifier.

Trains logistic regression on [e5-large embedding ‖ structural features] with
the 1,099 LLM relevance labels as the teacher, then:

  1. 5-fold CV agreement with the teacher (how much of the LLM gate the
     features capture);
  2. κ vs the human gold — the honest comparison against the LLM's own
     κ=0.611/0.735 (is the student close to the teacher's ceiling?);
  3. corpus-scale inference: relevance scores for ALL 21,710 feed videos
     (→ the Block-4.2 path: gate a 280K corpus without LLM cost).

Fully local, runs NOW (no keys, no PI input). Artefacts:
  outputs/stage_e/distilled_gate.joblib       model + scaler + feature list
  outputs/distilled_relevance_feed.csv        per-feed-video P(direct/indirect/absent)
  outputs/stage_e/distilled_gate_report.md

Run from project root:
    .venv_v2/bin/python scripts/train_distilled_gate.py
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

LABELS = ["direct", "indirect", "absent"]
STRUCT = ["velocity_d7_z", "broker_score", "visibility_days_top10"]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--lancedb", default="outputs/v2_lancedb")
    p.add_argument("--table", default="videos_e5large")
    p.add_argument("--index", default="outputs/stage_e/protest_index.csv")
    p.add_argument("--pred-glob",
                   default="outputs/stage_e/relevance_pred/claude_chunk*.jsonl")
    p.add_argument("--gold", default="mini_study/coding_layer2.csv")
    p.add_argument("--engagement", default="outputs/engagement_features.csv")
    p.add_argument("--hypergraph", default="outputs/hypergraph/vertex_stats.csv")
    p.add_argument("--search", default="outputs/search_features.csv")
    p.add_argument("--static", default="outputs/static_flags.csv")
    p.add_argument("--out-model", default="outputs/stage_e/distilled_gate.joblib")
    p.add_argument("--out-feed", default="outputs/distilled_relevance_feed.csv")
    p.add_argument("--report", default="outputs/stage_e/distilled_gate_report.md")
    return p.parse_args()


def load_labels(pattern: str) -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(pattern)):
        for line in open(f, encoding="utf-8"):
            if line.strip():
                rows.append(json.loads(line))
    return (pd.DataFrame(rows).drop_duplicates("yt_id", keep="first")
            .rename(columns={"yt_id": "YT_ID"}))


def build_features(a, ids: pd.Series) -> tuple[np.ndarray, list[str], pd.DataFrame]:
    import lancedb
    db = lancedb.connect(a.lancedb)
    tbl = db.open_table(a.table).to_pandas()[["YT_ID", "vector"]]
    base = pd.DataFrame({"YT_ID": ids})
    base = base.merge(tbl, on="YT_ID", how="left")
    miss = base["vector"].isna().sum()
    if miss:
        raise SystemExit(f"{miss} ids missing from LanceDB table {a.table}")

    eng = pd.read_csv(a.engagement, usecols=["YT_ID", "velocity_d7_z"])
    hyp = pd.read_csv(a.hypergraph, usecols=["YT_ID", "broker_score"])
    sea = pd.read_csv(a.search, usecols=["YT_ID", "visibility_days_top10"])
    base = base.merge(eng, on="YT_ID", how="left").merge(
        hyp, on="YT_ID", how="left").merge(sea, on="YT_ID", how="left")
    struct_cols = list(STRUCT)
    if Path(a.static).exists():
        st = pd.read_csv(a.static)
        flag_cols = [c for c in st.columns if c.startswith("topic_")
                     or c in ("has_captions", "age_restricted", "license_cc")]
        base = base.merge(st[["YT_ID"] + flag_cols], on="YT_ID", how="left")
        struct_cols += flag_cols

    vec = np.vstack(base["vector"].values).astype(np.float32)
    s = base[struct_cols].astype(float).fillna(0.0)
    mu, sd = s.mean(), s.std(ddof=0).replace(0, 1)
    sz = ((s - mu) / sd).values.astype(np.float32)
    X = np.hstack([vec, sz])
    scaler = {"mean": mu.to_dict(), "std": sd.to_dict(), "struct_cols": struct_cols}
    return X, struct_cols, scaler


def main():
    a = parse_args()
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import cohen_kappa_score
    from sklearn.model_selection import cross_val_predict

    labels = load_labels(a.pred_glob)
    idx = pd.read_csv(a.index, usecols=["YT_ID"]).merge(labels, on="YT_ID")
    y = np.asarray(idx["protest_relevance"].astype(str))
    print(f"[1/5] Teacher labels: {len(idx)} pool videos "
          f"({pd.Series(y).value_counts().to_dict()})")

    print("[2/5] Features: e5-large vectors + structural (LanceDB) …")
    X, struct_cols, scaler = build_features(a, idx["YT_ID"])
    print(f"      X = {X.shape[0]}×{X.shape[1]} "
          f"(1024 emb + {len(struct_cols)} structural)")

    print("[3/5] 5-fold CV vs the teacher …")
    clf = LogisticRegression(max_iter=3000, C=1.0)
    oof = cross_val_predict(clf, X, y, cv=5, n_jobs=-1)
    cv_acc = float((oof == y).mean())
    cv_k = cohen_kappa_score(y, oof)
    bin_k = cohen_kappa_score(pd.Series(y).ne("absent"), pd.Series(oof).ne("absent"))
    print(f"      OOF agreement with LLM: acc={cv_acc:.3f} κ3={cv_k:.3f} κ2={bin_k:.3f}")

    print("[4/5] Train on all pool labels → validate vs HUMAN gold …")
    clf.fit(X, y)
    gold = pd.read_csv(a.gold)[["yt_id", "protest_relevance"]].rename(
        columns={"yt_id": "YT_ID", "protest_relevance": "human"})
    gpos = idx.reset_index(drop=True)
    gmask = gpos["YT_ID"].isin(set(gold["YT_ID"]))
    # honest eval: a student that never saw the gold videos' teacher labels
    clf_h = LogisticRegression(max_iter=3000, C=1.0)
    clf_h.fit(X[~gmask.values], y[~gmask.values])
    pred_gold = clf_h.predict(X[gmask.values])
    gh = gpos.loc[gmask, ["YT_ID"]].assign(student=pred_gold).merge(gold, on="YT_ID")
    s_k3 = cohen_kappa_score(gh["human"], gh["student"])
    s_k2 = cohen_kappa_score(gh["human"].ne("absent"), gh["student"].ne("absent"))
    # the teacher's own gold metrics for comparison
    t = gpos.loc[gmask, ["YT_ID", "protest_relevance"]].merge(gold, on="YT_ID")
    t_k3 = cohen_kappa_score(t["human"], t["protest_relevance"])
    t_k2 = cohen_kappa_score(t["human"].ne("absent"), t["protest_relevance"].ne("absent"))
    print(f"      student vs human (gold held out of training): "
          f"κ3={s_k3:.3f} κ2={s_k2:.3f} "
          f"(teacher LLM: κ3={t_k3:.3f} κ2={t_k2:.3f})")

    print("[5/5] Corpus-scale inference on the full feed …")
    feed_ids = pd.read_csv("outputs/v2_feed_ready.csv.gz", usecols=["YT_ID"])["YT_ID"]
    Xf, _, _ = build_features(a, feed_ids)
    proba = clf.predict_proba(Xf)
    out = pd.DataFrame({"YT_ID": feed_ids,
                        "distilled_label": clf.predict(Xf)})
    for i, c in enumerate(clf.classes_):
        out[f"p_{c}"] = proba[:, i].round(4)
    out.to_csv(a.out_feed, index=False)
    n_rel = int((out["distilled_label"] != "absent").sum())
    print(f"      {a.out_feed}: {len(out):,} rows; "
          f"{n_rel:,} predicted relevant outside-pool candidates incl. pool")

    joblib.dump({"model": clf, "scaler": scaler, "labels": LABELS,
                 "table": a.table}, a.out_model)

    L = ["# Distilled gate — logreg student of the LLM relevance gate", "",
         f"Features: e5-large embedding (1024) + {len(struct_cols)} structural "
         f"({', '.join(struct_cols[:6])}…). Teacher: {len(idx)} LLM labels.", "",
         "| metric | student | teacher (LLM) |", "|---|---:|---:|",
         f"| OOF agreement with teacher (acc / κ3 / κ2) | "
         f"{cv_acc:.3f} / {cv_k:.3f} / {bin_k:.3f} | — |",
         f"| κ3 vs human gold, gold HELD OUT of training (n={len(gh)}) "
         f"| {s_k3:.3f} | {t_k3:.3f} |",
         f"| κ2 vs human gold (held out) | {s_k2:.3f} | {t_k2:.3f} |", "",
         "Interpretation: the student is usable for corpus-scale pre-gating "
         "(Block 4.2) when its human-κ is close to the teacher's; the LLM stays "
         "the production gate for the published index. Re-train after gold v2 "
         "and after any pool expansion.", "",
         f"Corpus inference: `{a.out_feed}` "
         f"({n_rel:,}/{len(out):,} predicted direct∪indirect — candidate mine for "
         "recall expansion: high-p_direct videos outside the current pool).",
         ]
    Path(a.report).write_text("\n".join(L), encoding="utf-8")
    print(f"      wrote {a.out_model}\n      wrote {a.report}")


if __name__ == "__main__":
    main()
