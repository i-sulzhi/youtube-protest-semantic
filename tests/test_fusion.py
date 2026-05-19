"""Unit tests for v2_stage_d_ensemble fusion helpers.

The first three tests (the `test_regression_*` ones) would each have
caught one of the bugs fixed in this debug session — they exercise the
specific behaviour that broke. The remaining tests cover normal cases.

Run with:
    .venv_v2/bin/pytest tests/ -v
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stage_d_ensemble import (
    _to_bool,
    add_rank_and_norm,
    merge_rankers,
    fusion_rrf,
    fusion_combsum,
    fusion_union,
    attach_metadata,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_retrieval(anchor: str, ids: list[str], sims: list[float]) -> pd.DataFrame:
    """Build a minimal Stage-B-style retrieval CSV row set for one anchor."""
    return pd.DataFrame({
        "anchor": [anchor] * len(ids),
        "YT_ID":  ids,
        "similarity": sims,
        "protest_anywhere": [False] * len(ids),
        "country_combo":   ["RU"] * len(ids),
        "TITLE":           [f"title-{i}" for i in ids],
    })


@pytest.fixture
def small():
    # rank 1=highest similarity → A, B, C
    return _make_retrieval("anc1", ["A", "B", "C"], [0.9, 0.8, 0.7])


@pytest.fixture
def large():
    # rank 1 → D, A, B (different best matches, partial overlap)
    return _make_retrieval("anc1", ["D", "A", "B"], [0.95, 0.85, 0.75])


@pytest.fixture
def merged(small, large):
    return merge_rankers(small, large)


# ---------------------------------------------------------------------------
# Regression tests for the three bugs fixed in this session
# ---------------------------------------------------------------------------

def test_regression_fusion_union_sorted_by_best_rank():
    """REGRESSION: fusion_union previously discarded its sort and produced
    fused_rank in arbitrary positional order. After the fix, fused_rank
    must be monotonic with best_rank within each anchor."""
    # Construct a merged DataFrame where best_rank is NOT in source-row order
    merged = pd.DataFrame({
        "anchor":     ["a"] * 5,
        "YT_ID":      ["v1", "v2", "v3", "v4", "v5"],
        "rank_small": [5,    1,    3,    np.nan, 2],
        "rank_large": [np.nan, 2,  4,    1,      5],
        "sim_small":  [0.5, 0.9, 0.7, np.nan, 0.8],
        "sim_large":  [np.nan, 0.85, 0.65, 0.95, 0.55],
        "sim_norm_small": [0.0, 1.0, 0.5, np.nan, 0.75],
        "sim_norm_large": [np.nan, 0.75, 0.25, 1.0, 0.0],
    })
    out = fusion_union(merged).sort_values("fused_rank")
    br = out["best_rank"].values
    # Strictly non-decreasing — this is what the old buggy code failed
    assert np.all(np.diff(br) >= 0), (
        f"fused_rank must be monotonic in best_rank, got best_rank order {br}"
    )


def test_regression_fusion_union_tie_break_by_max_sim():
    """REGRESSION: when two videos share best_rank, max_sim breaks the tie
    (higher sim wins). The old bug ignored max_sim entirely."""
    merged = pd.DataFrame({
        "anchor":     ["a"] * 3,
        "YT_ID":      ["lo_sim", "hi_sim", "mid_sim"],
        "rank_small": [1, 1, 1],   # all tied on best_rank
        "rank_large": [1, 1, 1],
        "sim_small":  [0.3, 0.9, 0.6],
        "sim_large":  [0.3, 0.9, 0.6],
        "sim_norm_small": [0.0, 1.0, 0.5],
        "sim_norm_large": [0.0, 1.0, 0.5],
    })
    out = fusion_union(merged).sort_values("fused_rank")
    assert out["YT_ID"].tolist() == ["hi_sim", "mid_sim", "lo_sim"], (
        f"tie-break by max_sim descending broken, got {out['YT_ID'].tolist()}"
    )


def test_regression_to_bool_robust_to_string_csv():
    """REGRESSION: protest_anywhere parsing must handle string 'False'
    correctly. The old `.astype(bool)` returned True for any non-empty
    string, silently flipping all newly-surfaced flags."""
    s = pd.Series(["True", "False", "true", "false", "1", "0"])
    out = _to_bool(s)
    assert out.tolist() == [True, False, True, False, True, False]


def test_regression_to_bool_with_nan_returns_false():
    """REGRESSION: NaN must not be parsed as True — a missing
    protest_anywhere must not be reported as 'has protest keyword'."""
    s = pd.Series([True, np.nan, False])
    out = _to_bool(s)
    assert out.tolist() == [True, False, False]


# ---------------------------------------------------------------------------
# _to_bool helper
# ---------------------------------------------------------------------------

def test_to_bool_passthrough_for_bool_dtype():
    s = pd.Series([True, False, True], dtype=bool)
    assert _to_bool(s).tolist() == [True, False, True]


def test_to_bool_case_insensitive_string():
    s = pd.Series(["TRUE", "True", "true", "tRuE"])
    assert _to_bool(s).tolist() == [True, True, True, True]


# ---------------------------------------------------------------------------
# add_rank_and_norm
# ---------------------------------------------------------------------------

def test_add_rank_and_norm_rank_starts_at_1(small):
    out = add_rank_and_norm(small, "small")
    assert out["rank_small"].min() == 1
    assert out["rank_small"].max() == 3


def test_add_rank_and_norm_rank_descending_by_similarity(small):
    out = add_rank_and_norm(small, "small").sort_values("rank_small")
    # A has highest sim (0.9) → rank 1; C lowest (0.7) → rank 3
    assert out["YT_ID"].tolist() == ["A", "B", "C"]


def test_add_rank_and_norm_normalised_in_unit_range(small):
    out = add_rank_and_norm(small, "small")
    assert out["sim_norm_small"].min() == pytest.approx(0.0)
    assert out["sim_norm_small"].max() == pytest.approx(1.0)


def test_add_rank_and_norm_handles_all_equal_similarities():
    """Division-by-zero guard when every video in an anchor has identical sim."""
    df = _make_retrieval("a", ["X", "Y"], [0.5, 0.5])
    out = add_rank_and_norm(df, "small")
    # Should not raise; norm should be defined (0 or 1 — implementation-dependent)
    assert out["sim_norm_small"].notna().all()


# ---------------------------------------------------------------------------
# merge_rankers
# ---------------------------------------------------------------------------

def test_merge_rankers_outer_join_preserves_all_pairs(small, large):
    out = merge_rankers(small, large)
    # Union of YT_IDs: {A, B, C, D} = 4 distinct rows
    assert out["YT_ID"].nunique() == 4


def test_merge_rankers_missing_ranker_yields_nan(small, large):
    out = merge_rankers(small, large)
    # C is in small only → rank_large should be NaN
    c = out[out["YT_ID"] == "C"].iloc[0]
    assert pd.isna(c["rank_large"])
    # D is in large only → rank_small should be NaN
    d = out[out["YT_ID"] == "D"].iloc[0]
    assert pd.isna(d["rank_small"])


# ---------------------------------------------------------------------------
# fusion_rrf
# ---------------------------------------------------------------------------

def test_fusion_rrf_score_formula(merged):
    out = fusion_rrf(merged, top_k=10, k_rrf=60)
    # Video A: rank_small=1, rank_large=2 → score = 1/61 + 1/62
    a = out[out["YT_ID"] == "A"].iloc[0]
    expected = 1 / 61 + 1 / 62
    assert a["score"] == pytest.approx(expected, rel=1e-6)


def test_fusion_rrf_missing_ranker_contributes_zero(merged):
    out = fusion_rrf(merged, top_k=10, k_rrf=60)
    # Video C: rank_small=3, rank_large=NaN → score = 1/63 + 0
    c = out[out["YT_ID"] == "C"].iloc[0]
    assert c["score"] == pytest.approx(1 / 63, rel=1e-6)


def test_fusion_rrf_truncates_to_top_k(merged):
    out = fusion_rrf(merged, top_k=2, k_rrf=60)
    # Only 2 videos per anchor should survive
    assert len(out[out["anchor"] == "anc1"]) == 2


# ---------------------------------------------------------------------------
# fusion_combsum
# ---------------------------------------------------------------------------

def test_fusion_combsum_handles_missing_ranker(merged):
    out = fusion_combsum(merged, top_k=10)
    # D is in large only — sim_norm_small is NaN → contributes 0 to score
    d = out[out["YT_ID"] == "D"].iloc[0]
    # D's large normalised similarity in the large fixture: 0.95 is max → 1.0
    assert d["score"] == pytest.approx(1.0, rel=1e-6)


def test_fusion_combsum_invariant_to_similarity_scale():
    """CombSUM uses min-max normalisation, so scaling all similarities by
    a positive constant must not change the ranking."""
    s1 = _make_retrieval("a", ["X", "Y", "Z"], [0.9, 0.8, 0.7])
    l1 = _make_retrieval("a", ["X", "Y", "Z"], [0.5, 0.4, 0.3])

    s2 = _make_retrieval("a", ["X", "Y", "Z"], [0.9, 0.8, 0.7])
    l2 = _make_retrieval("a", ["X", "Y", "Z"], [50, 40, 30])  # 100x scaling

    o1 = fusion_combsum(merge_rankers(s1, l1), top_k=10).sort_values("fused_rank")
    o2 = fusion_combsum(merge_rankers(s2, l2), top_k=10).sort_values("fused_rank")
    assert o1["YT_ID"].tolist() == o2["YT_ID"].tolist()


# ---------------------------------------------------------------------------
# fusion_union — recall-max behaviour
# ---------------------------------------------------------------------------

def test_fusion_union_preserves_all_videos(merged):
    out = fusion_union(merged)
    # All 4 distinct videos from the union of rankers must appear
    assert set(out["YT_ID"]) == {"A", "B", "C", "D"}


def test_fusion_union_consensus_video_ranks_higher_than_singleton():
    """A video at rank 1 in both rankers must outrank a video at rank 1
    in only one ranker (the consensus pick wins on best_rank tie via
    max_sim if needed)."""
    merged = pd.DataFrame({
        "anchor":     ["a", "a"],
        "YT_ID":      ["consensus", "singleton"],
        "rank_small": [1, np.nan],
        "rank_large": [1, 1],
        "sim_small":  [0.9, np.nan],
        "sim_large":  [0.9, 0.7],
        "sim_norm_small": [1.0, np.nan],
        "sim_norm_large": [1.0, 0.0],
    })
    out = fusion_union(merged).sort_values("fused_rank")
    assert out.iloc[0]["YT_ID"] == "consensus"


def test_fusion_union_per_anchor_independence():
    """Each anchor gets its own fused_rank starting from 1."""
    merged = pd.DataFrame({
        "anchor":     ["a", "a", "b", "b"],
        "YT_ID":      ["v1", "v2", "v3", "v4"],
        "rank_small": [1, 2, 1, 2],
        "rank_large": [1, 2, 1, 2],
        "sim_small":  [0.9, 0.8, 0.7, 0.6],
        "sim_large":  [0.9, 0.8, 0.7, 0.6],
        "sim_norm_small": [1.0, 0.0, 1.0, 0.0],
        "sim_norm_large": [1.0, 0.0, 1.0, 0.0],
    })
    out = fusion_union(merged)
    for anchor in ["a", "b"]:
        ranks = sorted(out[out["anchor"] == anchor]["fused_rank"].tolist())
        assert ranks == [1, 2], f"anchor {anchor!r} expected [1,2], got {ranks}"
