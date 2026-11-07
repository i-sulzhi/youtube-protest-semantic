"""Build 4 self-contained classification briefings for the Claude-as-annotator pass.

Splits the 60-item coding sheet into 2 chunks of 30 items each, then writes
4 markdown briefing files (chunk_X × prompt_Y) that a Claude sub-agent can
read and execute. Each briefing is fully self-contained — codebook,
protocol, items, output spec.

Outputs:
  mini_study/llm_input/briefing_promptA_chunk1.md   (items 1-30, terse prompt)
  mini_study/llm_input/briefing_promptA_chunk2.md   (items 31-60, terse prompt)
  mini_study/llm_input/briefing_promptB_chunk1.md   (items 1-30, CoT prompt)
  mini_study/llm_input/briefing_promptB_chunk2.md   (items 31-60, CoT prompt)
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
CSV = REPO / "mini_study" / "coding_sheet_for_human.csv"
OUT_DIR = REPO / "mini_study" / "llm_input"
PRED_DIR = REPO / "mini_study" / "llm_predictions"
CHUNK_SIZE = 30
DESC_TRUNC = 700  # chars — keeps briefing under ~25k chars total


CODEBOOK = """\
## Codebook — 5 mutually-exclusive framing categories

**prokremlowski / pro-Kremlin**
Text adopts the Russian state's framing or its allies'. Signals: calls the 2022 invasion "СВО" / "specjalna operacja" without distancing quotes; delegitimises Ukrainian statehood or Belarusian opposition; blames the West for escalation; pejoratives for opposition ("так называемые", "Western agents", "нацистский режим"); absence of alternative voices; state-TV editorial framing (Беларусь 1, СТВ, Russia 1, Соловьёв LIVE).

**antywojenny / antiwar**
Text explicitly opposes the war (2022+) or state repression (Belarus 2020+, Russia post-2022). Signals: protest slogans ("нет войне", "свободу политзаключённым", "свободу Навальному"); coverage of arrests, political prisoners, exile; voices of mobilised soldiers / their families framed sympathetically; opposition perspective treated as legitimate; Russian opposition channels (Navalny team, Dozhd, Eurоradio, Bykov, Gordon, Milov).

**prozachodni / pro-Western**
Text treats Western institutions (EU, NATO, US) as the normative reference. Signals: Western-media explainer format (DW, Reuters, BBC, Euronews, Voice of America, France 24, NPR); framing the war as "democratic values vs authoritarianism"; advocacy for UA/BY integration with EU/NATO; Western politicians/experts as primary sources.

**białorusko-narodowy / Belarusian-national**
Text grounds itself in Belarusian national identity as distinct from Russian. Signals: БЧБ flag / "белорусский-красный-белый"; Tikhanouskaya, Kalinouski, Bialiatski; references to GDL history (Wielkie Księstwo Litewskie); opposition to "русский мир"; Belarusian language as primary; émigré editorial centres (Belsat from Warsaw, Radyjo Svaboda from Vilnius, Nasha Niva); Poland/Lithuania as refuge.

**neutralny-informacyjny / neutral-informational**
News/briefing format without explicit evaluation: summaries, briefings, factual updates, multi-item news roundups. No evaluative language, no overt partisanship. **Default category when 50/50 between two framings.**

## Decision rules

1. Find the **dominant evaluative voice** (≥60% of content).
2. If unclear, ask: **who is the implied addressee?** (Diaspora / Western / Russian-speaking domestic / no-explicit-target.)
3. Default to `neutralny-informacyjny` when in genuine doubt.

## Known ambiguities

- `prokremlowski` vs `neutralny-informacyjny` — most frequent. State-media bulletins (Беларусь 1, Россия 24) often present pro-regime narrative AS news. Code `prokremlowski` only if explicit evaluative markers are present. Otherwise `neutralny-informacyjny`.
- `białorusko-narodowy` vs `prozachodni` — Belsat in Belarusian → BN; DW in English about Belarus → PZ. Switch to PZ only when language is EN/DE/FR addressed to Western audience.
- `antywojenny` vs `prozachodni` — Russian opposition channels (Navalny, Dozhd) are both anti-war AND pro-Western. Default `antywojenny` because primary frame is *opposition to Russian state*, not *advocacy for Western institutions*.
- `antywojenny` vs `białorusko-narodowy` — Belarusian opposition is both. Default BN when Belarusian identity is the primary frame; antywojenny when the 2022 war / Russian mobilisation is the primary frame.

## Out of scope
- Pre-2014 events / Soviet history without contemporary framing → `neutralny-informacyjny`.
- Apolitical content that slipped through Politics auto-classifier → `neutralny-informacyjny`.
"""


PROMPT_A_INSTRUCTIONS = """\
## Prompt formulation A — structured / terse

You are an expert annotator of multilingual Eastern-European political media. Read each video's TITLE and DESCRIPTION. Apply the codebook above to assign ONE of the 5 mutually-exclusive framing labels.

For each item, produce:
- `label`: exactly one of `prokremlowski` / `antywojenny` / `prozachodni` / `bialorusko-narodowy` / `neutralny-informacyjny`
- `confidence`: integer 1 (low), 2 (medium), or 3 (high)
- `rationale`: ONE sentence (max 30 words) naming the specific signal that drove your decision

Be decisive. Do not abstain. When boundary cases arise, apply the decision rules section above.
"""


PROMPT_B_INSTRUCTIONS = """\
## Prompt formulation B — chain-of-thought / discursive

You are an experienced researcher of Eastern-European disinformation and political communication. For each video, you will think through the framing in three steps before committing to a label.

For each item, perform internally (you do NOT need to output the reasoning, just the conclusion):

1. **Identify the speaker.** Who is the channel/author? Is this a state outlet, an opposition outlet, a Western broadcaster, an independent commentator?
2. **Identify the implied audience.** Is the text addressed to a diaspora? Russian-speaking domestic audience? Western audience? Belarusian national community?
3. **Find the dominant evaluative move.** Is the war legitimated, opposed, explained, or merely reported?

Then assign exactly ONE of: `prokremlowski` / `antywojenny` / `prozachodni` / `bialorusko-narodowy` / `neutralny-informacyjny`.

Output for each item:
- `label`: the framing category
- `confidence`: 1 (low), 2 (medium), or 3 (high)
- `rationale`: ONE sentence (max 40 words) summarising the three-step reasoning

Apply the boundary rules from the "Known ambiguities" section above.
"""


def fmt_item(it: dict, idx: int) -> str:
    def _s(v):
        if v is None: return ""
        try:
            import math
            if isinstance(v, float) and math.isnan(v): return ""
        except Exception:
            pass
        return str(v)
    title = _s(it.get("TITLE")).strip()
    desc = _s(it.get("DESCRIPTION")).strip()
    if len(desc) > DESC_TRUNC:
        desc = desc[:DESC_TRUNC] + "…[truncated]"
    return (
        f"### Item {idx}\n"
        f"- YT_ID: `{it['YT_ID']}`\n"
        f"- anchor: {it['anchor']}\n"
        f"- language: {it['language_norm']}  |  country_combo: {it['country_combo']}  |  protest_keyword: {it['protest_anywhere']}\n"
        f"- **TITLE:** {title}\n"
        f"- **DESCRIPTION:** {desc}\n"
    )


def make_briefing(items: list, prompt_letter: str, chunk_id: int, prompt_text: str, out_jsonl: str) -> str:
    yt_ids = ", ".join(f"`{it['YT_ID']}`" for it in items)
    body = "\n\n".join(fmt_item(it, i + 1) for i, it in enumerate(items))
    n = len(items)
    return f"""# Classification briefing — Prompt {prompt_letter}, chunk {chunk_id}

You are acting as **Claude as an LLM annotator** for a multilingual YouTube framing-classification study.

The study compares LLM annotations against human-coded labels to compute Cohen's κ and per-class F1, with cross-prompt-formulation stability as a proxy for the "Benchmark Illusion" cross-model disagreement check (Yang & Wang 2025).

**Your task:** classify the {n} items listed at the bottom of this briefing. Apply the codebook below using prompt formulation {prompt_letter}.

{CODEBOOK}

{prompt_text}

## Output format

Write your predictions to `{out_jsonl}` — one JSON object per line, in the exact order of items below.

Each line must be a single-line JSON object with these keys exactly:
```json
{{"yt_id": "ABC123def", "label": "antywojenny", "confidence": 2, "rationale": "Reuters explainer framing UA war from Western institutional perspective."}}
```

Required:
- `label` must be one of: `prokremlowski`, `antywojenny`, `prozachodni`, `bialorusko-narodowy`, `neutralny-informacyjny`
- `confidence` must be integer 1, 2, or 3
- `rationale` must be present and non-empty

**Operational rules:**
- Do NOT use Bash, Web, or any tool other than `Write`.
- Process all {n} items. Do not skip any.
- After writing the JSONL file, output a one-line summary: how many items per label, and any items where you were genuinely uncertain (confidence=1).
- Do not modify any other file.

YT_IDs to classify in this chunk (n={n}): {yt_ids}

---

## Items to classify

{body}
"""


def main():
    df = pd.read_csv(CSV, dtype=str, keep_default_na=False, na_values=[""])
    items = df.to_dict(orient="records")
    print(f"Loaded {len(items)} items")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PRED_DIR.mkdir(parents=True, exist_ok=True)

    chunks = []
    for i in range(0, len(items), CHUNK_SIZE):
        chunks.append(items[i : i + CHUNK_SIZE])
    print(f"Split into {len(chunks)} chunks of up to {CHUNK_SIZE}")

    written = []
    for chunk_id, chunk_items in enumerate(chunks, start=1):
        for letter, prompt in [("A", PROMPT_A_INSTRUCTIONS), ("B", PROMPT_B_INSTRUCTIONS)]:
            out_jsonl = str(PRED_DIR / f"claude_prompt{letter}_chunk{chunk_id}.jsonl")
            briefing_path = OUT_DIR / f"briefing_prompt{letter}_chunk{chunk_id}.md"
            briefing = make_briefing(chunk_items, letter, chunk_id, prompt, out_jsonl)
            briefing_path.write_text(briefing, encoding="utf-8")
            written.append((str(briefing_path), out_jsonl, len(chunk_items)))
            print(f"  wrote {briefing_path}  → {out_jsonl}  ({len(chunk_items)} items)")

    print(f"\nDone. {len(written)} briefings written.")
    print("Each agent should:")
    print("  1. Read its briefing markdown file")
    print("  2. Process all items per the prompt formulation")
    print("  3. Write JSONL predictions to the specified path")


if __name__ == "__main__":
    main()
