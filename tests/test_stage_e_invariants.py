"""Golden-numbers regression tests for the Stage E chain.

Pins the validated production numbers (RESULTS_LOG, Stage E v2 + the
2026-06-10 validation pass) so silent breakage — dropped labels, membership
drift, metric regressions — fails loudly. If a number changes *on purpose*
(new gold, new pool), update the constant together with a RESULTS_LOG entry.

These tests read the artefacts in outputs/ (gitignored, Tier C/D); they are
skipped wholesale when the artefacts are absent (fresh checkout / CI).

Run with:
    .venv_v2/bin/pytest tests/test_stage_e_invariants.py -v
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent
INDEX = REPO / "outputs/stage_e/protest_index.csv"
GATED = REPO / "outputs/stage_e/protest_index_gated.csv"
NWAY = REPO / "outputs/retrieval_nway/all_sources_combined.csv"
PRED_GLOB = str(REPO / "outputs/stage_e/relevance_pred/claude_chunk*.jsonl")
GOLD = REPO / "mini_study/coding_layer2.csv"

# --- golden numbers (validated 2026-06-10) --------------------------------- #
POOL_N = 1099
GATED_N = 387
NEWLY_SURFACED = 708          # post «стачк» regex fix (was 709)
LLM_DIST = {"direct": 249, "indirect": 138, "absent": 712}
KAPPA3 = 0.611                # round-1 gold, 3-class
KAPPA2 = 0.735                # round-1 gold, binary
FEED_PROTEST_ANYWHERE = 2049  # post regex fix

pytestmark = pytest.mark.skipif(
    not (INDEX.exists() and GATED.exists() and NWAY.exists()),
    reason="Stage E outputs not on disk (gitignored Tier C/D artefacts)")


@pytest.fixture(scope="module")
def preds() -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(PRED_GLOB)):
        for line in open(f, encoding="utf-8"):
            if line.strip():
                rows.append(json.loads(line))
    return pd.DataFrame(rows).drop_duplicates(subset="yt_id", keep="first")


@pytest.fixture(scope="module")
def index() -> pd.DataFrame:
    return pd.read_csv(INDEX)


@pytest.fixture(scope="module")
def gated() -> pd.DataFrame:
    return pd.read_csv(GATED)


def test_pool_size_and_uniqueness(index):
    assert len(index) == POOL_N
    assert index["YT_ID"].nunique() == POOL_N


def test_every_pool_video_labelled(index, preds):
    assert set(index["YT_ID"]) == set(preds["yt_id"]), (
        "label coverage broken — sub-agent drop or stale JSONLs")


def test_llm_label_distribution(preds):
    assert preds["protest_relevance"].value_counts().to_dict() == LLM_DIST


def test_gated_membership_is_direct_union_indirect(index, preds, gated):
    kept = preds[preds["protest_relevance"].isin(["direct", "indirect"])]
    assert len(gated) == GATED_N
    assert set(gated["YT_ID"]) == set(kept["yt_id"])


def test_gated_sorted_by_composite(gated):
    assert gated["composite_score"].is_monotonic_decreasing
    assert list(gated["rank"]) == list(range(1, len(gated) + 1))


def test_newly_surfaced_count():
    nway = pd.read_csv(NWAY, usecols=["YT_ID", "protest_anywhere"])
    uniq = nway.drop_duplicates("YT_ID")
    assert len(uniq) == POOL_N
    assert int((~uniq["protest_anywhere"].astype(bool)).sum()) == NEWLY_SURFACED


def test_gate_kappa_on_round1_gold(preds):
    sklearn = pytest.importorskip("sklearn.metrics")
    gold = pd.read_csv(GOLD)[["yt_id", "protest_relevance"]]
    v = gold.merge(preds, on="yt_id", suffixes=("_h", "_l"))
    assert len(v) == 60
    k3 = sklearn.cohen_kappa_score(v["protest_relevance_h"], v["protest_relevance_l"])
    k2 = sklearn.cohen_kappa_score(v["protest_relevance_h"].ne("absent"),
                                   v["protest_relevance_l"].ne("absent"))
    assert k3 == pytest.approx(KAPPA3, abs=5e-4)
    assert k2 == pytest.approx(KAPPA2, abs=5e-4)


@pytest.mark.skipif(not (REPO / "outputs/v2_feed_ready.csv.gz").exists(),
                    reason="feed not on disk")
def test_feed_protest_flag_count():
    feed = pd.read_csv(REPO / "outputs/v2_feed_ready.csv.gz",
                       usecols=["YT_ID", "protest_anywhere"])
    assert len(feed) == 21710
    assert int(feed["protest_anywhere"].sum()) == FEED_PROTEST_ANYWHERE
