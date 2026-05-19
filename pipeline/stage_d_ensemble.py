"""Stage D — ensemble retrieval comparing three fusion strategies.

For each anchor we have top-100 from e5-small and top-100 from e5-large.
Three strategies are produced and compared:

  1. RRF (Reciprocal Rank Fusion, k=60). Rank-based and robust to score
     scale differences, but biased toward consensus picks: a video that
     appears in both rankers' top-K gets boosted. Good for precision,
     potentially worse for recall (the "newly-surfaced" metric).

  2. CombSUM with min-max normalised similarity. Each model's similarities
     are min-max scaled within an anchor, then summed across models.
     Videos in only one ranker get half-credit (the missing model
     contributes 0). Balanced between precision and recall.

  3. UNION (recall-max). Keep every video appearing in either ranker's
     top-K. Score by the best (smallest) rank across rankers, breaking
     ties by max similarity. Maximises distinct video coverage; intended
     for downstream human review where breadth beats precision.

Output:
  outputs/retrieval_ensemble/topk_per_anchor.csv      (RRF, top-100)
  outputs/retrieval_ensemble/combsum_per_anchor.csv   (CombSUM, top-100)
  outputs/retrieval_ensemble/union_per_anchor.csv     (UNION, all distinct)
  outputs/retrieval_ensemble/comparison_summary.csv
  outputs/retrieval_ensemble/newly_surfaced.csv       (best of UNION)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


# Defaults match the paths produced by `v2_stage_b_retrieve.py` when run
# with --out-dir outputs/retrieval (e5-small) and outputs/retrieval_e5large.
DEFAULT_SMALL_CSV = "outputs/retrieval/topk_per_anchor.csv"
DEFAULT_LARGE_CSV = "outputs/retrieval_e5large/topk_per_anchor.csv"
DEFAULT_OUT_DIR   = "outputs/retrieval_ensemble"
DEFAULT_TOP_K     = 100
DEFAULT_K_RRF     = 60


def parse_args():
    p = argparse.ArgumentParser(
        description="Stage D — ensemble retrieval (RRF, CombSUM, UNION) "
                    "over Stage-B outputs from two encoders.")
    p.add_argument("--small-csv", default=DEFAULT_SMALL_CSV,
                   help="Stage-B output CSV from the small encoder")
    p.add_argument("--large-csv", default=DEFAULT_LARGE_CSV,
                   help="Stage-B output CSV from the large encoder")
    p.add_argument("--out-dir",   default=DEFAULT_OUT_DIR,
                   help="output directory for the four fused CSVs")
    p.add_argument("--top-k",     type=int, default=DEFAULT_TOP_K,
                   help="top-K per anchor for RRF / CombSUM (UNION keeps all)")
    p.add_argument("--k-rrf",     type=int, default=DEFAULT_K_RRF,
                   help="RRF smoothing constant (Cormack et al. 2009 use 60)")
    return p.parse_args()


# ---- helpers ----------------------------------------------------------------

def _to_bool(s: pd.Series) -> pd.Series:
    """Robust boolean parse — works whether the column is bool, int, or string."""
    if s.dtype == bool:
        return s.fillna(False)
    return s.astype(str).str.lower().isin(["true", "1"])


def add_rank_and_norm(df: pd.DataFrame, model_name: str) -> pd.DataFrame:
    """Add rank (within anchor) and min-max normalised similarity."""
    df = df.copy()
    df["rank"] = (df.groupby("anchor")["similarity"]
                    .rank(method="first", ascending=False).astype(int))
    # min-max normalise similarity within each anchor (0..1)
    grp = df.groupby("anchor")["similarity"]
    mn, mx = grp.transform("min"), grp.transform("max")
    df["sim_norm"] = (df["similarity"] - mn) / (mx - mn).replace(0, 1)
    df = df.rename(columns={"rank": f"rank_{model_name}",
                            "sim_norm": f"sim_norm_{model_name}",
                            "similarity": f"sim_{model_name}"})
    return df


def merge_rankers(small: pd.DataFrame, large: pd.DataFrame) -> pd.DataFrame:
    """Outer-join the two rankers' rank/sim columns per (anchor, YT_ID)."""
    sm = add_rank_and_norm(small, "small")[["anchor", "YT_ID", "rank_small", "sim_small", "sim_norm_small"]]
    lg = add_rank_and_norm(large, "large")[["anchor", "YT_ID", "rank_large", "sim_large", "sim_norm_large"]]
    return sm.merge(lg, on=["anchor", "YT_ID"], how="outer")


def attach_metadata(fused: pd.DataFrame, source: pd.DataFrame) -> pd.DataFrame:
    """Bring back metadata columns (TITLE, country_combo, etc.) for the fused rows."""
    cols = [c for c in source.columns
            if c not in {"anchor", "YT_ID", "similarity", "_distance"}]
    meta = source.drop_duplicates(subset=["YT_ID"])[["YT_ID"] + cols]
    out = fused.merge(meta, on="YT_ID", how="left")
    out["protest_anywhere_bool"] = _to_bool(out["protest_anywhere"])
    out["newly"] = ~out["protest_anywhere_bool"]
    return out


# ---- fusion strategies ------------------------------------------------------

def fusion_rrf(merged: pd.DataFrame, top_k: int, k_rrf: int) -> pd.DataFrame:
    f = merged.copy()
    f["rrf_small"] = (1.0 / (k_rrf + f["rank_small"])).fillna(0)
    f["rrf_large"] = (1.0 / (k_rrf + f["rank_large"])).fillna(0)
    f["score"] = f["rrf_small"] + f["rrf_large"]
    f["fused_rank"] = (f.groupby("anchor")["score"]
                         .rank(method="first", ascending=False).astype(int))
    return f[f["fused_rank"] <= top_k].copy()


def fusion_combsum(merged: pd.DataFrame, top_k: int) -> pd.DataFrame:
    """Sum of min-max normalised similarities; missing entries contribute 0."""
    f = merged.copy()
    f["score"] = f["sim_norm_small"].fillna(0) + f["sim_norm_large"].fillna(0)
    f["fused_rank"] = (f.groupby("anchor")["score"]
                         .rank(method="first", ascending=False).astype(int))
    return f[f["fused_rank"] <= top_k].copy()


def fusion_union(merged: pd.DataFrame) -> pd.DataFrame:
    """Recall-max: keep every video; score by best (min) rank across rankers."""
    f = merged.copy()
    # best rank across the two; missing → very large (so they sort last)
    f["best_rank"] = f[["rank_small", "rank_large"]].min(axis=1, skipna=True)
    # tie-break by max similarity
    f["max_sim"] = f[["sim_small", "sim_large"]].max(axis=1, skipna=True)
    # Stable global sort, then per-anchor cumcount gives correct fused_rank.
    # NaN best_rank → sentinel so missing-from-both videos (shouldn't exist
    # after outer-join, but be defensive) sort last.
    f = (f.assign(_br_fill=f["best_rank"].fillna(1e9))
           .sort_values(["anchor", "_br_fill", "max_sim"],
                        ascending=[True, True, False],
                        kind="mergesort"))
    f["fused_rank"] = f.groupby("anchor").cumcount() + 1
    return f.drop(columns=["_br_fill"])


# ---- main -------------------------------------------------------------------

def main():
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[D.1] Loading retrieval CSVs")
    small = pd.read_csv(args.small_csv)
    large = pd.read_csv(args.large_csv)
    print(f"      e5-small rows: {len(small):,}  ({args.small_csv})")
    print(f"      e5-large rows: {len(large):,}  ({args.large_csv})")

    # Canonicalise protest_anywhere up-front so both single-encoder and fused
    # branches use the same definition of "newly surfaced".
    small["newly"] = ~_to_bool(small["protest_anywhere"])
    large["newly"] = ~_to_bool(large["protest_anywhere"])

    merged = merge_rankers(small, large)
    print(f"\n[D.2] Outer-joined rankers: {len(merged):,} distinct (anchor, YT_ID) pairs")

    # Prefer e5-large metadata when a video appears in both (it is the
    # higher-quality retrieval), then fall back to e5-small.
    src_concat = pd.concat([large, small], ignore_index=True)

    print("\n[D.3] Producing three fused result sets")
    rrf  = attach_metadata(fusion_rrf(merged, args.top_k, args.k_rrf), src_concat)
    cs   = attach_metadata(fusion_combsum(merged, args.top_k),         src_concat)
    uni  = attach_metadata(fusion_union(merged),                       src_concat)

    rrf.sort_values(["anchor","fused_rank"]).to_csv(out_dir / "topk_per_anchor.csv",     index=False)
    cs.sort_values(["anchor","fused_rank"]).to_csv(out_dir / "combsum_per_anchor.csv", index=False)
    uni.sort_values(["anchor","fused_rank"]).to_csv(out_dir / "union_per_anchor.csv",  index=False)

    print(f"      RRF       — top-{args.top_k}/anchor, distinct={rrf['YT_ID'].nunique()}, total rows={len(rrf):,}")
    print(f"      CombSUM   — top-{args.top_k}/anchor, distinct={cs['YT_ID'].nunique()}, total rows={len(cs):,}")
    print(f"      Union     — all distinct/anchor, distinct={uni['YT_ID'].nunique()}, total rows={len(uni):,}")

    # -- per-anchor newly-surfaced comparison ---------------------------------
    print("\n[D.4] Per-anchor newly-surfaced rate (% of top hits without surface protest keyword)")
    rows = []
    for anchor in sorted(merged["anchor"].unique()):
        s_a = small[small["anchor"]==anchor]
        l_a = large[large["anchor"]==anchor]
        r_a = rrf[rrf["anchor"]==anchor]
        c_a = cs[cs["anchor"]==anchor]
        u_a = uni[uni["anchor"]==anchor]
        rows.append({
            "anchor": anchor,
            "small": round(100*s_a["newly"].mean(), 1),
            "large": round(100*l_a["newly"].mean(), 1),
            "rrf":   round(100*r_a["newly"].mean(), 1),
            "comb":  round(100*c_a["newly"].mean(), 1),
            "union": round(100*u_a["newly"].mean(), 1),
            "n_union": u_a["YT_ID"].nunique(),
        })
    summary = pd.DataFrame(rows)
    print(summary.to_string(index=False))
    summary.to_csv(out_dir / "comparison_summary.csv", index=False)

    # -- aggregate distinct counts --------------------------------------------
    print("\n[D.5] Aggregate distinct video coverage across all anchors")
    s_uniq = set(small["YT_ID"]); l_uniq = set(large["YT_ID"])
    r_uniq = set(rrf["YT_ID"]);   c_uniq = set(cs["YT_ID"]); u_uniq = set(uni["YT_ID"])
    print(f"      e5-small alone:      {len(s_uniq):,}")
    print(f"      e5-large alone:      {len(l_uniq):,}")
    print(f"      RRF top-{args.top_k}/anchor:    {len(r_uniq):,}")
    print(f"      CombSUM top-{args.top_k}/anchor:{len(c_uniq):,}")
    print(f"      Union (all distinct):{len(u_uniq):,}")
    print(f"      Theoretical max (S∪L): {len(s_uniq | l_uniq):,}")

    # -- newly-surfaced (deduped, best of UNION) ------------------------------
    newly = (uni[uni["newly"]]
             .sort_values("fused_rank")
             .drop_duplicates(subset=["YT_ID"]))
    out_newly = out_dir / "newly_surfaced.csv"
    newly.to_csv(out_newly, index=False)

    # Single-encoder newly-surfaced counts, computed dynamically so this
    # log line stays correct as the corpus / anchors change.
    n_small_newly = small[small["newly"]]["YT_ID"].nunique()
    n_large_newly = large[large["newly"]]["YT_ID"].nunique()
    print(f"\n[D.6] Distinct newly-surfaced videos via UNION: {len(newly):,}")
    print(f"      (e5-small alone produced {n_small_newly}; e5-large alone produced {n_large_newly})")
    print(f"      wrote {out_newly}")


if __name__ == "__main__":
    main()
