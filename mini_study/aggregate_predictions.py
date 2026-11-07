"""Aggregate 4 Claude-annotator JSONL outputs into a unified predictions CSV.

Inputs:
  mini_study/llm_predictions/claude_prompt{A,B}_chunk{1,2}.jsonl

Outputs:
  mini_study/llm_predictions.csv  — long format: yt_id × model × prompt × label
  mini_study/cross_prompt_disagreement.md  — Day 1 deliverable: % items where
    Prompt A ≠ Prompt B (proxy for Yang & Wang 2025 "Benchmark Illusion" check)

Schema:
  yt_id, model, prompt, label, confidence, rationale, anchor, language_norm,
  country_combo, protest_anywhere, TITLE
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
PRED_DIR = REPO / "mini_study" / "llm_predictions"
CODING_SHEET = REPO / "mini_study" / "coding_sheet_for_human.csv"
LONG_CSV = REPO / "mini_study" / "llm_predictions.csv"
WIDE_CSV = REPO / "mini_study" / "llm_predictions_wide.csv"
DISAGREE_MD = REPO / "mini_study" / "cross_prompt_disagreement.md"

VALID_LABELS = {
    "prokremlowski",
    "antywojenny",
    "prozachodni",
    "bialorusko-narodowy",
    "neutralny-informacyjny",
}


def load_jsonl(path: Path):
    rows = []
    if not path.exists():
        print(f"  [missing] {path}")
        return rows
    with path.open("r", encoding="utf-8") as f:
        for ln_num, ln in enumerate(f, start=1):
            ln = ln.strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
            except json.JSONDecodeError as e:
                print(f"  [bad json] {path.name}:{ln_num}: {e}")
                continue
            rows.append(obj)
    return rows


def normalize_label(lbl: str) -> str:
    if not lbl:
        return ""
    s = str(lbl).strip().lower()
    # tolerate variants
    s = s.replace("białorusko", "bialorusko").replace("ż", "z").replace("ł", "l")
    if s in VALID_LABELS:
        return s
    # try matching by prefix
    for v in VALID_LABELS:
        if s.startswith(v.split("-")[0]):
            return v
    return s  # leave as-is for diagnostics


def main():
    coding = pd.read_csv(CODING_SHEET, dtype=str, keep_default_na=False, na_values=[""])
    meta_cols = ["YT_ID", "anchor", "language_norm", "country_combo", "protest_anywhere", "TITLE"]
    meta = coding[meta_cols].rename(columns={"YT_ID": "yt_id"})

    long_rows = []
    for prompt_letter in ["A", "B"]:
        for chunk in [1, 2]:
            path = PRED_DIR / f"claude_prompt{prompt_letter}_chunk{chunk}.jsonl"
            rows = load_jsonl(path)
            print(f"  loaded {len(rows):>2} from claude_prompt{prompt_letter}_chunk{chunk}.jsonl")
            for r in rows:
                lbl = normalize_label(r.get("label", ""))
                long_rows.append({
                    "yt_id": r.get("yt_id"),
                    "model": "claude-agent",
                    "prompt": prompt_letter,
                    "chunk": chunk,
                    "label": lbl,
                    "label_valid": lbl in VALID_LABELS,
                    "confidence": r.get("confidence"),
                    "rationale": (r.get("rationale") or "").strip(),
                })

    df = pd.DataFrame(long_rows)
    if df.empty:
        print("\nNo predictions yet. Re-run after agents finish.")
        return

    # Join metadata
    df = df.merge(meta, on="yt_id", how="left")

    LONG_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(LONG_CSV, index=False)
    print(f"\nWrote {LONG_CSV} ({len(df)} rows)")

    # Wide form: yt_id × prompt
    wide = df.pivot_table(
        index=["yt_id", "anchor", "language_norm", "country_combo", "protest_anywhere", "TITLE"],
        columns="prompt",
        values="label",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None
    if "A" in wide.columns and "B" in wide.columns:
        wide["agreement"] = wide["A"] == wide["B"]
    wide.to_csv(WIDE_CSV, index=False)
    print(f"Wrote {WIDE_CSV} ({len(wide)} unique items)")

    # Cross-prompt disagreement report
    report = []
    report.append("# Cross-prompt disagreement — Claude-as-annotator pass\n")
    report.append(f"Source: 4 sub-agent runs ({len(df)} total predictions, {len(wide)} unique items)\n")
    report.append("This is the **prompt-stability** check that proxies the Yang & Wang 2025 "
                  "\"Benchmark Illusion\" finding for a single-model setting. A high "
                  "disagreement rate between Prompt A (terse/structured) and Prompt B "
                  "(CoT/discursive) is itself a researcher-degree-of-freedom signal.\n\n")

    # Overall agreement
    if "agreement" in wide.columns:
        agree_n = wide["agreement"].sum()
        total = len(wide)
        report.append(f"## Overall agreement\n")
        report.append(f"- Items where Prompt A == Prompt B: **{agree_n} / {total} ({100*agree_n/total:.1f}%)**")
        report.append(f"- Disagreement rate: **{100*(total-agree_n)/total:.1f}%**\n")

        # Disagreement by anchor
        report.append("## Disagreement by anchor\n")
        for a, sub in wide.groupby("anchor"):
            n = len(sub)
            d = (~sub["agreement"]).sum()
            report.append(f"- `{a}`: {d}/{n} disagree ({100*d/n:.1f}%)")
        report.append("")

        # Label transitions A → B (only where they differ)
        report.append("## Label transitions A → B (mismatches only)\n")
        mismatches = wide[~wide["agreement"]]
        if len(mismatches):
            trans = mismatches.groupby(["A", "B"]).size().sort_values(ascending=False)
            report.append("| Prompt A | Prompt B | n |")
            report.append("|---|---|---:|")
            for (a, b), n in trans.items():
                report.append(f"| `{a}` | `{b}` | {n} |")
        report.append("")

        # Confidence on mismatches vs matches
        df_pivot_conf = df.pivot_table(
            index="yt_id", columns="prompt", values="confidence", aggfunc="first"
        ).reset_index()
        if "A" in df_pivot_conf.columns and "B" in df_pivot_conf.columns:
            df_pivot_conf = df_pivot_conf.merge(wide[["yt_id", "agreement"]], on="yt_id")
            mean_conf_match_A = df_pivot_conf.loc[df_pivot_conf["agreement"], "A"].astype(float).mean()
            mean_conf_mismatch_A = df_pivot_conf.loc[~df_pivot_conf["agreement"], "A"].astype(float).mean()
            mean_conf_match_B = df_pivot_conf.loc[df_pivot_conf["agreement"], "B"].astype(float).mean()
            mean_conf_mismatch_B = df_pivot_conf.loc[~df_pivot_conf["agreement"], "B"].astype(float).mean()
            report.append("## Mean confidence on matched vs mismatched items\n")
            report.append(f"- Prompt A: matched={mean_conf_match_A:.2f}, mismatched={mean_conf_mismatch_A:.2f}")
            report.append(f"- Prompt B: matched={mean_conf_match_B:.2f}, mismatched={mean_conf_mismatch_B:.2f}\n")
            report.append("If mismatched items consistently have lower confidence than matched items, "
                          "the model has *some* awareness of its own uncertainty — useful for confidence-gated "
                          "human review (cf. Gligorić et al. 2024 PPI extension to unconfident LLM labels).\n")

    # Per-label distribution A vs B
    report.append("## Label distribution per prompt\n")
    dist = df.groupby(["prompt", "label"]).size().unstack(fill_value=0)
    report.append("```")
    report.append(dist.to_string())
    report.append("```\n")

    # Validity check
    invalid = df[~df["label_valid"]]
    if len(invalid):
        report.append(f"## ⚠ {len(invalid)} predictions with non-canonical labels\n")
        report.append("```")
        report.append(invalid[["yt_id","prompt","label"]].to_string())
        report.append("```\n")

    DISAGREE_MD.write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote {DISAGREE_MD}")

    # Headline
    if "agreement" in wide.columns:
        d = (~wide["agreement"]).sum()
        n = len(wide)
        print(f"\n>>> Cross-prompt disagreement: {d}/{n} = {100*d/n:.1f}%")


if __name__ == "__main__":
    main()
