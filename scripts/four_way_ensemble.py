"""N-way ensemble analysis over multiple retrieval CSVs.

Aggregates per-anchor top-K results from N sources (here: e5-small/large ×
with-tags/no-tags), computes:

  - Per-anchor newly-surfaced rate for each source
  - Per-anchor UNION (all distinct videos across sources)
  - Aggregate distinct-video and newly-surfaced counts
  - Top-100 overlap statistics

The script does not modify the pipeline. It is a research script that
reads `outputs/retrieval*/topk_per_anchor.csv` files and reports.

Run from the project root:
    .venv_v2/bin/python scripts/four_way_ensemble.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import numpy as np

# Sources: (short name, retrieval CSV path)
SOURCES = [
    ("small_no_tags",   "outputs/retrieval/topk_per_anchor.csv"),
    ("large_no_tags",   "outputs/retrieval_e5large/topk_per_anchor.csv"),
    ("small_with_tags", "outputs/retrieval_with_tags/topk_per_anchor.csv"),
    ("large_with_tags", "outputs/retrieval_e5large_with_tags/topk_per_anchor.csv"),
]


def load_source(name: str, path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        print(f"  WARN: {name} → missing file {path} — skipping")
        return None
    df = pd.read_csv(path)
    df["__source__"] = name
    return df


def main():
    print("[1/4] Loading retrieval CSVs")
    frames = []
    available = []
    for name, path in SOURCES:
        df = load_source(name, path)
        if df is not None:
            frames.append(df)
            available.append(name)
            n_newly = (~df["protest_anywhere"]).sum()
            print(f"  ✓ {name:<18}  {len(df):>4} rows  {n_newly:>3} newly-surfaced")

    if len(frames) < 2:
        print("Need at least 2 sources; exiting.")
        sys.exit(1)

    full = pd.concat(frames, ignore_index=True)
    anchors = sorted(full["anchor"].unique())

    # -------------------------------------------------------------------------
    print("\n[2/4] Per-anchor newly-surfaced rate by source")
    header = f'{"anchor":<25}  ' + "  ".join(f"{n:>16}" for n in available) + f'  {"UNION":>7}  {"n_UNION":>8}'
    print(header)
    print("-" * len(header))
    for a in anchors:
        row_vals = []
        all_yt_ids = set()
        for name in available:
            sub = full[(full["anchor"] == a) & (full["__source__"] == name)]
            pct = 100 * (~sub["protest_anywhere"]).mean() if len(sub) else 0
            row_vals.append(f"{pct:>15.1f}%")
            all_yt_ids |= set(sub["YT_ID"])
        # UNION newly%
        union_rows = full[(full["anchor"] == a) & full["YT_ID"].isin(all_yt_ids)] \
                       .drop_duplicates("YT_ID")
        union_pct = 100 * (~union_rows["protest_anywhere"]).mean()
        n_union = len(all_yt_ids)
        line = f'{a:<25}  ' + "  ".join(row_vals) + f'  {union_pct:>6.1f}%  {n_union:>8}'
        print(line)

    # -------------------------------------------------------------------------
    print("\n[3/4] Aggregate distinct videos and newly-surfaced (across all anchors)")
    print(f'{"source":<25}  {"distinct":>10}  {"newly":>8}')
    print("-" * 50)
    per_source = {}
    for name in available:
        sub = full[full["__source__"] == name]
        distinct = sub["YT_ID"].nunique()
        newly = sub[~sub["protest_anywhere"]]["YT_ID"].nunique()
        per_source[name] = (distinct, newly)
        print(f'{name:<25}  {distinct:>10}  {newly:>8}')

    # All-source UNION
    all_distinct = full["YT_ID"].nunique()
    all_newly = full[~full["protest_anywhere"]]["YT_ID"].nunique()
    print(f'{"UNION (all sources)":<25}  {all_distinct:>10}  {all_newly:>8}')

    # Two-way UNION (existing Stage D baseline)
    if all(n in available for n in ("small_no_tags", "large_no_tags")):
        sub = full[full["__source__"].isin(("small_no_tags", "large_no_tags"))]
        s = sub["YT_ID"].nunique()
        n = sub[~sub["protest_anywhere"]]["YT_ID"].nunique()
        print(f'  ↳ existing 2-way UNION (no-tags): {s} distinct, {n} newly')
        if all_newly > n:
            print(f'  → gain from adding tags variants: +{all_newly-n} newly ({100*(all_newly/n-1):.1f}%)')

    # -------------------------------------------------------------------------
    print("\n[4/4] Pairwise top-100 overlap (per-anchor avg)")
    print(f'{"pair":<40}  {"avg overlap":>12}  {"min":>5}  {"max":>5}')
    print("-" * 70)
    from itertools import combinations
    for a_name, b_name in combinations(available, 2):
        overlaps = []
        for anchor in anchors:
            a_ids = set(full[(full["anchor"]==anchor) & (full["__source__"]==a_name)]["YT_ID"])
            b_ids = set(full[(full["anchor"]==anchor) & (full["__source__"]==b_name)]["YT_ID"])
            overlaps.append(len(a_ids & b_ids))
        avg = np.mean(overlaps)
        print(f'{a_name} × {b_name:<22}  {avg:>11.1f}/100  {min(overlaps):>5}  {max(overlaps):>5}')

    # -------------------------------------------------------------------------
    # Save a compact summary CSV for downstream use
    out_dir = Path("outputs/retrieval_nway")
    out_dir.mkdir(parents=True, exist_ok=True)
    full.to_csv(out_dir / "all_sources_combined.csv", index=False)
    union_newly = full[~full["protest_anywhere"]].drop_duplicates("YT_ID")
    union_newly.to_csv(out_dir / "newly_surfaced_union_nway.csv", index=False)
    print(f"\n  Wrote outputs/retrieval_nway/ ({all_distinct} distinct, {all_newly} newly)")


if __name__ == "__main__":
    main()
