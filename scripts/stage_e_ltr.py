"""Block 3.1 — learning-to-rank on the human gold (OOF, anti-overfit).

Pointwise logistic ranker over the composite's components + the new optional
features (channel LOO, event windows, static flags). Honest protocol: 5-fold
out-of-fold AUC on the gold, compared against the hand-set v2 composite
(the production baseline). The hand-set composite stays in production until
the learned ranker beats it OOF *on gold v2* — on 60 labels this is a smoke
test, and the script says so.

DESIGNED FOR INPUT: mini_study/coding_gold_v2.csv (≥110 labels after the PI
codes round-2). Runs on the 60-item round-1 gold meanwhile with a warning.

Run from project root:
    .venv_v2/bin/python scripts/stage_e_ltr.py
    .venv_v2/bin/python scripts/stage_e_ltr.py --gold mini_study/coding_gold_v2.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

BASE_FEATS = ["sim_agg", "velocity_d7_z", "broker_score", "visibility_days_top10"]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--index", default="outputs/stage_e/protest_index.csv")
    p.add_argument("--gold", default="mini_study/coding_layer2.csv")
    p.add_argument("--channel-features", default="outputs/channel_features.csv")
    p.add_argument("--event-features", default="outputs/event_features.csv")
    p.add_argument("--static", default="outputs/static_flags.csv")
    p.add_argument("--report", default="outputs/stage_e/ltr_report.md")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def zfill(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    sd = s.std(ddof=0)
    return ((s - s.mean()) / sd).fillna(0.0) if sd else s.fillna(0.0) * 0.0


def oof_auc(X, y, groups_ok, seed):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold
    scores = np.zeros(len(y), dtype=float)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    for tr, te in skf.split(X, y):
        clf = LogisticRegression(max_iter=2000, class_weight="balanced")
        clf.fit(X[tr], y[tr])
        scores[te] = clf.predict_proba(X[te])[:, 1]
    return roc_auc_score(y, scores), scores


def main():
    a = parse_args()
    from sklearn.metrics import roc_auc_score

    idx = pd.read_csv(a.index)
    gold = pd.read_csv(a.gold)
    ycol = "protest_relevance"
    gold = gold[["yt_id", ycol]].rename(columns={"yt_id": "YT_ID"})
    df = idx.merge(gold, on="YT_ID", how="inner")
    n = len(df)
    print(f"[1/3] Gold joined to index: {n} items "
          f"({df[ycol].value_counts().to_dict()})")
    if n < 100:
        print(f"      ⚠ only {n} labels — SMOKE TEST. The real run is after the "
              "PI codes round-2: --gold mini_study/coding_gold_v2.csv")

    feats = list(BASE_FEATS)
    for path, cols in [(a.channel_features, ["channel_relevant_rate_loo"]),
                       (a.event_features, ["days_to_event_anchor",
                                           "event_window_30"]),
                       (a.static, ["topic_military", "topic_tv", "has_captions"]),
                       ("outputs/trajectory_features.csv",
                        ["burst_ratio", "growth_after_d30", "revival",
                         "rank_slope"])]:
        if Path(path).exists():
            extra = pd.read_csv(path)
            use = [c for c in cols if c in extra.columns]
            df = df.merge(extra[["YT_ID"] + use], on="YT_ID", how="left",
                          suffixes=("", "_x"))
            feats += use
    X = np.column_stack([zfill(df[f]).values for f in feats])
    print(f"[2/3] Features ({len(feats)}): {', '.join(feats)}")

    rows = []
    for contrast, mask, pos in [
            ("direct-vs-absent", df[ycol].isin(["direct", "absent"]),
             df[ycol] == "direct"),
            ("relevant-vs-absent", pd.Series(True, index=df.index),
             df[ycol] != "absent")]:
        Xm, ym = X[mask.values], pos[mask].astype(int).values
        if len(set(ym)) < 2:
            continue
        auc_ltr, _ = oof_auc(Xm, ym, None, a.seed)
        auc_base = roc_auc_score(ym, df.loc[mask, "composite_score"])
        rows.append((contrast, int(mask.sum()), auc_base, auc_ltr,
                     auc_ltr - auc_base))
        print(f"      {contrast:20s} n={int(mask.sum()):3d}  "
              f"composite {auc_base:.3f} → LTR OOF {auc_ltr:.3f} "
              f"(Δ {auc_ltr-auc_base:+.3f})")

    verdict = ("LTR beats the hand-set composite OOF — consider promotion "
               "after confirming on gold v2 AND a membership-diff review."
               if all(r[4] > 0.01 for r in rows) else
               "No reliable OOF gain over the hand-set composite — keep the "
               "documented v2 weights in production (consistent with the "
               "Task-2 finding that magnitude search is noise at this gold size).")
    L = ["# Stage E LTR — learned ranker vs hand-set composite (OOF)", "",
         f"Gold: {n} items from `{a.gold}`. Features ({len(feats)}): "
         f"{', '.join(feats)}.",
         "" if n >= 100 else "\n**⚠ SMOKE TEST** — rerun with gold v2 (≥110).",
         "",
         "| contrast | n | composite AUC | LTR OOF AUC | Δ |",
         "|---|---:|---:|---:|---:|",
         *[f"| {c} | {nn} | {b:.3f} | {l:.3f} | {d:+.3f} |"
           for c, nn, b, l, d in rows],
         "", verdict]
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text("\n".join(L), encoding="utf-8")
    print(f"[3/3] wrote {a.report}")


if __name__ == "__main__":
    main()
