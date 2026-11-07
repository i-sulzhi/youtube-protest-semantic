"""Build the REAL human coding sheet from the manual coding export.

Source of truth: AGH_project/coding_progress.json — dr Sulzhytski's manual
labels for all 60 sampled items (exported from coding_ui.html). This replaces
the SELF-TEST stand-in (claude_A) used while real labels did not yet exist.

Output: mini_study/coding_sheet_for_human_FILLED.csv
Columns: YT_ID, human_label, coding_confidence, coding_notes
  (compute_metrics.py consumes YT_ID + human_label; the rest is provenance.)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

# Sibling projects live next to this repo (nexus/code on the Mac, C:\code on the PC);
# override with the NEXUS_CODE environment variable.
CODE_ROOT = Path(os.environ.get("NEXUS_CODE", Path(__file__).resolve().parents[2]))


REPO = Path(__file__).resolve().parent.parent
PROGRESS = (CODE_ROOT / "AGH_project" / "coding_progress.json")
WIDE = REPO / "mini_study" / "all_predictions_wide.csv"
OUT = REPO / "mini_study" / "coding_sheet_for_human_FILLED.csv"

VALID = {
    "prokremlowski", "antywojenny", "prozachodni",
    "bialorusko-narodowy", "neutralny-informacyjny",
}


def main():
    prog = json.loads(PROGRESS.read_text(encoding="utf-8"))
    data = prog["data"]

    rows = []
    for yt_id, rec in data.items():
        label = (rec.get("label") or "").strip().lower()
        label = label.replace("ł", "l").replace("białorusko", "bialorusko")
        if label not in VALID:
            raise ValueError(f"{yt_id}: unexpected label {label!r}")
        rows.append({
            "YT_ID": yt_id,
            "human_label": label,
            "coding_confidence": rec.get("confidence", ""),
            "coding_notes": (rec.get("notes") or "").replace("\n", " ").strip(),
        })

    df = pd.DataFrame(rows)

    # Sanity: every ID must exist in the prediction set, and vice versa.
    wide_ids = set(pd.read_csv(WIDE)["yt_id"])
    sheet_ids = set(df["YT_ID"])
    assert sheet_ids == wide_ids, (
        f"ID mismatch — only-in-sheet={sheet_ids - wide_ids}, "
        f"only-in-wide={wide_ids - sheet_ids}"
    )
    assert len(df) == 60, f"expected 60 rows, got {len(df)}"
    assert df["human_label"].notna().all() and (df["human_label"] != "").all()

    df.to_csv(OUT, index=False)
    print(f"Wrote {OUT} ({len(df)} rows)")
    print(df["human_label"].value_counts().to_string())


if __name__ == "__main__":
    main()
