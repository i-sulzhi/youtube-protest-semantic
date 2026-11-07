"""Verify which regenerated artefacts are on disk (so we never regen blindly).

Prints a present/missing table for every Tier A–D artefact in DATA_MANIFEST.md,
with row counts where cheap, and the regen hint for anything missing. Exit 0 if
the full Stage-E chain is reproducible from disk, 1 if a Tier-A/B (expensive or
DB-bound) artefact is missing.

    .venv_v2/bin/python scripts/verify_outputs.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# (tier, path, is_lance, regen-hint)
ARTEFACTS = [
    ("A", "outputs/v2_lancedb/videos.lance", True, "stage_a_embed e5-small"),
    ("A", "outputs/v2_lancedb/videos_e5large.lance", True, "stage_a_embed e5-large"),
    ("A", "outputs/v2_lancedb/videos_with_tags.lance", True, "stage_a_embed e5-small --use-tags"),
    ("A", "outputs/v2_lancedb/videos_e5large_with_tags.lance", True, "stage_a_embed e5-large --use-tags"),
    ("B", "outputs/v2_feed_ready.csv.gz", False, "regen_feed_ready.py (MariaDB)"),
    ("B", "outputs/v2_feed_ready_with_tags.csv.gz", False, "enrich_with_tags.py"),
    ("B", "outputs/engagement_features.csv", False, "build_engagement_features.py (MariaDB)"),
    ("B", "outputs/churn_signal.csv", False, "detect_churn.py (MariaDB)"),
    ("B", "outputs/search_features.csv", False, "build_search_features.py (MariaDB)"),
    ("B", "outputs/hypergraph/vertex_stats.csv", False, "build_hypergraph.py --skip-hnx (MariaDB)"),
    ("C", "outputs/retrieval/topk_per_anchor.csv", False, "stage_b_retrieve videos"),
    ("C", "outputs/retrieval_e5large/topk_per_anchor.csv", False, "stage_b_retrieve videos_e5large"),
    ("C", "outputs/retrieval_with_tags/topk_per_anchor.csv", False, "stage_b_retrieve videos_with_tags"),
    ("C", "outputs/retrieval_e5large_with_tags/topk_per_anchor.csv", False, "stage_b_retrieve videos_e5large_with_tags"),
    ("C", "outputs/retrieval_nway/all_sources_combined.csv", False, "four_way_ensemble.py"),
    ("C", "outputs/stage_e/protest_index.csv", False, "stage_e_rank.py"),
    ("C", "outputs/channel_features.csv", False, "build_channel_features.py"),
    ("D", "outputs/stage_e/protest_index_gated.csv", False, "stage_e_gate.py"),
    ("D", "mini_study/coding_layer2.csv", False, "(60-item human gold — do not regen)"),
    ("D", "mini_study/coding_sheet_round2.csv", False, "build_active_learning_sheet.py"),
]


def n_rows(path: Path, is_lance: bool):
    try:
        if is_lance:
            import lancedb
            db = lancedb.connect(str(path.parent))
            return f"{len(db.open_table(path.stem)):,}"
        if path.suffix == ".gz" or path.suffix == ".csv":
            import pandas as pd
            return f"{len(pd.read_csv(path)):,}"
    except Exception:
        return "?"
    return ""


def main():
    print(f"{'tier':<4} {'status':<8} {'rows':>8}  artefact")
    print("-" * 74)
    missing_ab = 0
    for tier, rel, is_lance, hint in ARTEFACTS:
        p = REPO / rel
        ok = p.exists()
        rows = n_rows(p, is_lance) if ok else ""
        status = "OK" if ok else "MISSING"
        print(f"{tier:<4} {status:<8} {rows:>8}  {rel}" + ("" if ok else f"   ← {hint}"))
        if not ok and tier in ("A", "B"):
            missing_ab += 1

    rp = REPO / "outputs/stage_e/relevance_pred"
    n_pred = len(list(rp.glob("claude_chunk*.jsonl"))) if rp.exists() else 0
    print("-" * 74)
    print(f"relevance_pred JSONLs (Tier D, LLM labels): {n_pred} files")
    if missing_ab:
        print(f"\n⚠ {missing_ab} Tier-A/B artefact(s) missing — regen needed "
              f"(see docs/DATA_MANIFEST.md). Tier-A is ~55 min of embeddings.")
        sys.exit(1)
    print("\n✓ All expensive (Tier A/B) artefacts present — chain reproducible from disk.")


if __name__ == "__main__":
    main()
