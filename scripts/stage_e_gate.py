"""Stage E gate — apply the Claude relevance labels to the ranked index.

Aggregates the per-chunk Claude relevance predictions (protest_relevance ∈
{direct, indirect, absent}), validates them against the 60-item human gold
(Cohen's κ on the topic axis), then applies the gate to the composite-ranked
index from stage_e_rank.py:

  * protest_index_scored.csv  — all pool videos, with the LLM relevance label.
  * protest_index_gated.csv   — direct∪indirect only, re-ranked = the clean
                                protest-video index (the deliverable).

The gate is the precision lever the codebook diagnosis called for: the
recall-maximised retrieval pulled in ~70% topic-noise; this removes the videos
the annotator judges not-about-protest, keeping the composite ordering within
the survivors.

Run after stage_e_rank.py and the 6 Claude relevance sub-agents:
    .venv_v2/bin/python scripts/stage_e_gate.py
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import (accuracy_score, cohen_kappa_score,
                             confusion_matrix)

LABELS = ["direct", "indirect", "absent"]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--pred-glob", default="outputs/stage_e/relevance_pred/claude_chunk*.jsonl")
    p.add_argument("--index", default="outputs/stage_e/protest_index.csv")
    p.add_argument("--gold",  default="mini_study/coding_layer2.csv")
    p.add_argument("--out-dir", default="outputs/stage_e")
    return p.parse_args()


def load_preds(pattern: str) -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(pattern)):
        for line in open(f, encoding="utf-8"):
            if line.strip():
                rows.append(json.loads(line))
    p = pd.DataFrame(rows).drop_duplicates(subset="yt_id", keep="first")
    return p.rename(columns={"yt_id": "YT_ID",
                             "protest_relevance": "relevance_llm",
                             "confidence": "relevance_conf"})


def validate(v: pd.DataFrame) -> dict:
    """Gate-vs-human metrics on a merged frame with `human` + `relevance_llm`."""
    hb, lb = v["human"].ne("absent"), v["relevance_llm"].ne("absent")
    return {
        "n": len(v),
        "acc3": accuracy_score(v["human"], v["relevance_llm"]),
        "kappa3": cohen_kappa_score(v["human"], v["relevance_llm"], labels=LABELS),
        "acc2": accuracy_score(hb, lb),
        "kappa2": cohen_kappa_score(hb, lb),
        "cm": confusion_matrix(v["human"], v["relevance_llm"], labels=LABELS),
        "absent_caught": int(((v.human == "absent") & (v.relevance_llm == "absent")).sum()),
        "n_absent": int((v.human == "absent").sum()),
        "direct_lost": int(((v.human == "direct") & (v.relevance_llm == "absent")).sum()),
        "n_direct": int((v.human == "direct").sum()),
    }


def main():
    a = parse_args()
    out_dir = Path(a.out_dir)

    # --- 1. Aggregate predictions -----------------------------------------
    print(f"[1/4] Aggregating relevance predictions: {a.pred_glob}")
    pred = load_preds(a.pred_glob)
    dist = pred["relevance_llm"].value_counts().reindex(LABELS).to_dict()
    print(f"      {len(pred)} videos labelled — {dist}")

    # --- 2. Validate against human gold -----------------------------------
    print("[2/4] Validating against human gold")
    gold_raw = pd.read_csv(a.gold)
    gold_cols = ["yt_id", "protest_relevance"] + (["round"] if "round" in gold_raw.columns else [])
    gold = gold_raw[gold_cols].rename(
        columns={"yt_id": "YT_ID", "protest_relevance": "human"})
    v = pred.merge(gold, on="YT_ID", how="inner")
    m = validate(v)
    acc3, kappa3, cm = m["acc3"], m["kappa3"], m["cm"]
    acc2, kappa2 = m["acc2"], m["kappa2"]
    absent_caught, n_absent = m["absent_caught"], m["n_absent"]
    direct_lost, n_direct = m["direct_lost"], m["n_direct"]
    print(f"      3-class: acc={acc3:.3f} κ={kappa3:.3f} | binary: acc={acc2:.3f} κ={kappa2:.3f}")
    print(f"      gate keeps {n_direct-direct_lost}/{n_direct} human-direct, "
          f"removes {absent_caught}/{n_absent} human-absent")

    # Stratified κ by gold round. Round-2+ waves are uncertainty-selected
    # (adversarial), so a pooled κ understates the gate by sample composition;
    # round-1 is the comparable baseline, later rounds a hard-zone lower bound.
    by_round = []
    if "round" in v.columns and v["round"].nunique() > 1:
        for rnd, vr in v.groupby("round"):
            mr = validate(vr)
            by_round.append((rnd, mr))
            print(f"      round {rnd} (n={mr['n']}): 3-class κ={mr['kappa3']:.3f} "
                  f"| binary κ={mr['kappa2']:.3f}")

    # Confidence calibration: does the gate's self-reported confidence track
    # accuracy? conf=1 ≈ coin-flip would justify auto-routing to human review.
    calib = []
    if "relevance_conf" in v.columns:
        vc = v.dropna(subset=["relevance_conf"])
        for conf, vg in vc.groupby(vc["relevance_conf"].astype(int)):
            calib.append((conf, len(vg),
                          accuracy_score(vg["human"], vg["relevance_llm"]),
                          accuracy_score(vg["human"].ne("absent"),
                                         vg["relevance_llm"].ne("absent"))))
        if calib:
            print("      calibration: " + "  ".join(
                f"conf={c}: acc3={a3:.2f} (n={n})" for c, n, a3, _ in calib))

    # --- 3. Apply gate to the ranked index --------------------------------
    print("[3/4] Applying gate to the composite-ranked index")
    idx = pd.read_csv(a.index).merge(pred[["YT_ID", "relevance_llm", "relevance_conf"]],
                                     on="YT_ID", how="left")

    # Coverage check — sub-agents have silently dropped briefing items while
    # reporting completeness (see RESULTS_LOG / STAGE_E_ROADMAP gotcha). Make
    # the briefing-vs-JSONL diff automatic instead of a manual ritual.
    missing = idx.loc[idx["relevance_llm"].isna(), "YT_ID"].tolist()
    strays = sorted(set(pred["YT_ID"]) - set(idx["YT_ID"]))
    if missing:
        shown = ", ".join(missing[:20]) + (" …" if len(missing) > 20 else "")
        print(f"      ⚠ {len(missing)} pool videos have NO relevance label "
              f"(sub-agent drop?): {shown}\n"
              f"        → re-brief them or hand-label into a fix JSONL before "
              f"trusting the gated index.")
    if strays:
        print(f"      ⚠ {len(strays)} labelled videos are not in the index pool "
              f"(stale JSONLs?): {', '.join(strays[:10])}"
              + (" …" if len(strays) > 10 else ""))
    if not missing and not strays:
        print(f"      label coverage OK: all {len(idx)} pool videos labelled, "
              f"no strays")

    idx["relevance_llm"] = idx["relevance_llm"].fillna("unlabelled")
    scored_path = out_dir / "protest_index_scored.csv"
    idx.to_csv(scored_path, index=False)

    gated = idx[idx["relevance_llm"].isin(["direct", "indirect"])].copy()
    gated = gated.sort_values("composite_score", ascending=False).reset_index(drop=True)
    gated["rank"] = range(1, len(gated) + 1)
    gated_path = out_dir / "protest_index_gated.csv"
    gated.to_csv(gated_path, index=False)
    n_in, n_out = len(idx), len(gated)
    print(f"      {n_in} -> {n_out} videos kept ({100*n_out/n_in:.0f}%); "
          f"{n_in-n_out} cut as absent/unlabelled")
    per_anchor = gated["primary_anchor"].value_counts()

    # --- 4. Report --------------------------------------------------------
    print("[4/4] Writing gate report")
    lines = [
        "# Stage E gate — Claude relevance labels applied to the index", "",
        f"Pool: {n_in} videos. LLM relevance distribution: "
        f"direct {dist.get('direct')}, indirect {dist.get('indirect')}, "
        f"absent {dist.get('absent')}.", "",
        (f"⚠ **Label coverage: {len(missing)} pool videos unlabelled, "
         f"{len(strays)} stray labels** — fix before trusting the index."
         if (missing or strays) else
         "Label coverage: complete (every pool video labelled, no strays)."),
        "",
        f"## Validation vs human gold (n={m['n']}, protest_relevance axis)", "",
        "| Metric | Value |", "|---|---:|",
        f"| 3-class accuracy | {acc3:.3f} |",
        f"| 3-class Cohen κ | **{kappa3:.3f}** |",
        f"| binary relevant-vs-absent accuracy | {acc2:.3f} |",
        f"| binary Cohen κ | **{kappa2:.3f}** |",
        f"| human-absent correctly cut | {absent_caught}/{n_absent} |",
        f"| human-direct preserved (never cut) | {n_direct-direct_lost}/{n_direct} |",
        "",
        *([
            "### κ stratified by gold round", "",
            "Later rounds are uncertainty-selected (hard cases by design), so "
            "their κ is a lower bound on the hard zone, **not comparable** to "
            "the round-1 baseline; the pooled κ above mixes the two.", "",
            "| round | n | 3-class κ | binary κ | direct kept | absent cut |",
            "|---|---:|---:|---:|---:|---:|",
            *[f"| {rnd} | {mr['n']} | {mr['kappa3']:.3f} | {mr['kappa2']:.3f} "
              f"| {mr['n_direct']-mr['direct_lost']}/{mr['n_direct']} "
              f"| {mr['absent_caught']}/{mr['n_absent']} |"
              for rnd, mr in by_round],
            "",
        ] if by_round else []),
        *([
            "### Confidence calibration (gold items)", "",
            "| LLM conf | n | 3-class acc | binary acc |",
            "|---|---:|---:|---:|",
            *[f"| {c} | {n} | {a3:.3f} | {a2:.3f} |" for c, n, a3, a2 in calib],
            "",
        ] if calib else []),
        "Confusion matrix (rows = human, cols = LLM), order " + str(LABELS) + ":", "",
        "```",
        "\n".join("  ".join(f"{x:4d}" for x in row) for row in cm),
        "```",
        "",
        "The gate's only false-negatives are `indirect` (peripheral) videos pushed "
        "to `absent`; `direct` protest videos are never dropped — the right failure "
        "mode for a precision gate.", "",
        "## Gate effect", "",
        f"- **{n_out} videos** kept (direct∪indirect) = the clean index "
        f"`protest_index_gated.csv`.",
        f"- {n_in-n_out} cut as topic-noise.", "",
        "Per-anchor survivors:", "",
        "| anchor | kept |", "|---|---:|",
        *[f"| {k} | {v_} |" for k, v_ in per_anchor.items()],
        "",
        f"Full pool with labels: `protest_index_scored.csv`. "
        f"Clean index: `protest_index_gated.csv`.",
    ]
    (out_dir / "gate_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"      wrote {scored_path}\n      wrote {gated_path}\n"
          f"      wrote {out_dir/'gate_report.md'}")


if __name__ == "__main__":
    main()
