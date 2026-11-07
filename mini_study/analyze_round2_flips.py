"""Stage E Task 4 — post-hoc flip analysis of the round-2 active-learning wave.

Run AFTER the PI codes round-2 (and merge_round2_gold.py has been verified to
accept the sheet). Joins the selection manifest (why each item was picked:
conf1 / indirect / gate_fn / kept_lowrank) with the human labels and answers:

  * which uncertainty tags actually predicted human↔LLM disagreement (per-tag
    flip rate vs the wave average) — did the active-learning targeting work?
  * where do the flips go (confusion human×LLM on the new items)?
  * gate-consequence: how many flips would change index membership
    (LLM absent → human relevant = missed recall; LLM kept → human absent =
    precision leak)?

Never invents labels — exits if the sheet has no valid codes (mirrors
merge_round2_gold.py).

Run from project root:
    .venv_v2/bin/python mini_study/analyze_round2_flips.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

LABELS = {"direct", "indirect", "absent"}
TAGS = ["conf1", "indirect", "gate_fn", "kept_lowrank"]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--filled", default="mini_study/coding_sheet_round2_FILLED.csv",
                   help="HTML export; falls back to coding_sheet_round2.csv if absent")
    p.add_argument("--manifest", default="mini_study/round2_selection_manifest.csv")
    p.add_argument("--out", default="mini_study/round2_flip_report.md")
    return p.parse_args()


def main():
    a = parse_args()
    filled = Path(a.filled)
    if not filled.exists():
        alt = Path("mini_study/coding_sheet_round2.csv")
        print(f"[!] {filled} not found — trying {alt}")
        filled = alt
    if not filled.exists():
        raise SystemExit("No round-2 sheet found. Code mini_study/coding_round2.html first.")

    r2 = pd.read_csv(filled, dtype=str, keep_default_na=False, na_values=[])
    yt = "yt_id" if "yt_id" in r2.columns else "YT_ID"
    r2 = r2.rename(columns={yt: "yt_id"})
    r2["human"] = r2["protest_relevance"].str.strip().str.lower()
    coded = r2[r2["human"].isin(LABELS)][["yt_id", "human"]].copy()
    if len(coded) == 0:
        raise SystemExit(f"No valid labels yet in {filled} "
                         f"(found {len(r2)} rows, none with direct/indirect/absent). "
                         "The PI still needs to code the sheet.")

    man = pd.read_csv(a.manifest).rename(columns={"YT_ID": "yt_id"})
    df = coded.merge(man, on="yt_id", how="left")
    if df["relevance_llm"].isna().any():
        miss = df[df["relevance_llm"].isna()]["yt_id"].tolist()
        raise SystemExit(f"{len(miss)} coded items missing from the manifest: {miss[:5]}")
    df["flip"] = df["human"] != df["relevance_llm"]
    n, n_flip = len(df), int(df["flip"].sum())
    base = n_flip / n
    print(f"[1/3] {n} coded round-2 items; {n_flip} flips "
          f"(human≠LLM) = {100*base:.0f}% wave-average")

    # --- per-tag flip rates ------------------------------------------------ #
    rows = []
    for t in TAGS:
        sub = df[df["why_selected"].str.contains(t, na=False)]
        if len(sub):
            rows.append((t, len(sub), int(sub["flip"].sum()),
                         sub["flip"].mean()))
    print("[2/3] per-tag flip rates (vs wave avg "
          f"{100*base:.0f}%):")
    for t, nt, ft, rate in rows:
        marker = "▲" if rate > base else "▽"
        print(f"      {t:13s} n={nt:3d}  flips={ft:3d}  rate={100*rate:.0f}% {marker}")

    # --- flip direction + gate consequence --------------------------------- #
    conf = pd.crosstab(df["human"], df["relevance_llm"])
    kept = {"direct", "indirect"}
    missed_recall = df[(~df["relevance_llm"].isin(kept)) & (df["human"].isin(kept))]
    precision_leak = df[(df["relevance_llm"].isin(kept)) & (~df["human"].isin(kept))]
    print(f"[3/3] gate consequences on the wave: "
          f"{len(missed_recall)} missed-recall (LLM cut, human relevant), "
          f"{len(precision_leak)} precision-leak (LLM kept, human absent)")

    lines = [
        "# Round-2 flip analysis — did the active-learning targeting work?", "",
        f"{n} coded items, {n_flip} human↔LLM flips ({100*base:.0f}%). The wave was "
        "uncertainty-selected, so a flip rate well above the ~25% gold-v1 "
        "disagreement base-rate means the targeting found genuinely hard items.", "",
        "## Per-tag flip rates", "",
        "| tag | n | flips | rate |", "|---|---:|---:|---:|",
        *[f"| {t} | {nt} | {ft} | {100*rate:.0f}% |" for t, nt, ft, rate in rows],
        "",
        "## Confusion on the new items (rows = human, cols = LLM)", "",
        "```", conf.to_string(), "```", "",
        "## Gate consequences", "",
        f"- **{len(missed_recall)} missed-recall**: LLM cut them, human says relevant "
        f"({missed_recall['yt_id'].tolist()})",
        f"- **{len(precision_leak)} precision-leak**: LLM kept them, human says absent "
        f"({precision_leak['yt_id'].tolist()})", "",
        "Next: `merge_round2_gold.py` → `stage_e_gate.py --gold "
        "mini_study/coding_gold_v2.csv` (reports κ stratified by round).",
    ]
    Path(a.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
