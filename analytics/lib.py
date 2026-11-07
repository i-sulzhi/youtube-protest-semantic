"""Shared analytics library — load the master dataset, write reports, figures.

Every analytical task starts from ONE canonical table (build_master.py →
outputs/analytics/master.csv.gz, 21,710 rows × everything the pipeline knows
per video). Modules in this package read it via load_master(), emit a markdown
report into outputs/analytics/ and optional PNGs into figures/analytics/.

Conventions:
  * a module = an_<topic>.py exposing run(master) -> (report_path, one_liner);
  * reports are self-contained markdown with provenance lines;
  * capture-rate correction (the 7.7% funnel, ARCHITECTURE §2) lives here so
    every temporal claim can be sampling-aware.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "outputs" / "analytics"
FIGS = REPO / "figures" / "analytics"
MASTER = OUT / "master.csv.gz"
CAPTURE_RATES = REPO / "data" / "capture_rates.csv"


def load_master(columns: list[str] | None = None) -> pd.DataFrame:
    if not MASTER.exists():
        raise SystemExit(
            f"{MASTER} not found — build it first:\n"
            "    make analytics-master   (analytics/build_master.py)")
    return pd.read_csv(MASTER, usecols=columns, low_memory=False)


def write_report(name: str, lines: list[str]) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def save_fig(fig, name: str) -> Path | None:
    FIGS.mkdir(parents=True, exist_ok=True)
    path = FIGS / f"{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    return path


def md_table(df: pd.DataFrame, floatfmt: str = "{:.3f}") -> list[str]:
    """Markdown table without the tabulate dependency."""
    def fmt(v):
        if isinstance(v, float):
            return "" if pd.isna(v) else floatfmt.format(v)
        return str(v)
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |",
             "|" + "|".join("---:" if pd.api.types.is_numeric_dtype(df[c])
                            else "---" for c in cols) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(fmt(v) for v in row) + " |")
    return lines


def capture_weight(publish_year: pd.Series) -> pd.Series:
    """1 / capture_rate per publish year (≤2019 pooled into the 2019 row).

    Multiplying per-year counts by this weight estimates the count that would
    be observed if every discovered Politics video had been captured — an
    APPROXIMATE correction (assumes capture ⊥ protest-ness within a year, which
    survivorship makes optimistic). Quote as 'capture-corrected, see caveat'.
    """
    rates = pd.read_csv(CAPTURE_RATES).set_index("publish_year")["capture_rate"]
    yr = publish_year.clip(lower=rates.index.min())
    return 1.0 / yr.map(rates)


def gini(x) -> float:
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    if n == 0 or x.sum() == 0:
        return float("nan")
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def hhi(counts) -> float:
    s = pd.Series(counts, dtype=float)
    if s.sum() == 0:
        return float("nan")
    sh = s / s.sum()
    return float((sh ** 2).sum())


def provenance(extra: str = "") -> str:
    import time
    return (f"_Generated {time.strftime('%Y-%m-%d')} from "
            f"`outputs/analytics/master.csv.gz`. {extra}_")
