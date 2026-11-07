"""Run every analytics module against the master dataset → INDEX.md.

Loads the master once, executes each an_<topic>.run(m), collects one-line
summaries into outputs/analytics/INDEX.md. New module = new an_*.py with
run(master) -> (path, summary); register it in MODULES below.

Run:  .venv_v2/bin/python analytics/run_all.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.lib import OUT, load_master, write_report  # noqa: E402
from analytics import (an_anchors, an_brokers, an_channels,  # noqa: E402
                       an_cohorts, an_temporal)

MODULES = [an_temporal, an_channels, an_anchors, an_cohorts, an_brokers]


def main():
    m = load_master()
    print(f"master: {len(m):,} rows × {len(m.columns)} cols\n")
    lines = ["# Analytics index", "",
             f"_Run {time.strftime('%Y-%m-%d %H:%M')}; master "
             f"{len(m):,} rows × {len(m.columns)} cols._", ""]
    for mod in MODULES:
        name = mod.__name__.split(".")[-1]
        try:
            path, summary = mod.run(m)
            print(f"  ✓ {name:14s} {summary}")
            lines.append(f"- [{name}]({Path(path).name}) — {summary}")
        except Exception as e:  # noqa: BLE001 — one module must not kill the run
            print(f"  ✗ {name:14s} FAILED: {e}")
            lines.append(f"- {name} — **FAILED**: {e}")
    lines += ["", "Ad-hoc questions: `analytics/slice.py` "
              "(see its docstring for examples)."]
    write_report("INDEX", lines)
    print(f"\nwrote {OUT/'INDEX.md'}")


if __name__ == "__main__":
    main()
