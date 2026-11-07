"""Build self-contained briefings for the Claude-as-annotator RELEVANCE gate.

Stage E precision layer. Unlike the mini_study framing pass (5 stance classes),
this classifies the *topic* axis only — `protest_relevance` ∈ {direct, indirect,
absent} — from the codebook v0.2 §2. Purpose: a hard gate that removes the ~70%
topic-noise (war/mobilisation/other) the recall-maximised retrieval pulled in.

One prompt formulation (cross-prompt stability is not the goal here — a single
decisive relevance call is). The pool is collapsed to one row per video; each
Claude sub-agent reads one chunk briefing and writes a JSONL of predictions.

Inputs:
  --pool   retrieval pool (default outputs/retrieval_e5large/topk_per_anchor.csv)
Outputs:
  outputs/stage_e/relevance_input/briefing_chunk{k}.md
  (each agent writes) outputs/stage_e/relevance_pred/claude_chunk{k}.jsonl
"""
from __future__ import annotations

import argparse
import glob
import json
import math
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
CHUNK_SIZE = 83          # 496 videos -> 6 chunks
DESC_TRUNC = 700


CODEBOOK = """\
## Codebook — protest_relevance (TOPIC axis, 3 mutually-exclusive values)

You judge ONE thing only: **is this video about a protest event?** This is a
question about TOPIC, not about political stance/framing. A pro-government and an
anti-government video about the same demonstration are BOTH `direct`.

**`direct`** — the video is *about* a protest: a demonstration, rally, march,
strike, picket, or the act of protesting itself; or footage/coverage of one.
Signals: "протесты", "митинг", "акция", "вышли на улицы", "демонстрация",
"забастовка", arrests *at a protest*, crowd/street footage. Example titles:
"Беларусь после выборов 2020: протесты и задержания"; "НАВАЛЬНЫЙ. ПРОТЕСТЫ 31.01".

**`indirect`** — protest is *peripheral but present*: the video is about something
adjacent to a protest — the state's reaction to a protest, repression/arrests as
the *aftermath* of protests, a counter-protest, sanctions or a migration crisis
that followed protests, court cases of protesters. The protest is the backdrop,
not the subject. Example: coverage of political-prisoner trials; the 2021 Belarus
border/migration crisis framed as protest fallout; "силовики после протестов".

**`absent`** — the video is NOT about a protest. The dominant subject is the war,
mobilisation, a politician's speech, a talk-show debate, military analysis,
elections, diplomacy, or anything else. Even if it mentions a protest in passing,
code `absent` when protest is not a subject of the video. Examples: a Putin
address; front-line war reporting; a studio talk-show about Lukashenko;
mobilisation explainers; apolitical content that slipped the Politics filter.

## Decision rules
1. Ask: *if I had to give this video a one-word topic, would it be "protest"?*
   Yes -> `direct`. "Protest-adjacent" (repression/reaction/aftermath) -> `indirect`.
   Something else (war/speech/analysis/election) -> `absent`.
2. TOPIC ≠ STANCE. Do not let pro/anti framing affect the relevance call.
3. You see only TITLE + DESCRIPTION (what the model sees). Judge from that text.
   If the text genuinely under-determines it, pick the most likely value and mark
   confidence 1.
4. Be decisive. Do not abstain. Exactly one value per item.
"""


INSTRUCTIONS = """\
## Your task

You are an expert annotator of multilingual Eastern-European political media
(Russian, Ukrainian, Belarusian, German, English). For each video, read TITLE and
DESCRIPTION and assign exactly ONE protest_relevance value: `direct`, `indirect`,
or `absent`, per the codebook above.

For each item output:
- `protest_relevance`: one of `direct` / `indirect` / `absent`
- `confidence`: integer 1 (low), 2 (medium), 3 (high)
- `rationale`: ONE short sentence naming the signal that drove the call
"""


def _s(v):
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    return str(v)


def fmt_item(it: dict, idx: int) -> str:
    title = _s(it.get("TITLE")).strip()
    desc = _s(it.get("DESCRIPTION")).strip()
    if len(desc) > DESC_TRUNC:
        desc = desc[:DESC_TRUNC] + "…[truncated]"
    return (
        f"### Item {idx}\n"
        f"- YT_ID: `{it['YT_ID']}`\n"
        f"- anchor: {it.get('primary_anchor')}  |  lang: {it.get('DEFAULT_AUDIO_LANG')}  |  "
        f"country: {it.get('country_combo')}  |  protest_keyword_in_text: {it.get('protest_anywhere')}\n"
        f"- **TITLE:** {title}\n"
        f"- **DESCRIPTION:** {desc}\n"
    )


def make_briefing(items: list, chunk_id: int, out_jsonl: str) -> str:
    yt_ids = ", ".join(f"`{it['YT_ID']}`" for it in items)
    body = "\n\n".join(fmt_item(it, i + 1) for i, it in enumerate(items))
    n = len(items)
    return f"""# Relevance-gate briefing — chunk {chunk_id}

You are acting as **Claude as an LLM annotator** for the Stage E precision gate of
a multilingual YouTube protest-retrieval pipeline. The recall-maximised retrieval
surfaced many videos that are not actually about protest; your labels let the
pipeline filter and re-rank them. Your labels are validated against a human-coded
gold set (Cohen's κ on the same axis), so apply the codebook faithfully.

**Your task:** classify the {n} items at the bottom of this briefing.

{CODEBOOK}

{INSTRUCTIONS}

## Output format

Write predictions to `{out_jsonl}` — one JSON object per line, in item order.
Each line is a single-line JSON object with exactly these keys:
```json
{{"yt_id": "ABC123def", "protest_relevance": "direct", "confidence": 2, "rationale": "Street footage of a post-election rally with arrests."}}
```

Required:
- `protest_relevance` ∈ {{`direct`, `indirect`, `absent`}}
- `confidence` ∈ {{1, 2, 3}}
- `rationale` non-empty

**Operational rules:**
- Use ONLY the `Write` tool. Do NOT use Bash, Web, or Read on other files.
- Process all {n} items, in order. Do not skip any.
- After writing the JSONL, output a one-line summary: count per value + any
  confidence-1 items.
- Do not modify any other file.

YT_IDs in this chunk (n={n}): {yt_ids}

---

## Items to classify

{body}
"""


def load_predicted_ids(pattern: str) -> set:
    """yt_ids that already have a relevance prediction (so we can skip them)."""
    ids = set()
    for f in sorted(glob.glob(pattern)):
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(json.loads(line)["yt_id"])
            except (json.JSONDecodeError, KeyError):
                continue
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", default="outputs/retrieval_e5large/topk_per_anchor.csv")
    ap.add_argument("--out-dir", default="outputs/stage_e")
    ap.add_argument("--exclude-pred-glob", default=None,
                    help="glob of existing prediction JSONLs; their yt_ids are "
                         "skipped so only NEW videos get briefings (incremental gate)")
    ap.add_argument("--chunk-offset", type=int, default=0,
                    help="start chunk numbering at offset+1 so new briefings/JSONLs "
                         "do not overwrite existing ones")
    args = ap.parse_args()

    pool = pd.read_csv(args.pool)
    pool["similarity"] = pd.to_numeric(pool["similarity"], errors="coerce")
    # one row per video = its best-similarity anchor row
    idx = pool.groupby("YT_ID")["similarity"].idxmax()
    df = pool.loc[idx].rename(columns={"anchor": "primary_anchor"}).reset_index(drop=True)
    df = df.sort_values("YT_ID").reset_index(drop=True)
    print(f"Pool collapsed to {len(df)} distinct videos")

    if args.exclude_pred_glob:
        done = load_predicted_ids(args.exclude_pred_glob)
        before = len(df)
        df = df[~df["YT_ID"].isin(done)].reset_index(drop=True)
        print(f"Excluding {len(done)} already-labelled yt_ids "
              f"({args.exclude_pred_glob}) -> {len(df)} NEW videos to brief "
              f"(was {before})")

    items = df.to_dict(orient="records")
    if not items:
        print("No new videos to brief — nothing to do.")
        return

    in_dir = Path(args.out_dir) / "relevance_input"
    pred_dir = Path(args.out_dir) / "relevance_pred"
    in_dir.mkdir(parents=True, exist_ok=True)
    pred_dir.mkdir(parents=True, exist_ok=True)

    chunks = [items[i:i + CHUNK_SIZE] for i in range(0, len(items), CHUNK_SIZE)]
    print(f"Split into {len(chunks)} chunks of up to {CHUNK_SIZE} "
          f"(numbered from {args.chunk_offset + 1})")
    for j, chunk in enumerate(chunks):
        k = args.chunk_offset + 1 + j
        out_jsonl = f"{pred_dir}/claude_chunk{k}.jsonl"
        path = in_dir / f"briefing_chunk{k}.md"
        path.write_text(make_briefing(chunk, k, out_jsonl), encoding="utf-8")
        print(f"  wrote {path}  ({len(chunk)} items) -> {out_jsonl}")
    print(f"\nDone. {len(chunks)} briefings. Spawn one Claude sub-agent per briefing.")


if __name__ == "__main__":
    main()
