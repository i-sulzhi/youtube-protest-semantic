"""Smoke tests for the analytics layer (master dataset + module contract).

Skipped wholesale when the master is absent (fresh checkout — outputs/ is
gitignored). Pins the master's integrity invariants so feature drift or a
broken join fails loudly before any analysis is trusted.

Run with:
    .venv_v2/bin/pytest tests/test_analytics_master.py -v
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent
MASTER = REPO / "outputs" / "analytics" / "master.csv.gz"

pytestmark = pytest.mark.skipif(not MASTER.exists(),
                                reason="master not built (make analytics-master)")

KEY_COLS = [
    "YT_ID", "publish_year", "country_combo", "protest_anywhere",
    "views_total", "velocity_d7_z", "churned_90", "primary_term_canon",
    "broker_score", "hyper_unique_terms", "in_pool", "in_gated_index",
    "relevance_llm", "gold_label", "distilled_label",
]


@pytest.fixture(scope="module")
def m() -> pd.DataFrame:
    return pd.read_csv(MASTER, low_memory=False)


def test_master_shape_and_key(m):
    assert len(m) == 21710
    assert m["YT_ID"].is_unique


def test_key_columns_present(m):
    missing = [c for c in KEY_COLS if c not in m.columns]
    assert not missing, f"master lost columns: {missing}"


def test_layer_coverage(m):
    assert int(m["in_pool"].sum()) == 1099
    assert int(m["in_gated_index"].sum()) == 387
    assert int(m["relevance_llm"].notna().sum()) == 1099
    assert m["gold_label"].notna().sum() >= 60


def test_gated_subset_of_pool(m):
    assert (m.loc[m["in_gated_index"], "in_pool"]).all()
    assert set(m.loc[m["in_gated_index"], "relevance_llm"]) <= {"direct", "indirect"}


def test_capture_rates_table():
    cr = pd.read_csv(REPO / "data" / "capture_rates.csv")
    assert (cr["capture_rate"] > 0).all() and (cr["capture_rate"] <= 1).all()
    # provenance: rates = in_corpus / all_politics from the 2026-06-10 DB audit
    calc = cr["in_corpus"] / cr["all_politics"]
    assert (abs(calc - cr["capture_rate"]) < 5e-4).all()
