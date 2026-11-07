# Session progress — 2026-06-02/03 (Stage E Tasks 1–4)

Consolidated hand-off for the session that took Stage E from v1 → v2 and worked
the roadmap Tasks 1–4. Per-task detail lives in `RESULTS_LOG.md`; data inventory
+ regen commands in `DATA_MANIFEST.md`; task status flags in
`STAGE_E_ROADMAP.md`. **Resume point: the PI hand-codes the 50-item round-2 sheet,
then κ is recomputed (Task 4).**

## Headline

| | start (v1) | end of session |
|---|---:|---:|
| Candidate pool | 496 (e5-large only) | **1,099** (full 4-way UNION) |
| Clean gated index | 187 | **387** |
| Composite AUC dir-abs | 0.744 | **0.840** |
| Gate κ (3-class / binary) | 0.611 / 0.735 | **0.611 / 0.735** (held) |
| Gold-survivor purity | 97% | **97%** |
| Human gold | 60 | 60 (+50 instrument ready) |

The index more than doubled (recall) while the gate's precision held exactly and
the ranking improved — all four tasks advanced.

## Task 1 — pool expansion to the full 4-way UNION (DONE)
- Built all 4 LanceDB tables: e5-small/large × no-tags/with-tags (21,710 each).
  The user restored `complete_video_info_202404251556.csv`, unblocking the
  with-tags path (`enrich_with_tags.py` → 90.4% tag coverage).
- UNION (`four_way_ensemble.py`): 496 → 2-way **796** → 4-way **1,099** distinct
  (709 newly-surfaced; +35% from the tags variants; sources complementary,
  pairwise top-100 overlap 28–61/100).
- **Incremental gate**: extended `build_relevance_briefings.py` with
  `--exclude-pred-glob` + `--chunk-offset` so each expansion only relabels the
  NEW videos and reuses prior labels (496 → +300 → +303). Sub-agents labelled the
  new chunks; **they silently dropped a few items both rounds (4, then 3) while
  reporting completeness** — caught by a briefing-vs-JSONL diff, hand-labelled
  into `claude_chunk_fix_dropped*.jsonl`. All 1,099 carry a label.
- Gate κ unchanged by construction (the 60 gold's labels are reused verbatim).
  Index **187 → 263 → 387**; every anchor grew (UA-Maidan 3→9→14).

## Task 2 — composite tuning & ablation (DONE)
- New research harness `scripts/stage_e_tune.py` (sim-aggregation test +
  leave-one-out ablation + 5-fold CV weight search).
- **Adopted (v2):** `--sim-agg zmax` (z-score cosine within each retrieval source
  before the cross-source max — fixes the encoder scale mismatch, unsupervised) +
  `consistency_bonus = 0` + `churn_penalty = 0` (ablation showed they don't earn
  their weight). Hand-set sim/vel/broker/vis magnitudes kept (CV search was
  noise — honest, not overfit).
- Result: AUC dir-abs 0.740 → **0.840**, rel-abs 0.753, Spearman 0.493; mean rank
  of `direct` 446 → 274. **Gate membership unchanged (387).** `protest_index.csv`
  gained a `sim_agg` column. Reproduce v1 ranking with `--sim-agg max_raw`.

## Task 3 — channel prior, description-proxy (DONE)
- **Blocker found:** there is **no channel/uploader field anywhere local**
  (every MariaDB table/DB, the feed, complete_video_info). Only the YouTube Data
  API has it. Per the user, used a **description-proxy channel**
  (`scripts/build_channel_features.py`): the t.me / YouTube-channel / Instagram
  handle a video promotes. 57% pool coverage; surfaces the right outlets (DW
  100%, SOTA 90%, Belsat 72%, UNIAN 71%, Vot-Tak 85%).
- **Concentration (Task-5 input):** over the 387 gated, 89 channels, **Gini 0.515
  but HHI 0.030 (diffuse)** — protest coverage spread unevenly across many
  outlets, *not* hub-and-spoke.
- **Honest LOO ranking lift only +0.020 AUC dir-abs (w=0.5)** on 16/60
  proxy-covered gold → wired into `stage_e_rank.py` as **optional, off-by-default**
  (`--channel-weight`); production index unchanged. Enable w=0.5 once API channels
  give full coverage or the gold grows.

## Task 4 — active learning: grow the gold (INSTRUMENT READY)
- `mini_study/build_active_learning_sheet.py` selected a balanced **wave of 50**
  high-uncertainty uncoded items (tags: conf1 / indirect / gate-FN / low-rank;
  7–8 per anchor; 30 indirect + 19 absent + 1 direct; 48/50 LLM-low-confidence).
- Instrument: `mini_study/coding_sheet_round2.csv` (blind — no LLM label shown),
  `mini_study/coding_round2.html` (self-contained click-to-code UI: buttons,
  1/2/3 keys, YouTube links, autosave, Export-CSV),
  `mini_study/round2_selection_manifest.csv` (internal provenance).
- Recompute path: `mini_study/merge_round2_gold.py` → `coding_gold_v2.csv`, then
  `stage_e_gate.py --gold …` / `stage_e_tune.py --gold …`. Verified the merge
  **refuses to run on an empty sheet** (no fabrication).
- **The agent did NOT fabricate labels.** κ recompute is the one pending step.

## ▶ Resume checklist (next session / after PI codes)
1. PI opens `mini_study/coding_round2.html`, codes 50 items, Export CSV →
   `mini_study/coding_sheet_round2_FILLED.csv` (or fills the CSV by hand).
2. `python mini_study/merge_round2_gold.py` → `mini_study/coding_gold_v2.csv`.
3. `python scripts/stage_e_gate.py --gold mini_study/coding_gold_v2.csv` — new κ.
4. `python scripts/stage_e_tune.py --gold mini_study/coding_gold_v2.csv` — does
   the larger gold firm up the magnitude search (Task 2) and the channel lift
   (Task 3)? Does it recover any of the 7/35 human-relevant v1 cut?
5. Then **Task 5** (analytics: semantic ∪ hypergraph ∪ channel; channel
   concentration already computed).
6. Optional clean channel: fetch channelId via YouTube API (~22 quota units for
   the 1,099 pool) and set `--channel-weight 0.5`.

## Data persistence
All regenerated artefacts (664 MB) are in `outputs/` **in the main checkout**
(not a worktree, not /tmp) and persist across normal git use. `outputs/` and
`complete_video_info_*.csv` are **gitignored by design** (size). Run
`python scripts/verify_outputs.py` to see what's cached vs needs regen. See
`DATA_MANIFEST.md`. ⚠ Do **not** `git clean -dfx` — it deletes the 664 MB cache.
