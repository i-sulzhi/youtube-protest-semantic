"""GPT-4o classification pass — the second LLM annotator for cross-model disagreement.

Reuses the EXACT same codebook + Prompt A/B formulations as the Claude pass
(imported from build_classification_briefings) so the comparison is apples-to-apples.

One API call per (item × prompt), structured JSON output. Model + version + prompt
+ timestamp logged into each JSONL line for reproducibility (Spirling 2023).

API key: read from OPENAI_API_KEY env var ONLY. Never written to disk.

Outputs:
  mini_study/llm_predictions/gpt_promptA.jsonl
  mini_study/llm_predictions/gpt_promptB.jsonl
  mini_study/llm_predictions/raw/gpt_{prompt}_{yt_id}.json  (raw API responses)

Usage:
  OPENAI_API_KEY=sk-... python mini_study/classify_with_gpt.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_classification_briefings import (  # noqa: E402
    CODEBOOK,
    PROMPT_A_INSTRUCTIONS,
    PROMPT_B_INSTRUCTIONS,
    DESC_TRUNC,
)

REPO = Path(__file__).resolve().parent.parent
CODING_SHEET = REPO / "mini_study" / "coding_sheet_for_human.csv"
PRED_DIR = REPO / "mini_study" / "llm_predictions"
RAW_DIR = PRED_DIR / "raw"

MODEL = "gpt-4o"  # resolves to latest gpt-4o snapshot; actual version logged per call
VALID_LABELS = [
    "prokremlowski",
    "antywojenny",
    "prozachodni",
    "bialorusko-narodowy",
    "neutralny-informacyjny",
]

JSON_SCHEMA_HINT = (
    'Return ONLY a JSON object with exactly these keys: '
    '"label" (one of: prokremlowski, antywojenny, prozachodni, bialorusko-narodowy, '
    'neutralny-informacyjny), "confidence" (integer 1, 2, or 3), '
    '"rationale" (one sentence). No other text.'
)


def build_system_prompt(prompt_letter: str) -> str:
    instr = PROMPT_A_INSTRUCTIONS if prompt_letter == "A" else PROMPT_B_INSTRUCTIONS
    return (
        "You are an expert annotator of multilingual Eastern-European political media "
        "acting as an LLM coder in a computational social science study.\n\n"
        + CODEBOOK
        + "\n\n"
        + instr
        + "\n\n"
        + JSON_SCHEMA_HINT
    )


def build_user_prompt(item: dict) -> str:
    def _s(v):
        if v is None:
            return ""
        try:
            import math
            if isinstance(v, float) and math.isnan(v):
                return ""
        except Exception:
            pass
        return str(v)

    title = _s(item.get("TITLE")).strip()
    desc = _s(item.get("DESCRIPTION")).strip()
    if len(desc) > DESC_TRUNC:
        desc = desc[:DESC_TRUNC] + "…[truncated]"
    return (
        f"Classify this YouTube video.\n\n"
        f"anchor: {item.get('anchor')}\n"
        f"language: {item.get('language_norm')}  country_combo: {item.get('country_combo')}  "
        f"protest_keyword: {item.get('protest_anywhere')}\n\n"
        f"TITLE: {title}\n\n"
        f"DESCRIPTION: {desc}"
    )


def normalize_label(lbl: str) -> str:
    if not lbl:
        return ""
    s = str(lbl).strip().lower().replace("białorusko", "bialorusko").replace("ł", "l")
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(CODING_SHEET), help="CSV with items (needs YT_ID, TITLE, DESCRIPTION, anchor, language_norm, country_combo, protest_anywhere)")
    ap.add_argument("--prompts", default="A,B", help="comma list of prompt letters to run")
    ap.add_argument("--suffix", default="", help="suffix for output filenames, e.g. _full200")
    args = ap.parse_args()

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("ERROR: OPENAI_API_KEY not set in environment.")
        sys.exit(1)

    client = OpenAI(api_key=key)
    df = pd.read_csv(args.input, dtype=str, keep_default_na=False, na_values=[""])
    items = df.to_dict(orient="records")
    prompts = [p.strip() for p in args.prompts.split(",") if p.strip()]
    print(f"Loaded {len(items)} items from {args.input}; prompts={prompts}; suffix='{args.suffix}'")

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for prompt_letter in prompts:
        system_prompt = build_system_prompt(prompt_letter)
        out_path = PRED_DIR / f"gpt_prompt{prompt_letter}{args.suffix}.jsonl"
        n_ok, n_err = 0, 0
        with out_path.open("w", encoding="utf-8") as fout:
            for i, item in enumerate(items, start=1):
                yt_id = item["YT_ID"]
                user_prompt = build_user_prompt(item)
                try:
                    resp = client.chat.completions.create(
                        model=MODEL,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.0,
                        response_format={"type": "json_object"},
                        max_tokens=200,
                    )
                    content = resp.choices[0].message.content
                    model_version = resp.model
                    parsed = json.loads(content)
                    label = normalize_label(parsed.get("label", ""))
                    conf = parsed.get("confidence", "")
                    rationale = (parsed.get("rationale") or "").strip()
                    # raw response for reproducibility
                    (RAW_DIR / f"gpt_prompt{prompt_letter}_{yt_id}.json").write_text(
                        json.dumps(
                            {
                                "yt_id": yt_id,
                                "model_version": model_version,
                                "prompt": prompt_letter,
                                "temperature": 0.0,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "raw_content": content,
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    fout.write(
                        json.dumps(
                            {
                                "yt_id": yt_id,
                                "model": "gpt-4o",
                                "model_version": model_version,
                                "prompt": prompt_letter,
                                "temperature": 0.0,
                                "label": label,
                                "confidence": conf,
                                "rationale": rationale,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    fout.flush()
                    n_ok += 1
                    if label not in VALID_LABELS:
                        print(f"  [warn] {yt_id} prompt {prompt_letter}: non-canonical label '{label}'")
                except Exception as e:
                    n_err += 1
                    print(f"  [error] {yt_id} prompt {prompt_letter}: {e}")
                    fout.write(
                        json.dumps(
                            {"yt_id": yt_id, "model": "gpt-4o", "prompt": prompt_letter,
                             "label": "", "confidence": "", "rationale": f"ERROR: {e}"},
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                if i % 10 == 0:
                    print(f"  prompt {prompt_letter}: {i}/{len(items)} done")
                time.sleep(0.2)  # gentle rate limit
        print(f"Prompt {prompt_letter}: {n_ok} ok, {n_err} errors → {out_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
