"""Block 2.1 — GPT-4o as a second gate annotator (annotator ensemble).

The codebook experiment measured ~25–28% cross-model disagreement on framing;
on the easier topic axis we expect less, but wherever Claude and GPT *disagree*
is exactly the gate's fragile zone — those items become the next human wave
(complementing the uncertainty-selected round-2 and the random audit wave).

Reuses the EXACT relevance codebook + instructions from the Claude briefings
(imported from build_relevance_briefings) so labels are comparable. One API
call per video, temperature 0, JSON output, checkpointed per chunk.

WAITS FOR INPUT: the OPENAI_API_KEY env var for fetching. `--report-only`
computes the agreement report from existing predictions without a key.

Cost estimate: 1,099 calls × (~700 in + ~60 out tokens) ≈ $3–4 on gpt-4o.

Run from project root:
    OPENAI_API_KEY=... .venv_v2/bin/python scripts/gate_ensemble.py
    .venv_v2/bin/python scripts/gate_ensemble.py --report-only
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_relevance_briefings import CODEBOOK, INSTRUCTIONS, DESC_TRUNC  # noqa: E402

LABELS = ["direct", "indirect", "absent"]
MODEL = "gpt-4o"
SYSTEM = (CODEBOOK + "\n" + INSTRUCTIONS +
          '\nReturn ONLY a JSON object: {"protest_relevance": "direct|indirect|absent", '
          '"confidence": 1|2|3, "rationale": "one sentence"}.')


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--index", default="outputs/stage_e/protest_index.csv")
    p.add_argument("--pool", default="outputs/retrieval_nway/all_sources_combined.csv")
    p.add_argument("--claude-glob",
                   default="outputs/stage_e/relevance_pred/claude_chunk*.jsonl")
    p.add_argument("--out-dir", default="outputs/stage_e/relevance_pred_gpt")
    p.add_argument("--gold", default="mini_study/coding_layer2.csv")
    p.add_argument("--report", default="outputs/stage_e/ensemble_report.md")
    p.add_argument("--disagreements",
                   default="outputs/stage_e/ensemble_disagreements.csv")
    p.add_argument("--limit", type=int, default=None, help="cap calls this run")
    p.add_argument("--report-only", action="store_true")
    return p.parse_args()


def load_jsonls(pattern: str) -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(pattern)):
        for line in open(f, encoding="utf-8"):
            if line.strip():
                rows.append(json.loads(line))
    return pd.DataFrame(rows).drop_duplicates("yt_id", keep="first") if rows else pd.DataFrame()


def fetch(a, todo: pd.DataFrame, out_dir: Path):
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "OPENAI_API_KEY is not set — fetching needs it (predictions are "
            "checkpointed; rerun is safe). For the agreement report on existing "
            "predictions use --report-only.")
    from openai import OpenAI
    client = OpenAI()
    out_dir.mkdir(parents=True, exist_ok=True)
    chunk_path = out_dir / f"gpt_chunk_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
    n = 0
    with chunk_path.open("a", encoding="utf-8") as out:
        for r in todo.itertuples():
            user = (f"TITLE: {r.TITLE}\n"
                    f"DESCRIPTION: {(r.DESCRIPTION or '')[:DESC_TRUNC]}")
            try:
                resp = client.chat.completions.create(
                    model=MODEL, temperature=0,
                    response_format={"type": "json_object"},
                    messages=[{"role": "system", "content": SYSTEM},
                              {"role": "user", "content": user}])
                d = json.loads(resp.choices[0].message.content)
                rec = {"yt_id": r.YT_ID,
                       "protest_relevance": str(d.get("protest_relevance", "")).lower(),
                       "confidence": int(d.get("confidence", 1)),
                       "rationale": d.get("rationale", ""),
                       "model": resp.model}
                if rec["protest_relevance"] not in LABELS:
                    rec["protest_relevance"] = "absent"
                    rec["confidence"] = 1
            except Exception as e:  # noqa: BLE001 — log & continue, checkpointed
                print(f"      ✗ {r.YT_ID}: {e}")
                continue
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            n += 1
            if n % 50 == 0:
                print(f"      … {n}/{len(todo)}")
    print(f"      fetched {n} this run → {chunk_path}")


def main():
    a = parse_args()
    out_dir = Path(a.out_dir)

    idx = pd.read_csv(a.index, usecols=["YT_ID"])
    pool = pd.read_csv(a.pool).drop_duplicates("YT_ID")[["YT_ID", "TITLE", "DESCRIPTION"]]
    pool = idx.merge(pool, on="YT_ID", how="left")

    gpt = load_jsonls(str(out_dir / "gpt_chunk_*.jsonl"))
    have = set(gpt["yt_id"]) if len(gpt) else set()
    todo = pool[~pool["YT_ID"].isin(have)]
    print(f"[1/3] GPT labels: {len(have)}/{len(pool)} done, {len(todo)} to fetch")

    if not a.report_only and len(todo):
        fetch(a, todo.head(a.limit) if a.limit else todo, out_dir)
        gpt = load_jsonls(str(out_dir / "gpt_chunk_*.jsonl"))

    if not len(gpt):
        raise SystemExit("No GPT predictions yet — run with OPENAI_API_KEY set.")

    # --- agreement vs Claude ----------------------------------------------- #
    from sklearn.metrics import cohen_kappa_score
    cl = load_jsonls(a.claude_glob)[["yt_id", "protest_relevance", "confidence"]]
    m = cl.merge(gpt[["yt_id", "protest_relevance", "confidence"]],
                 on="yt_id", suffixes=("_claude", "_gpt"))
    agree = (m["protest_relevance_claude"] == m["protest_relevance_gpt"])
    k = cohen_kappa_score(m["protest_relevance_claude"], m["protest_relevance_gpt"])
    print(f"[2/3] Claude×GPT on {len(m)}: agreement {100*agree.mean():.1f}%, κ={k:.3f}")
    conf = pd.crosstab(m["protest_relevance_claude"], m["protest_relevance_gpt"])

    dis = m[~agree].copy()
    pool_t = pool.set_index("YT_ID")["TITLE"]
    dis["TITLE"] = dis["yt_id"].map(pool_t)
    dis.to_csv(a.disagreements, index=False)

    # gold: does 2-model agreement predict correctness?
    gold = pd.read_csv(a.gold)[["yt_id", "protest_relevance"]].rename(
        columns={"protest_relevance": "human"})
    g = m.merge(gold, on="yt_id", how="inner")
    lines_gold = []
    if len(g):
        ag, dg = g[g.protest_relevance_claude == g.protest_relevance_gpt], \
                 g[g.protest_relevance_claude != g.protest_relevance_gpt]
        acc_ag = (ag["protest_relevance_claude"] == ag["human"]).mean() if len(ag) else float("nan")
        acc_dg = (dg["protest_relevance_claude"] == dg["human"]).mean() if len(dg) else float("nan")
        print(f"      gold check: Claude acc when models agree {100*acc_ag:.0f}% "
              f"(n={len(ag)}) vs when they disagree {100*acc_dg:.0f}% (n={len(dg)})")
        lines_gold = [
            "## Gold check — agreement as a confidence signal", "",
            f"| models | n | Claude acc vs human |", "|---|---:|---:|",
            f"| agree | {len(ag)} | {100*acc_ag:.0f}% |",
            f"| disagree | {len(dg)} | {100*acc_dg:.0f}% |", ""]

    L = ["# Gate ensemble — Claude × GPT-4o on the protest_relevance axis", "",
         f"{len(m)} videos double-labelled. Agreement **{100*agree.mean():.1f}%**, "
         f"κ **{k:.3f}**.", "",
         "## Confusion (rows = Claude, cols = GPT)", "",
         "```", conf.to_string(), "```", "",
         *lines_gold,
         f"## Disagreements → next human wave", "",
         f"{len(dis)} items in `{a.disagreements}` — route to the PI after the "
         "round-2 + audit waves (they are the model-uncertainty complement to "
         "the uncertainty- and random-selected waves).",
         ]
    Path(a.report).write_text("\n".join(L), encoding="utf-8")
    print(f"[3/3] wrote {a.report}\n      wrote {a.disagreements} ({len(dis)} items)")


if __name__ == "__main__":
    main()
