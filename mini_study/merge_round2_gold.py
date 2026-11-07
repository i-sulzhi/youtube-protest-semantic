"""Stage E Task 4 — merge the PI's round-2 labels into an enlarged gold.

Run AFTER the PI codes `mini_study/coding_round2.html` (Export CSV →
coding_sheet_round2_FILLED.csv) or fills `coding_sheet_round2.csv` by hand.

Folds round-1 (the 60-item coding_layer2.csv) + round-2 human `protest_relevance`
labels into `mini_study/coding_gold_v2.csv`. Then recompute κ on the larger gold:

    .venv_v2/bin/python scripts/stage_e_gate.py  --gold mini_study/coding_gold_v2.csv
    .venv_v2/bin/python scripts/stage_e_tune.py  --gold mini_study/coding_gold_v2.csv

This script never invents labels — rows with an empty/invalid `protest_relevance`
are skipped and reported.

Run from project root:
    .venv_v2/bin/python mini_study/merge_round2_gold.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

LABELS = {"direct", "indirect", "absent"}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--round1", default="mini_study/coding_layer2.csv")
    p.add_argument("--filled", default="mini_study/coding_sheet_round2_FILLED.csv",
                   help="HTML export; falls back to coding_sheet_round2.csv if absent")
    p.add_argument("--manifest", default="mini_study/round2_selection_manifest.csv")
    p.add_argument("--out", default="mini_study/coding_gold_v2.csv")
    p.add_argument("--round-label", type=int, default=2,
                   help="round number for the new wave (audit wave = 3)")
    return p.parse_args()


def _pick_col(df, *names):
    for n in names:
        if n in df.columns:
            return n
    raise SystemExit(f"none of {names} in {list(df.columns)}")


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
    yt = _pick_col(r2, "yt_id", "YT_ID")
    rel = _pick_col(r2, "protest_relevance")
    r2 = r2.rename(columns={yt: "yt_id", rel: "protest_relevance"})
    r2["protest_relevance"] = r2["protest_relevance"].str.strip().str.lower()

    total = len(r2)
    coded = r2[r2["protest_relevance"].isin(LABELS)].copy()
    skipped = total - len(coded)
    if len(coded) == 0:
        raise SystemExit(f"No valid labels yet in {filled} "
                         f"(found {total} rows, none with direct/indirect/absent). "
                         "The PI still needs to code the sheet.")
    print(f"[1/3] Round-2 filled: {len(coded)}/{total} coded "
          f"({skipped} blank/invalid skipped)")

    r1_raw = pd.read_csv(a.round1)
    r1_cols = ["yt_id", "protest_relevance"] + (["round"] if "round" in r1_raw.columns else [])
    r1 = r1_raw[r1_cols].copy()
    if "round" not in r1.columns:
        r1["round"] = 1
    coded = coded[["yt_id", "protest_relevance"]].copy()
    coded["round"] = a.round_label

    dup = set(r1["yt_id"]) & set(coded["yt_id"])
    if dup:
        print(f"[!] {len(dup)} round-2 yt_ids already in round-1 gold — keeping round-1, "
              "dropping the round-2 duplicates")
        coded = coded[~coded["yt_id"].isin(dup)]

    gold = pd.concat([r1, coded], ignore_index=True).drop_duplicates("yt_id", keep="first")
    gold.to_csv(a.out, index=False)
    print(f"[2/3] Wrote {a.out}: {len(gold)} items "
          f"(round-1 {len(r1)} + round-2 {len(coded)})")
    print(f"      class dist: {gold['protest_relevance'].value_counts().to_dict()}")

    # optional: how the human labels compare to the LLM on the new items
    man = Path(a.manifest)
    if man.exists():
        m_raw = pd.read_csv(man)
        m_cols = [c for c in ["YT_ID", "relevance_llm", "why_selected", "stratum"]
                  if c in m_raw.columns]
        m = m_raw[m_cols].rename(columns={"YT_ID": "yt_id"})
        chk = coded.merge(m, on="yt_id", how="left")
        agree = (chk["protest_relevance"] == chk["relevance_llm"]).mean()
        flip = chk[chk["protest_relevance"] != chk["relevance_llm"]]
        print(f"[3/3] On the {len(chk)} new items, human==LLM on "
              f"{100*agree:.0f}%; {len(flip)} disagreements "
              f"(the high-value labels). Human dist on new items: "
              f"{coded['protest_relevance'].value_counts().to_dict()}")
    print("\nNext — recompute κ on the enlarged gold:")
    print(f"  scripts/stage_e_gate.py --gold {a.out}")
    print(f"  scripts/stage_e_tune.py --gold {a.out}")


if __name__ == "__main__":
    main()
