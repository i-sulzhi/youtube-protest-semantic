# Data manifest — regenerated artefacts (as of 2026-06-03)

What is on disk, how to regenerate each piece, and how expensive it is. Goal: the
next session never regenerates from scratch — run `scripts/verify_outputs.py`,
then rebuild only what's missing.

**Persistence.** Everything below lives in the **main checkout** (not a git
worktree, not /tmp) so it survives normal git operations. But `outputs/` and
`complete_video_info_*.csv` are **gitignored by design** (664 MB — too big for
git). ⚠ `git clean -dfx` would delete the whole cache. The earlier
"outputs-not-persisted" loss was a worktree cleanup; keeping work in the main
checkout (as this session did) is the fix.

`V` = the Python the Makefile picks (the project's `.venv`, else `../protest_tags/.venv_v2/bin/python` on the Mac) · MariaDB up
(`mariadb -u sulzhytski metadata`, unix_socket, `/tmp/mysql.sock`).

## Tier A — expensive (embeddings, ~55 min total on M2; models cached)
| artefact | rows/size | regen | cost |
|---|---|---|---|
| `outputs/v2_lancedb/videos.lance` | 21,710 / 95 MB | `$V pipeline/stage_a_embed.py --model intfloat/multilingual-e5-small --batch 32 --table videos` | ~6 min |
| `outputs/v2_lancedb/videos_e5large.lance` | 21,710 / 148 MB | `$V pipeline/stage_a_embed.py --model intfloat/multilingual-e5-large --batch 16 --table videos_e5large` | ~40 min |
| `outputs/v2_lancedb/videos_with_tags.lance` | 21,710 / 102 MB | `$V pipeline/stage_a_embed.py --feed-csv outputs/v2_feed_ready_with_tags.csv.gz --use-tags --model intfloat/multilingual-e5-small --batch 32 --table videos_with_tags` | ~7 min |
| `outputs/v2_lancedb/videos_e5large_with_tags.lance` | 21,710 / 155 MB | `$V pipeline/stage_a_embed.py --feed-csv outputs/v2_feed_ready_with_tags.csv.gz --use-tags --model intfloat/multilingual-e5-large --batch 16 --table videos_e5large_with_tags` | ~43 min |

## Tier B — needs MariaDB (small, ~minutes; UNREGENERABLE if the DB is gone)
| artefact | rows | regen |
|---|---|---|
| `outputs/v2_feed_ready_with_tags.csv.gz` | 21,710 | `$V scripts/enrich_with_tags.py` (needs `complete_video_info_202404251556.csv`, 90.4% tag coverage) |
| `outputs/engagement_features.csv` | 21,710 | `$V scripts/build_engagement_features.py --feed outputs/v2_feed_ready.csv.gz` |
| `outputs/churn_signal.csv` | 21,710 | `$V scripts/detect_churn.py --feed outputs/v2_feed_ready.csv.gz` |
| `outputs/search_features.csv` | 21,710 | `$V scripts/build_search_features.py --feed outputs/v2_feed_ready.csv.gz` |
| `outputs/hypergraph/vertex_stats.csv` | 21,710 | `$V scripts/build_hypergraph.py --feed outputs/v2_feed_ready.csv.gz --skip-hnx` |
| `outputs/sampling_validity.csv` | 17 | `$V` one-liner over `SEARCHES` (EXPORT 10 SQL in `RESULTS_LOG.md`) |
| `outputs/static_flags.csv` | 21,710 | `make flags` (topics/captions/license/live/age flags — DATA_GAPS №1,3–8) |
| `outputs/event_features.csv` | 1,099 | `make events` (from `data/event_calendar.csv`) |
| `outputs/distilled_relevance_feed.csv` + `stage_e/distilled_gate.joblib` | 21,710 | `make distill` (local student of the LLM gate) |
| `outputs/channel_expansion_candidates.csv` | ≤200 | `make expand-channel` |
| `outputs/stage_f/modality_sets.csv` | varies | `make modalities` |
| `outputs/trajectory_features.csv` | 21,710 | `make trajectory` (curve shapes + rank dynamics; DATA_GAPS №9–10) |
| `outputs/stage_e/rationale_clusters.{md,csv}` | 1,099 | `make rationales` |
| `outputs/distill_expansion_candidates.csv` | ≤200 | `make distill-mine` (after `make distill`) |
| `outputs/analytics/master.csv.gz` | 21,710 × 81 | `make analytics-master` (rebuild after ANY upstream artefact change) |
| `outputs/analytics/*.md` + `figures/analytics/` | 6 reports | `make analytics`; ad-hoc: `make slice Q='…'` |

**Waiting-for-input artefacts** (scripts ready, checkpointed, `make help`):
`outputs/video_api.csv` (`make api-video`, needs `YT_API_KEY`),
`outputs/metadata_bulk.csv` (`make api-bulk`, ~5,222 quota units; id cache
`outputs/missing_politics_ids.csv` builds without a key),
`outputs/churn_attribution.csv` (`make churn-attr`, needs video_api),
`outputs/stage_e/relevance_pred_gpt/*.jsonl` (`make ensemble`, needs
`OPENAI_API_KEY`), `mini_study/coding_gold_v2.csv` (`make gold-v2`, needs the
PI's round-2 coding).

**Flag-drift note (2026-06-10).** `protest_anywhere` / `protest_in_*` /
`country_combo` are regexes over the latest title+description snapshot — they
drift across regenerations when the underlying snapshot or regex changes
(historical logs say 2,034 protest-mentioning; current feed says **2,049**
after the «стачк» regex fix). Quote them as approximate. The four
`v2_lancedb/*.lance` tables still carry the pre-fix flags for 4 videos
(`0sbxFJSst5g, B5PXtbgVQNg, u9c7shF28x0, xhwJQhamI_w`) — vectors are
unaffected (feed_text unchanged); the flags self-correct at the next
re-embed. Downstream CSVs were patched/regenerated 2026-06-10.

## Tier C — cheap (seconds), from Tier A+B
| artefact | rows | regen |
|---|---|---|
| `outputs/retrieval/topk_per_anchor.csv` | 700 | `$V pipeline/stage_b_retrieve.py --table videos --model intfloat/multilingual-e5-small --out-dir outputs/retrieval` |
| `outputs/retrieval_e5large/…` | 700 | `…--table videos_e5large --model …-e5-large --out-dir outputs/retrieval_e5large` |
| `outputs/retrieval_with_tags/…` | 700 | `…--table videos_with_tags --model …-e5-small --out-dir outputs/retrieval_with_tags` |
| `outputs/retrieval_e5large_with_tags/…` | 700 | `…--table videos_e5large_with_tags --model …-e5-large --out-dir outputs/retrieval_e5large_with_tags` |
| `outputs/retrieval_nway/all_sources_combined.csv` | 2,800 | `$V scripts/four_way_ensemble.py` (4-way UNION = 1,099 distinct) |
| `outputs/stage_e/protest_index.csv` | 1,099 | `$V scripts/stage_e_rank.py --pool outputs/retrieval_nway/all_sources_combined.csv` |
| `outputs/channel_features.csv` | 1,099 | `$V scripts/build_channel_features.py` |

## Tier D — IRREPLACEABLE-cheap (LLM gate labels — needs sub-agents to regen)
| artefact | what | note |
|---|---|---|
| `outputs/stage_e/relevance_pred/claude_chunk*.jsonl` | 1,099 LLM relevance labels | Built by 14 Claude sub-agents + 2 hand-fix files. **Preserve these** — regenerating means re-running sub-agents. |
| `outputs/stage_e/protest_index_gated.csv` | 387 | `$V scripts/stage_e_gate.py` (from index + relevance_pred) |
| `mini_study/coding_layer2.csv` | 60-item human gold | the κ baseline |
| `mini_study/coding_sheet_round2.csv`, `coding_round2.html`, `round2_selection_manifest.csv` | Task-4 instrument | awaiting PI coding |
| `mini_study/coding_sheet_audit.csv`, `coding_audit.html`, `audit_selection_manifest.csv` | random audit wave (20, seed=42, stratified by retrieval source) | awaiting PI coding; merge as `--round-label 3` |

## Full rebuild order (if starting cold)
Tier B (MariaDB) → Tier A (embeddings) → Tier C (retrieval/UNION/rank) → Tier D
(`stage_e_gate.py`; relevance_pred must already exist or be re-labelled).

## Snapshots for the second computer

The data are not in git. A dated, checksummed snapshot of `outputs/`, the tags CSV, the MariaDB dump and the private files (row-level sheets with titles and descriptions, the AGH talk brief, `backups/`) is kept on OneDrive AGH, folder `nexus-data/youtube-protest-semantic/<date>/`; its `MANIFEST.md` says how to restore it on Windows and how it was checked. First snapshot: 2026-11-07 (all 432 files and both raw files verified identical after restore). The Mac is the only writer of `outputs/`.
