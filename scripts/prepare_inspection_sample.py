"""Prepare an inspection-ready CSV for the 185 incremental newly-surfaced
videos — those surfaced *only* by the tags-augmented variants and missed
by the no-tags pipeline.

Reads:
  outputs/retrieval/newly_surfaced.csv             (e5-small no tags)
  outputs/retrieval_e5large/newly_surfaced.csv     (e5-large no tags)
  outputs/retrieval_with_tags/newly_surfaced.csv   (e5-small with tags)
  outputs/retrieval_e5large_with_tags/newly_surfaced.csv
                                                   (e5-large with tags)

Writes:
  outputs/inspection_185.csv  — incremental videos, with TITLE,
                                DESCRIPTION snippet, anchor, country
                                combo, both similarity scores, and an
                                empty 'label' column for the reviewer to
                                fill in.

Run from the project root:
    .venv_v2/bin/python scripts/prepare_inspection_sample.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

SRC = {
    "small_no_tags":    "outputs/retrieval/topk_per_anchor.csv",
    "large_no_tags":    "outputs/retrieval_e5large/topk_per_anchor.csv",
    "small_with_tags":  "outputs/retrieval_with_tags/topk_per_anchor.csv",
    "large_with_tags":  "outputs/retrieval_e5large_with_tags/topk_per_anchor.csv",
}

OUT_PATH = "outputs/inspection_185.csv"


def main():
    print("[1/3] Loading the four retrieval CSVs")
    dfs = {name: pd.read_csv(p) for name, p in SRC.items()}
    for name, df in dfs.items():
        print(f"      {name:<22}  {len(df):>4} rows")

    # Sets of newly-surfaced YT_IDs per source
    sets = {name: set(df[~df["protest_anywhere"]]["YT_ID"]) for name, df in dfs.items()}

    # 2-way no-tags baseline newly-surfaced set
    baseline = sets["small_no_tags"] | sets["large_no_tags"]
    print(f"\n      2-way no-tags newly-surfaced: {len(baseline)}")

    # 4-way newly-surfaced set
    four_way = baseline | sets["small_with_tags"] | sets["large_with_tags"]
    print(f"      4-way newly-surfaced:         {len(four_way)}")

    # Incremental: those surfaced only by adding tags variants
    incremental = four_way - baseline
    print(f"      incremental (only with tags): {len(incremental)}")

    # For each incremental video, find which sources surfaced it,
    # at what anchor, and what its best similarity was.
    print("\n[2/3] Building per-video inspection rows")
    rows = []
    for yt_id in incremental:
        # Find best-scoring (anchor, source) for this video, across the
        # two with-tags sources (since by definition no-tags didn't find it
        # as newly-surfaced).
        candidates = []
        for src_name in ("small_with_tags", "large_with_tags"):
            sub = dfs[src_name][dfs[src_name]["YT_ID"] == yt_id]
            for _, r in sub.iterrows():
                candidates.append((src_name, r["anchor"], r["similarity"], r))
        if not candidates:
            continue
        # Pick the best (anchor, source) by similarity
        candidates.sort(key=lambda x: -x[2])
        best_src, best_anchor, best_sim, best_row = candidates[0]
        # Other anchors this video was retrieved on
        other_anchors = sorted({a for s, a, _, _ in candidates} - {best_anchor})

        # Also try to fetch sim from no-tags variants (where it scored,
        # but didn't make it as newly because either it wasn't retrieved
        # or it's been re-classified — though newly_surfaced is fixed
        # per-row, so if not in no-tags newly set, it wasn't retrieved).
        no_tag_sims = {}
        for src_name in ("small_no_tags", "large_no_tags"):
            sub = dfs[src_name][(dfs[src_name]["YT_ID"] == yt_id) &
                                (dfs[src_name]["anchor"] == best_anchor)]
            if len(sub):
                no_tag_sims[src_name] = sub["similarity"].iloc[0]

        rows.append({
            "YT_ID":            yt_id,
            "best_anchor":      best_anchor,
            "best_source":      best_src,
            "best_sim":         round(best_sim, 4),
            "small_no_tags_sim":  round(no_tag_sims.get("small_no_tags", float("nan")), 4) if "small_no_tags" in no_tag_sims else None,
            "large_no_tags_sim":  round(no_tag_sims.get("large_no_tags", float("nan")), 4) if "large_no_tags" in no_tag_sims else None,
            "other_anchors":    ", ".join(other_anchors) if other_anchors else "",
            "country_combo":    best_row.get("country_combo", ""),
            "lang":             best_row.get("DEFAULT_AUDIO_LANG", ""),
            "PUBLISHED_AT":     best_row.get("PUBLISHED_AT", ""),
            "TITLE":            str(best_row.get("TITLE", ""))[:200],
            "DESCRIPTION":      str(best_row.get("DESCRIPTION", ""))[:500],
            "label":            "",   # for the reviewer to fill
            "notes":            "",
        })

    out = pd.DataFrame(rows)
    # Stratified sort: by anchor then by similarity descending, so the
    # reviewer sees the strongest candidates per anchor first.
    out = out.sort_values(["best_anchor", "best_sim"],
                          ascending=[True, False]).reset_index(drop=True)

    Path(OUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)

    print(f"\n[3/3] Wrote {len(out)} inspection rows → {OUT_PATH}")
    print("\nDistribution by best_anchor:")
    print(out["best_anchor"].value_counts().to_string())
    print("\nDistribution by best_source:")
    print(out["best_source"].value_counts().to_string())
    print("\nDistribution by country_combo:")
    print(out["country_combo"].value_counts().head(10).to_string())

    print("\nReviewer instructions:")
    print(f"  1. Open {OUT_PATH} in a spreadsheet.")
    print("  2. For each row, mark `label` as:")
    print("     R = clearly relevant to its best_anchor")
    print("     P = partially relevant (mentions the event but is not about it)")
    print("     N = not relevant (false positive — should not have been surfaced)")
    print("     ? = uncertain, needs second opinion")
    print("  3. Optional: add free-text notes in the `notes` column.")
    print("  4. Save and re-run a precision-by-anchor analysis.")


if __name__ == "__main__":
    main()
