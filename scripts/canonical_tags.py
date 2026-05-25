"""Pure-function helpers for canonicalising raw YouTube tag strings.

This module deliberately performs no I/O beyond ``load_synonym_table``
so the canonicalisation rules can be unit-tested in isolation.

The pipeline is:
    raw_tag --canonicalise()--> folded --apply_synonyms(table)--> canonical

``canonicalise`` is deterministic and idempotent on its own output.
``apply_synonyms`` expects an input that has already been canonicalised.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path


_WS_RE = re.compile(r"\s+")


def canonicalise(tag: str) -> str:
    """Return a deterministic folded form of a raw tag.

    Steps:
      1. NFKC normalisation (collapses full-width, compatibility forms).
      2. ``casefold`` — locale-independent lowercasing (handles ``ß``,
         dotless-i, etc. correctly, unlike ``.lower()``).
      3. Strip + collapse internal whitespace runs to a single space.

    Empty input yields the empty string; the caller decides whether to
    drop it. The function is idempotent: ``canonicalise(canonicalise(t))
    == canonicalise(t)`` for any string ``t``.
    """
    if tag is None:
        return ""
    t = unicodedata.normalize("NFKC", tag).casefold().strip()
    t = _WS_RE.sub(" ", t)
    return t


def apply_synonyms(tag: str, synonyms: dict[str, str]) -> str:
    """Map a *canonicalised* tag through the synonym table.

    Unknown tags pass through unchanged. The table is expected to be
    keyed on canonicalised variants (see ``load_synonym_table``), so
    callers must canonicalise first.
    """
    return synonyms.get(tag, tag)


def load_synonym_table(path: str | Path) -> dict[str, str]:
    """Read a two-column (canonical, variant) CSV into a variant→canonical dict.

    Both columns are canonicalised on load so lookups against
    ``apply_synonyms`` match irrespective of how the CSV was written.

    Raises ``ValueError`` on duplicate variant rows that disagree on the
    canonical form — a curated table should be internally consistent.
    """
    path = Path(path)
    table: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            canon = canonicalise(row["canonical"])
            variant = canonicalise(row["variant"])
            if not canon or not variant:
                continue
            if variant in table and table[variant] != canon:
                raise ValueError(
                    f"synonym table conflict for variant {variant!r}: "
                    f"{table[variant]!r} vs {canon!r}"
                )
            table[variant] = canon
    return table
