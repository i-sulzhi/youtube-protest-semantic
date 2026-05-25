"""Unit tests for canonical_tags helpers used by build_canonical_tag_map.

Run with:
    .venv_v2/bin/pytest tests/test_canonical_tags.py -v
"""
from __future__ import annotations

from pathlib import Path

import pytest

from canonical_tags import apply_synonyms, canonicalise, load_synonym_table


REPO_ROOT = Path(__file__).resolve().parent.parent
SYNONYMS_CSV = REPO_ROOT / "data" / "tag_synonyms.csv"


# ---------------------------------------------------------------------------
# canonicalise
# ---------------------------------------------------------------------------

def test_case_folding_collapses_upper_lower_mixed():
    assert canonicalise("PUTIN") == "putin"
    assert canonicalise("Putin") == "putin"
    assert canonicalise("putin") == "putin"


def test_whitespace_trimmed_and_collapsed():
    assert canonicalise("  putin  ") == "putin"
    assert canonicalise("foo   bar") == "foo bar"
    assert canonicalise("\tfoo\nbar\t") == "foo bar"


def test_nfkc_folds_compatibility_forms():
    # full-width digit '１' -> ASCII '1'
    assert canonicalise("BY-２０２０") == "by-2020"
    # ligature 'ﬃ' -> 'ffi'
    assert canonicalise("oﬃcial") == "official"


def test_casefold_handles_eszett_and_unique_unicode():
    # casefold maps 'ß' to 'ss' (lower() leaves it as 'ß')
    assert canonicalise("WEIẞRUSSLAND") == "weissrussland"
    assert canonicalise("weißrussland") == "weissrussland"


def test_empty_input_returns_empty():
    assert canonicalise("") == ""
    assert canonicalise(None) == ""
    assert canonicalise("   ") == ""


def test_canonicalise_is_idempotent():
    for raw in ["Putin", " WEIẞRUSSLAND ", "foo  bar", "BY-２０２０"]:
        once = canonicalise(raw)
        assert canonicalise(once) == once


# ---------------------------------------------------------------------------
# apply_synonyms
# ---------------------------------------------------------------------------

def test_apply_synonyms_maps_known_variant():
    table = {"путин": "putin", "навальный": "navalny"}
    assert apply_synonyms("путин", table) == "putin"
    assert apply_synonyms("навальный", table) == "navalny"


def test_apply_synonyms_passes_unknown_through():
    table = {"путин": "putin"}
    assert apply_synonyms("какой-то-тег", table) == "какой-то-тег"
    assert apply_synonyms("", table) == ""


# ---------------------------------------------------------------------------
# load_synonym_table — integration with the curated CSV
# ---------------------------------------------------------------------------

def test_load_synonym_table_reads_curated_csv():
    table = load_synonym_table(SYNONYMS_CSV)
    # Several anchor terms must collapse to a single canonical form
    assert table["путин"] == "putin"
    assert table["навальный"] == "navalny"
    assert table["лукашенко"] == "lukashenko"
    assert table["лукашэнка"] == "lukashenko"  # Belarusian spelling
    assert table["беларусь"] == "belarus"
    assert table["weissrussland"] == "belarus"  # casefolded form
    assert table["украина"] == "ukraine"
    assert table["україна"] == "ukraine"


def test_load_synonym_table_keys_are_canonical():
    """Every key in the loaded table should be invariant under canonicalise()."""
    table = load_synonym_table(SYNONYMS_CSV)
    for variant in table:
        assert canonicalise(variant) == variant


def test_load_synonym_table_detects_conflicts(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "canonical,variant\n"
        "putin,путин\n"
        "navalny,путин\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="conflict"):
        load_synonym_table(bad)


# ---------------------------------------------------------------------------
# End-to-end: canonicalise -> apply_synonyms, mirroring script behaviour
# ---------------------------------------------------------------------------

def test_pipeline_collapses_cross_script_variants():
    table = load_synonym_table(SYNONYMS_CSV)

    def fold(raw: str) -> str:
        return apply_synonyms(canonicalise(raw), table)

    # Mixed-case Cyrillic and Latin must both reach the same canonical
    assert fold("ПУТИН") == fold("Putin") == fold("путин") == "putin"
    assert fold("Лукашэнка") == fold("LUKASHENKO") == "lukashenko"
    assert fold("Weißrussland") == fold("БЕЛАРУСЬ") == "belarus"
