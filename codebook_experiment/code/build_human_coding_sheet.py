"""Build the 60-item human coding sheet for the κ baseline.

Strategy: 12 items per anchor × 5 anchors = 60 items. Within each anchor,
stratify by language_norm (round-robin top languages first) and by
protest_anywhere (so the human sees both surface-keyword and newly-surfaced
videos). Random seed = 42.

Output: mini_study/coding_sheet_for_human.csv

Columns: ALL columns from sample.csv + empty `human_label` (to be filled
in by hand) + `coding_notes` (free text). Add a `coder` header default
"sulzhytski".
"""
from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
SAMPLE = REPO / "mini_study" / "sample.csv"
OUT = REPO / "mini_study" / "coding_sheet_for_human.csv"

ITEMS_PER_ANCHOR = 12
SEED = 42


def main():
    s = pd.read_csv(SAMPLE, dtype=str, keep_default_na=False, na_values=[""])
    s["protest_anywhere"] = s["protest_anywhere"].astype(str).str.lower() == "true"

    rng = random.Random(SEED)
    picks = []
    for anchor in s["anchor"].unique():
        sub = s[s["anchor"] == anchor].copy()
        # Stratify by (language_norm × protest_anywhere) round-robin
        sub["bucket"] = sub["language_norm"] + "::" + sub["protest_anywhere"].astype(str)
        buckets = list(sub["bucket"].unique())
        rng.shuffle(buckets)
        bdict = {b: sub[sub["bucket"] == b].sample(frac=1, random_state=SEED).reset_index(drop=True) for b in buckets}
        cursors = {b: 0 for b in buckets}
        chosen = []
        while len(chosen) < ITEMS_PER_ANCHOR:
            empty = True
            for b in buckets:
                if cursors[b] < len(bdict[b]):
                    chosen.append(bdict[b].iloc[cursors[b]])
                    cursors[b] += 1
                    empty = False
                    if len(chosen) >= ITEMS_PER_ANCHOR:
                        break
            if empty:
                break
        picks.extend(chosen)

    sheet = pd.DataFrame(picks).reset_index(drop=True)
    sheet["coder"] = "sulzhytski"
    sheet["human_label"] = ""
    sheet["coding_notes"] = ""
    sheet["coding_confidence"] = ""  # 1=low, 2=medium, 3=high

    # Reorder so human-coding columns are at the front for ergonomics
    front = ["human_label", "coding_confidence", "coding_notes", "coder"]
    rest = [c for c in sheet.columns if c not in front]
    sheet = sheet[front + rest]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.to_csv(OUT, index=False)
    print(f"Wrote {OUT} ({len(sheet)} rows)")
    print(sheet[["anchor", "language_norm", "protest_anywhere"]].value_counts().to_string())


if __name__ == "__main__":
    main()
