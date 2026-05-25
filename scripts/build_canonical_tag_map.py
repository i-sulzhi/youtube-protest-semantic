"""Build a raw_tag -> canonical_tag mapping from the per-video tags CSV.

Inputs:
    complete_video_info_202404251556.csv   (350K rows, columns YT_ID,tags,PUBLISHED_AT)
    data/tag_synonyms.csv                  (curated canonical,variant pairs)

Outputs:
    outputs/canonical_tag_map.csv          (raw_tag, canonical_tag)
    outputs/canonical_tag_stats.csv        (canonical_tag, n_raw_variants, n_instances)

Reduction ratio: 1 - canonical/raw. Measured at ~10.18 % on the full
931,377 raw tags (the historical 3.86 % figure was case-only duplicates
in the MariaDB TAGS dictionary; see docs/RESULTS_LOG.md for the
reconciliation).

READER NOTE. The corpus contains string-literal tags like "Null", "NA",
"null" (real YouTube user inputs). When loading the output CSV, pass
`keep_default_na=False` to preserve these as strings — pandas' default
na_values would silently coerce them to NaN.

Run from the project root:
    .venv_v2/bin/python scripts/build_canonical_tag_map.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from canonical_tags import apply_synonyms, canonicalise, load_synonym_table


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--input",     default="complete_video_info_202404251556.csv")
    p.add_argument("--synonyms",  default="data/tag_synonyms.csv")
    p.add_argument("--out-map",   default="outputs/canonical_tag_map.csv")
    p.add_argument("--out-stats", default="outputs/canonical_tag_stats.csv")
    return p.parse_args()


def main():
    args = parse_args()

    print(f"[1/5] Reading synonyms: {args.synonyms}")
    synonyms = load_synonym_table(args.synonyms)
    print(f"      {len(synonyms):,} variant->canonical entries")

    print(f"\n[2/5] Reading tags: {args.input}")
    df = pd.read_csv(args.input, usecols=["tags"], dtype=str,
                     keep_default_na=False, na_values=[""])
    print(f"      {len(df):,} rows in source")

    print(f"\n[3/5] Exploding comma-separated tag strings")
    raw = (df["tags"].dropna()
                     .str.split(", ")
                     .explode()
                     .str.strip())
    raw = raw[raw != ""]
    n_instances = len(raw)
    print(f"      raw tag instances:  {n_instances:>10,}")
    print(f"      distinct raw tags:  {raw.nunique():>10,}")

    print(f"\n[4/5] Canonicalising distinct raw tags")
    distinct = pd.Series(raw.unique(), name="raw_tag")
    folded = distinct.map(canonicalise)
    canonical = folded.map(lambda t: apply_synonyms(t, synonyms))
    mapping = pd.DataFrame({"raw_tag": distinct, "canonical_tag": canonical})
    # Drop rows where canonicalisation collapsed to empty OR where either
    # column is NaN. The `!= ""` filter alone leaks NaN survivors because
    # in pandas `NaN != ""` evaluates to True; explicit notna() is needed.
    mapping = mapping.dropna(subset=["raw_tag", "canonical_tag"])
    mapping = mapping[(mapping["canonical_tag"] != "") & (mapping["raw_tag"] != "")]

    n_raw = len(mapping)
    n_canon = mapping["canonical_tag"].nunique()
    reduction = 1 - n_canon / n_raw if n_raw else 0.0
    print(f"      raw -> canonical:   {n_raw:>10,} -> {n_canon:>10,}")
    print(f"      reduction ratio:    {100 * reduction:>9.2f}%  "
          f"(expected ~3.86% per reference_dataset.md)")

    print(f"\n[5/5] Writing outputs")
    Path(args.out_map).parent.mkdir(parents=True, exist_ok=True)
    mapping.to_csv(args.out_map, index=False)
    map_kb = Path(args.out_map).stat().st_size / 1024
    print(f"      {args.out_map}  ({map_kb:.0f} KB, {len(mapping):,} rows)")

    # Instance-weighted statistics: how many raw variants collapse per
    # canonical, and how many total tag instances each canonical represents.
    raw_to_canon = dict(zip(mapping["raw_tag"], mapping["canonical_tag"]))
    instance_canon = raw.map(raw_to_canon)
    n_raw_variants = mapping.groupby("canonical_tag")["raw_tag"].nunique()
    n_raw_variants.index.name = "canonical_tag"
    inst_vc = instance_canon.value_counts()
    inst_vc.index.name = "canonical_tag"
    stats = pd.DataFrame({
        "n_raw_variants": n_raw_variants,
        "n_instances":    inst_vc,
    }).fillna(0).astype({"n_raw_variants": int, "n_instances": int})
    stats = (stats.sort_values(["n_instances", "n_raw_variants"], ascending=False)
                  .reset_index())   # index name preserved → first column is "canonical_tag"
    stats.to_csv(args.out_stats, index=False)
    stats_kb = Path(args.out_stats).stat().st_size / 1024
    print(f"      {args.out_stats}  ({stats_kb:.0f} KB, {len(stats):,} rows)")

    print(f"\nTop 20 canonical tags by raw-variant fan-in:")
    print(stats.nlargest(20, "n_raw_variants")
               .to_string(index=False))

    print(f"\nTop 20 canonical tags by instance count:")
    print(stats.nlargest(20, "n_instances")
               .to_string(index=False))


if __name__ == "__main__":
    main()
