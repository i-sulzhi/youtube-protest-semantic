"""Aggregate ALL annotator passes (Claude + GPT-4o, prompts A + B) and compute
the cross-model / cross-prompt disagreement matrix — the core empirical material
for the talk's slide 10 (Yang & Wang 2025 "Benchmark Illusion").

Inputs:
  mini_study/llm_predictions/claude_prompt{A,B}_chunk{1,2}.jsonl  (Claude annotator)
  mini_study/llm_predictions/gpt_prompt{A,B}.jsonl                 (GPT-4o annotator)

Outputs:
  mini_study/all_predictions.csv          — long format, 4 annotator configs × 60 items
  mini_study/all_predictions_wide.csv     — yt_id × {claude_A, claude_B, gpt_A, gpt_B}
  mini_study/cross_model_disagreement.md  — the headline report
"""
from __future__ import annotations

import json
import itertools
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
PRED_DIR = REPO / "mini_study" / "llm_predictions"
CODING_SHEET = REPO / "mini_study" / "coding_sheet_for_human.csv"
LONG_CSV = REPO / "mini_study" / "all_predictions.csv"
WIDE_CSV = REPO / "mini_study" / "all_predictions_wide.csv"
REPORT_MD = REPO / "mini_study" / "cross_model_disagreement.md"

VALID = ["prokremlowski", "antywojenny", "prozachodni", "bialorusko-narodowy", "neutralny-informacyjny"]


def norm(lbl):
    if not lbl:
        return ""
    s = str(lbl).strip().lower().replace("białorusko", "bialorusko").replace("ł", "l")
    for v in VALID:
        if s == v:
            return v
        if s.startswith(v.split("-")[0]):
            return v
    return s


def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
    return rows


def main():
    coding = pd.read_csv(CODING_SHEET, dtype=str, keep_default_na=False, na_values=[""])
    meta = coding[["YT_ID", "anchor", "language_norm", "country_combo", "protest_anywhere", "TITLE"]].rename(
        columns={"YT_ID": "yt_id"}
    )

    long_rows = []
    # Claude: 2 prompts × 2 chunks
    for p in ["A", "B"]:
        for ch in [1, 2]:
            for r in load_jsonl(PRED_DIR / f"claude_prompt{p}_chunk{ch}.jsonl"):
                long_rows.append({
                    "yt_id": r.get("yt_id"), "model": "claude", "prompt": p,
                    "config": f"claude_{p}", "label": norm(r.get("label", "")),
                    "confidence": r.get("confidence"), "rationale": (r.get("rationale") or "").strip(),
                })
    # GPT: 2 prompts
    for p in ["A", "B"]:
        for r in load_jsonl(PRED_DIR / f"gpt_prompt{p}.jsonl"):
            long_rows.append({
                "yt_id": r.get("yt_id"), "model": "gpt-4o", "prompt": p,
                "config": f"gpt_{p}", "label": norm(r.get("label", "")),
                "confidence": r.get("confidence"), "rationale": (r.get("rationale") or "").strip(),
            })

    df = pd.DataFrame(long_rows).merge(meta, on="yt_id", how="left")
    df.to_csv(LONG_CSV, index=False)
    print(f"Wrote {LONG_CSV} ({len(df)} rows)")

    wide = df.pivot_table(index="yt_id", columns="config", values="label", aggfunc="first").reset_index()
    wide.columns.name = None
    wide = wide.merge(meta, on="yt_id", how="left")
    configs = ["claude_A", "claude_B", "gpt_A", "gpt_B"]
    configs = [c for c in configs if c in wide.columns]
    wide.to_csv(WIDE_CSV, index=False)
    print(f"Wrote {WIDE_CSV} ({len(wide)} items)")

    N = len(wide)
    R = []
    R.append("# Cross-model & cross-prompt disagreement — Claude vs GPT-4o\n")
    R.append(f"Source: 4 annotator configs × {N} items = {len(df)} predictions.\n")
    R.append("- **Claude** (agent mode): 2 prompt formulations (A=terse, B=CoT)")
    R.append("- **GPT-4o** (`gpt-4o-2024-08-06`, temp=0): same 2 prompt formulations, same codebook\n")
    R.append("This operationalises the Yang & Wang (2025) \"Benchmark Illusion\": two models with "
             "comparable benchmark accuracy can still disagree on a substantial share of items. We measure "
             "both cross-MODEL (Claude vs GPT, same prompt) and cross-PROMPT (within model) disagreement.\n")

    def pair_disagree(c1, c2):
        if c1 not in wide.columns or c2 not in wide.columns:
            return None
        mask = wide[c1].notna() & wide[c2].notna()
        d = (wide.loc[mask, c1] != wide.loc[mask, c2]).sum()
        n = mask.sum()
        return d, n, 100 * d / n if n else 0

    # Pairwise matrix
    R.append("## Pairwise disagreement matrix (% items where the two configs differ)\n")
    R.append("| | " + " | ".join(configs) + " |")
    R.append("|" + "---|" * (len(configs) + 1))
    for c1 in configs:
        row = [f"**{c1}**"]
        for c2 in configs:
            if c1 == c2:
                row.append("—")
            else:
                res = pair_disagree(c1, c2)
                row.append(f"{res[2]:.1f}%" if res else "n/a")
        R.append("| " + " | ".join(row) + " |")
    R.append("")

    # Headline cross-model (same prompt)
    R.append("## Headline numbers\n")
    cm_A = pair_disagree("claude_A", "gpt_A")
    cm_B = pair_disagree("claude_B", "gpt_B")
    cp_claude = pair_disagree("claude_A", "claude_B")
    cp_gpt = pair_disagree("gpt_A", "gpt_B")
    if cm_A:
        R.append(f"- **Cross-MODEL, prompt A** (Claude_A vs GPT_A): **{cm_A[0]}/{cm_A[1]} = {cm_A[2]:.1f}%**")
    if cm_B:
        R.append(f"- **Cross-MODEL, prompt B** (Claude_B vs GPT_B): **{cm_B[0]}/{cm_B[1]} = {cm_B[2]:.1f}%**")
    if cp_claude:
        R.append(f"- Cross-PROMPT, Claude (A vs B): {cp_claude[0]}/{cp_claude[1]} = {cp_claude[2]:.1f}%")
    if cp_gpt:
        R.append(f"- Cross-PROMPT, GPT-4o (A vs B): {cp_gpt[0]}/{cp_gpt[1]} = {cp_gpt[2]:.1f}%")
    R.append("")

    # Unanimity: all 4 agree
    R.append("## Four-way unanimity\n")
    if all(c in wide.columns for c in configs):
        allcols = wide[configs]
        unanimous = allcols.apply(lambda r: len(set(r.dropna())) == 1, axis=1).sum()
        R.append(f"- All 4 configs identical: **{unanimous}/{N} = {100*unanimous/N:.1f}%**")
        # majority exists
        def n_distinct(r):
            return len(set(r.dropna()))
        wide["_ndistinct"] = allcols.apply(n_distinct, axis=1)
        for k in sorted(wide["_ndistinct"].unique()):
            cnt = (wide["_ndistinct"] == k).sum()
            R.append(f"  - {k} distinct label(s) across 4 configs: {cnt} items ({100*cnt/N:.1f}%)")
    R.append("")

    # Disagreement by anchor (cross-model prompt A)
    R.append("## Cross-model (prompt A) disagreement by anchor\n")
    if "claude_A" in wide.columns and "gpt_A" in wide.columns:
        for a, sub in wide.groupby("anchor"):
            m = sub["claude_A"].notna() & sub["gpt_A"].notna()
            d = (sub.loc[m, "claude_A"] != sub.loc[m, "gpt_A"]).sum()
            n = m.sum()
            R.append(f"- `{a}`: {d}/{n} ({100*d/n if n else 0:.1f}%)")
    R.append("")

    # Label distribution per config
    R.append("## Label distribution per config\n")
    dist = df.groupby(["config", "label"]).size().unstack(fill_value=0)
    R.append("```")
    R.append(dist.to_string())
    R.append("```\n")

    # Confusion: Claude_A vs GPT_A transitions
    R.append("## Cross-model label transitions (prompt A, mismatches only)\n")
    if "claude_A" in wide.columns and "gpt_A" in wide.columns:
        mm = wide[(wide["claude_A"].notna()) & (wide["gpt_A"].notna()) & (wide["claude_A"] != wide["gpt_A"])]
        if len(mm):
            t = mm.groupby(["claude_A", "gpt_A"]).size().sort_values(ascending=False)
            R.append("| Claude_A | GPT_A | n |")
            R.append("|---|---|---:|")
            for (ca, ga), n in t.items():
                R.append(f"| `{ca}` | `{ga}` | {n} |")
    R.append("")

    R.append("## Interpretation for the talk\n")
    R.append("- Cross-model disagreement is the *model-choice researcher degree of freedom*: switching "
             "Claude→GPT changes the label on a measurable share of items even at temperature 0.")
    R.append("- Both models individually may achieve high agreement with humans (F1) and still disagree "
             "with **each other** — this is precisely the Benchmark Illusion. \"Which model is right?\" is "
             "a question for the researcher, not the model.")
    R.append("- Disagreement concentrates on specific category boundaries (see transitions table), which is "
             "where construct validity is weakest and where moderation / disinformation policy is most "
             "consequential.\n")

    REPORT_MD.write_text("\n".join(R), encoding="utf-8")
    print(f"Wrote {REPORT_MD}")

    # console headline
    if cm_A:
        print(f"\n>>> Cross-model (prompt A): {cm_A[2]:.1f}%   Cross-model (prompt B): {cm_B[2]:.1f}%")
        if all(c in wide.columns for c in configs):
            print(f">>> Four-way unanimity: {100*unanimous/N:.1f}%")


if __name__ == "__main__":
    main()
