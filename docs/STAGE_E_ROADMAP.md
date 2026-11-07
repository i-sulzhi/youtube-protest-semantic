# Stage E roadmap — next-session tasks

Hand-off doc to start a fresh session. Stage E **v1 is done** (a clean ranked
protest-video index); this lists the five tasks that take it from v1 to a tuned
system + the analytics phase. Read this top-to-bottom, then pick a task.

> Priority order is 1 → 5. Tasks 1–4 harden the *index* (the current goal).
> Task 5 is the *analytics phase* — start it only once the index is settled.

---

## Cold-start context

**What the project is.** Multilingual (RU/UA/BE/DE/EN) YouTube protest-video
retrieval. v2 pipeline (Stages A–D) maximised *recall* (4-way UNION → 712
newly-surfaced). Stage E adds *precision*: a ranked, relevance-gated index.
Background: `README.md`, `docs/ARCHITECTURE.md`, `docs/RESULTS_LOG.md`
(the Stage E v1 section is the most recent entry).

**Environment.**
- venv: `~/Documents/claude_projects/protest_tags/.venv_v2/bin/python` (py3.11;
  sentence-transformers 5.4.1, lancedb 0.30.2, scikit-learn 1.8, scipy 1.17).
- MariaDB up: `mariadb -u sulzhytski metadata` (no password, unix_socket auth,
  socket `/tmp/mysql.sock`). Cyrillic: add `--default-character-set=utf8mb4`.

**⚠ Gotcha — outputs are not persisted.** Most `outputs/` artefacts were
computed but not kept on disk. Present: `v2_feed_ready.csv.gz` (no tags, **no
CHANNEL column**), one LanceDB table `videos_e5large.lance`, its retrieval
`outputs/retrieval_e5large/topk_per_anchor.csv`, the 4 regenerated EXPORT
feature CSVs, and `outputs/stage_e/`. Regen recipe: EXPORT feature scripts take
`--feed outputs/v2_feed_ready.csv.gz` (they only need country_combo + YT_ID
scope). The tags-dependent path (`enrich_with_tags.py`, with-tags embeddings,
`build_canonical_tag_map.py`) is **blocked** — it needs the local file
`complete_video_info_202404251556.csv`, which is missing; the tags would have to
be pulled from MariaDB (`VID_TAGS`/`TAGS`) instead.

**Stage E v1 state (DONE 2026-06-02).**
- Pool: 496 distinct videos (e5-large no-tags, 7 anchors × top-100).
- `scripts/stage_e_rank.py` — composite ranking (semantic + velocity_d7_z +
  hypergraph broker_score + search visibility + anchor↔channel consistency −
  churn penalty; weights hand-set in the `WEIGHTS` dict).
- `scripts/build_relevance_briefings.py` + 6 Claude sub-agents +
  `scripts/stage_e_gate.py` — LLM relevance gate on the `protest_relevance`
  axis (direct/indirect/absent). Validated vs 60 human gold: 3-class κ=0.611,
  binary κ=0.735; keeps 18/18 human-direct, cuts 24/25 human-absent.
- **Deliverable:** `outputs/stage_e/protest_index_gated.csv` — 187 videos
  (496→187), 97% human-protest purity on surviving gold.
- Validation set: `mini_study/coding_layer2.csv` (60 rows, `yt_id` +
  `protest_relevance`). All 60 are inside the 496 pool.

---

## Task 1 — Expand pool to the full UNION (recall before the gate)

> **STATUS: DONE — full 4-way UNION (2026-06-02).**
> Built all 4 LanceDB tables (e5-small/large × no-tags/with-tags) and UNION'd:
> 496 → 2-way **796** → 4-way **1,099** distinct. Gate re-run incrementally each
> step (only NEW videos relabelled, prior labels reused via `--exclude-pred-glob`
> + `--chunk-offset`). Clean index **187 → 263 → 387** (+107% over v1); gate κ
> unchanged (0.611/0.735, 97% gold purity) by construction; every anchor grew
> (UA-Maidan 3→9→14). The user restored `complete_video_info_202404251556.csv`,
> unblocking the with-tags path (`enrich_with_tags.py` → 90.4% tag coverage).
> See RESULTS_LOG "Stage E v1.1".
> **Queued for Task 2:** per-source similarity normalisation — `best_similarity`
> is `max` over encoders with different cosine scales (recovered to AUC 0.740 on
> the 4-way, but z-score/rank-within-source before the max is cleaner).
> **NB for the gate workflow:** sub-agents silently drop a few items per round
> while reporting completeness — always diff briefing YT_IDs vs JSONL after.

**Goal.** v1 gated only the 496-video e5-large pool. The recall-max pool is
larger; running the gate over it yields a more complete index.

**Why.** More candidates enter the gate → more true protest videos survive.
The gate (κ≈0.6, never drops `direct`) is the precision guard, so widening the
input is safe for precision.

**Inputs / blocker.** Needs more LanceDB tables. Only `videos_e5large.lance`
exists. Two paths:
- **Unblocked — 2-way UNION (≈799 distinct):** add the e5-small no-tags table.
- **Full 4-way (≈1,105 distinct):** also needs the two *with-tags* tables →
  blocked on the missing `complete_video_info_202404251556.csv` (see gotcha).
  Decide: restore that CSV, or pull tags from MariaDB into a regenerated
  `v2_feed_ready_with_tags.csv.gz`.

**Steps (2-way path).**
```bash
V=~/Documents/claude_projects/protest_tags/.venv_v2/bin/python
# Stage A — embed e5-small (~6.5 min on M2)
$V pipeline/stage_a_embed.py --model intfloat/multilingual-e5-small --batch 32 --table videos
# Stage B — retrieve
$V pipeline/stage_b_retrieve.py --table videos --model intfloat/multilingual-e5-small --out-dir outputs/retrieval
# UNION the two no-tags sources (or scripts/four_way_ensemble.py for 4-way)
$V scripts/four_way_ensemble.py        # writes outputs/retrieval_nway/all_sources_combined.csv
# Re-run Stage E on the bigger pool
$V scripts/stage_e_rank.py  --pool outputs/retrieval_nway/all_sources_combined.csv
$V scripts/build_relevance_briefings.py --pool outputs/retrieval_nway/all_sources_combined.csv
#   → spawn one Claude sub-agent per new briefing chunk (only the NEW videos need labels;
#     the 496 already-labelled can be reused from outputs/stage_e/relevance_pred/)
$V scripts/stage_e_gate.py
```

**Validation / done.** Gate κ on the 60 gold stays ≈0.6; index grows;
per-anchor survivor counts reported. Watch the under-sampled anchors
(UA-Maidan had only 3 survivors in v1).

**Effort.** Embedding 6.5 min (2-way) to ~1 h (full 4-way) + one sub-agent
classification pass over the *new* candidates (~300–600 videos).

---

## Task 2 — Tune the composite weights

> **STATUS: DONE (2026-06-03).** Harness `scripts/stage_e_tune.py` (ablation +
> 5-fold CV) → `outputs/stage_e/tuning_report.md`. Adopted in `stage_e_rank.py`:
> (1) `--sim-agg zmax` (z-score cosine within each retrieval source before the
> cross-source max — unsupervised fix for the encoder scale mismatch), (2)
> `consistency_bonus` & `churn_penalty` → 0 (ablation-negative, zeroed in ~5/5
> CV folds; gate covers the anti-FP role, and the churn penalty demoted genuine
> old protest content). Kept sim/vel/broker/vis magnitudes (CV magnitude search
> gain only +0.020, unstable → not worth chasing on 60 labels). Result: AUC
> dir-abs **0.740 → 0.840**, Spearman 0.316 → 0.493; **gate membership unchanged**
> (387, κ 0.611/0.735) — only the ranking improved. See RESULTS_LOG "Stage E v2".

**Goal.** v1 weights are hand-set (`WEIGHTS` dict + `CONSISTENCY_BONUS`,
`CHURN_PENALTY` in `scripts/stage_e_rank.py`). With the gate in place, optimise
the *ranking within the relevant set*.

**Why.** v1 composite beats raw cosine only modestly (AUC direct-vs-absent
0.744 vs 0.711). A small search may improve ordering; an ablation tells us
which structural signals actually earn their weight.

**Approach.**
- Ablation: drop one component at a time, re-measure AUC / rank-separation on
  the 60 gold → a per-signal contribution table.
- Light coordinate/grid search over the weights maximising
  AUC(direct-vs-absent) or Spearman(score, relevance). **Guard against
  overfitting** — only 60 labels; report cross-validated or held-out numbers,
  keep the hand-set weights as the documented baseline. (Task 4 grows the gold,
  which makes this more robust.)

**Validation / done.** Cross-validated AUC improvement over v1 weights + an
ablation table. Update the `WEIGHTS` docstring with the rationale.

**Effort.** Small (each eval is seconds).

---

## Task 3 — Channel prior (the biggest unused signal)

> **STATUS: DONE via description-proxy (2026-06-03).** Step-0 premise was wrong —
> there is **no channel field in MariaDB** (or the feed / complete_video_info);
> only the YouTube Data API has it (needs a key + network). Per the user, used a
> **description-proxy channel** (`scripts/build_channel_features.py`): the t.me /
> YouTube-channel / Instagram handle a video promotes. Surfaces the right outlets
> (DW 100%, SOTA 90%, Belsat 72%, UNIAN 71%, …). Concentration over the gated
> index: **Gini 0.515 but HHI 0.030 (diffuse, 89 channels, top-5=30%)** — spread
> unevenly across many outlets, not hub-and-spoke. Honest LOO ranking lift only
> **+0.020 AUC dir-abs (w=0.5)** on 16/60 proxy-covered gold → wired into
> `stage_e_rank.py` as **optional, off-by-default** (`--channel-weight`); index
> unchanged. Recommended w=0.5 once API channels give full coverage or the gold
> grows (Task 4). See RESULTS_LOG "Task 3" + `outputs/stage_e/channel_report.md`.
> **For the clean version:** fetch channelId/channelTitle via the YouTube API
> (`videos.list`, ~22 quota units for the 1,099 pool) — needs the user's API key.

**Goal.** Add channel identity to the pipeline as a feature and/or a retrieval
expander.

**Why.** The codebook's strongest diagnostic: **87% of human labels used
extra-textual info, channel identity decisive in ~1/3** (strana.ua, ОНТ, Дождь,
УНИАН…). The retrieval and the gate currently see only title+description.
Channel stance/reliability is stable and learnable. Conceptual link to the PI's
Telegram work (*Ambassadors of War*, hub-and-spoke concentration).

**Approach.**
- Step 0: the feed has **no channel column** — find the channel/uploader field
  in MariaDB (`VIDEOS`? `VIDEO_METADATA`? inspect schema) and build a
  `YT_ID → channel` map for the 21,710 subset.
- Build per-channel stats over the gate output: share of a channel's videos
  that are gate-`direct`, dominant frame, count. Then either (a) add
  `channel_protest_rate` as a composite feature in `stage_e_rank.py`, or (b)
  retrieval expansion — pull more videos from channels with high confirmed-
  protest rates (catches tag-less / short-text videos the embedding misses).

**Validation / done.** Does the channel feature lift gate/ranking on the gold?
Report channel-level concentration (Gini/HHI) — a structural finding for Task 5.

**Effort.** Medium — schema discovery + a new EXPORT-style script (model on
`scripts/build_search_features.py`).

---

## Task 4 — Active learning (grow the 60-item gold)

> **STATUS: INSTRUMENT READY — awaiting PI coding (2026-06-03).**
> `mini_study/build_active_learning_sheet.py` selected a balanced **wave of 50**
> high-uncertainty items (conf1 / indirect / gate-FN / low-rank; 7–8 per anchor,
> 30 indirect + 19 absent + 1 direct) → blind sheet `coding_sheet_round2.csv`,
> click-to-code UI `coding_round2.html` (YouTube links, autosave, Export-CSV),
> and internal `round2_selection_manifest.csv`. After the PI codes,
> `mini_study/merge_round2_gold.py` → `coding_gold_v2.csv` (≤110), then
> `stage_e_gate.py --gold …` / `stage_e_tune.py --gold …` recompute κ (and firm
> up Task-2's magnitude search + Task-3's channel lift). **The agent did NOT
> fabricate labels** — κ recompute is the one step pending the PI. See RESULTS_LOG
> "Task 4".

**Goal.** Expand the human gold beyond 60, targeting the most informative items.

**Why.** κ rests on 60 labels. The gate's uncertain zone is `indirect` (64
videos) + LLM `confidence==1` items + items where the composite rank and the
relevance label disagree. Coding *those* lifts κ confidence and sharpens the
gate boundary most per unit of the PI's time.

**Approach.**
- Select high-uncertainty items: LLM confidence-1 (the sub-agents flagged
  these), `indirect` predictions, and human↔LLM disagreement candidates.
- Build a coding sheet (reuse `mini_study/build_human_coding_sheet.py` /
  `mini_study/coding_ui.html`) → PI hand-codes → recompute κ on the larger gold
  → optionally re-tune (Task 2) and re-validate the gate.

**Validation / done.** κ stability on the enlarged gold; whether new labels
shift the precision/recall trade-off (v1 cut 7/35 human-relevant — does more
gold recover any?).

**Effort.** Medium — instrument is quick; the bottleneck is the PI's coding
time. The agent prepares the sheet and computes metrics; it does **not**
fabricate human labels.

---

## Task 5 — Analytics phase: three ways the corpus "knows" protest

**Goal.** The structural research result, held as potential: characterise how
the same corpus surfaces protest through three orthogonal modalities —
**semantic retrieval ∪ hypergraph co-occurrence ∪ channel**.

**Why.** Once the index is clean (Tasks 1–4), this is the publishable finding:
the modalities are complementary, not redundant (cf. the 4-way overlap analysis
in RESULTS_LOG, ~30% cross-cross overlap).

**Approach.**
- (a) semantic = the embedding retrieval; (b) hypergraph = expand from gate-
  `direct` seeds to their co-occurrence neighbours in
  `outputs/hypergraph/incidence.csv` (videos sharing `(term, date)` discovery
  pools); (c) channel = the Task-3 prior. Quantify pairwise overlap /
  complementarity; surface the cross-channel **brokers** (1 five-term super-
  broker + 6 four-term videos, see EXPORT 7) as bridges between event clusters.

**Validation / done.** An overlap/complementarity table + broker case studies.
This is a research write-up, not a pipeline change.

**Effort.** Large — the analytics deliverable. Do last.

---

## Quick reference — re-run the current Stage E v1 end-to-end
```bash
V=~/Documents/claude_projects/protest_tags/.venv_v2/bin/python
# features already on disk; if not, regen (MariaDB up):
$V scripts/build_engagement_features.py --feed outputs/v2_feed_ready.csv.gz
$V scripts/detect_churn.py             --feed outputs/v2_feed_ready.csv.gz
$V scripts/build_search_features.py    --feed outputs/v2_feed_ready.csv.gz
$V scripts/build_hypergraph.py         --feed outputs/v2_feed_ready.csv.gz --skip-hnx
# rank → briefings → 6 Claude sub-agents → gate
$V scripts/stage_e_rank.py
$V scripts/build_relevance_briefings.py     # then spawn 6 sub-agents on outputs/stage_e/relevance_input/*
$V scripts/stage_e_gate.py
# outputs/stage_e/protest_index_gated.csv is the deliverable
```
