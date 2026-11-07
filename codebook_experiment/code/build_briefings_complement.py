"""Build Prompt-A briefings for the 140 sample items NOT in the coding sheet.

Lets us run Claude on the full 200-item sample (60 already done in coding-sheet
briefings), so cross-model (Claude vs GPT) disagreement can be computed on N=200.

Outputs:
  mini_study/llm_input/briefing_promptA_extra{1..4}.md
  → predictions to mini_study/llm_predictions/claude_promptA_extra{1..4}.jsonl
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

import build_classification_briefings as bcb

REPO = Path(__file__).resolve().parent.parent
SAMPLE = REPO / "mini_study" / "sample.csv"
CODING = REPO / "mini_study" / "coding_sheet_for_human.csv"
OUT_DIR = REPO / "mini_study" / "llm_input"
PRED_DIR = REPO / "mini_study" / "llm_predictions"
N_CHUNKS = 4


def main():
    sample = pd.read_csv(SAMPLE, dtype=str, keep_default_na=False, na_values=[""])
    coding = pd.read_csv(CODING, dtype=str, keep_default_na=False, na_values=[""])
    done = set(coding["YT_ID"])
    extra = sample[~sample["YT_ID"].isin(done)].reset_index(drop=True)
    print(f"sample={len(sample)}  coding={len(done)}  complement={len(extra)}")

    items = extra.to_dict(orient="records")
    # split into N chunks
    size = (len(items) + N_CHUNKS - 1) // N_CHUNKS
    written = []
    for ci in range(N_CHUNKS):
        chunk = items[ci * size:(ci + 1) * size]
        if not chunk:
            continue
        out_jsonl = str(PRED_DIR / f"claude_promptA_extra{ci+1}.jsonl")
        briefing = bcb.make_briefing(chunk, "A", f"extra{ci+1}", bcb.PROMPT_A_INSTRUCTIONS, out_jsonl)
        path = OUT_DIR / f"briefing_promptA_extra{ci+1}.md"
        path.write_text(briefing, encoding="utf-8")
        written.append((str(path), out_jsonl, len(chunk)))
        print(f"  wrote {path.name} ({len(chunk)} items) → {Path(out_jsonl).name}")
    print(f"\n{len(written)} briefings.")


if __name__ == "__main__":
    main()
