# Results log — tags-as-additional-signal experiment

This document logs the empirical results of each milestone in the
project. Numbers below are produced by re-running the pipeline as
described in `RUNBOOK.md`; every row is reproducible from a
specific output CSV.

---

## Baseline — no tags in feed_e5

**Pipeline state.** `feed_e5 = "passage: " + TITLE + " . " + DESCRIPTION`
truncated to 2000 chars. Tags from YouTube `VID_TAGS` table are *not*
used. LanceDB tables: `videos` (e5-small, 384-dim) and `videos_e5large`
(e5-large, 1024-dim).

**Date last refreshed.** 2026-05-15 (after `.metric("cosine")` and
`fusion_union` fixes).

### Stage B — per-anchor newly-surfaced rate (%)

Source: `outputs/retrieval_ensemble/comparison_summary.csv`.

| Anchor | e5-small | e5-large |
|---|---:|---:|
| BY-2020-protest | 55.0 | 50.0 |
| RU-Navalny | 32.0 | 39.0 |
| RU-antiwar-2022 | 52.0 | 63.0 |
| RU-mobilisation-2022 | 46.0 | 63.0 |
| UA-Maidan-2014 | 75.0 | 85.0 |
| UA-current-protest | 95.0 | 82.0 |
| general-protest-action | 56.0 | 74.0 |
| **median** | **55** | **63** |

### Stage B — top-100 overlap between encoders

| Anchor | Common | Only e5-small | Only e5-large |
|---|---:|---:|---:|
| BY-2020-protest | 24 | 76 | 76 |
| RU-Navalny | 49 | 51 | 51 |
| RU-antiwar-2022 | 29 | 71 | 71 |
| RU-mobilisation-2022 | 32 | 68 | 68 |
| UA-Maidan-2014 | 38 | 62 | 62 |
| UA-current-protest | 56 | 44 | 44 |
| general-protest-action | 17 | 83 | 83 |
| **range** | **17–56** | | |

### Stage D — distinct video coverage (2-way ensemble)

Source: `outputs/retrieval_ensemble/comparison_summary.csv` and
`outputs/retrieval_ensemble/newly_surfaced.csv`.

| Method | Distinct videos | Newly-surfaced |
|---|---:|---:|
| e5-small alone | 502 | 315 |
| e5-large alone | 498 | 329 |
| RRF | 500 | ~310 |
| CombSUM | 501 | ~320 |
| **UNION** | **799** | **527** |

Headline number: **527 newly-surfaced videos**, +60% over best single
encoder (329).

### Stage C — cluster purity

Source: `outputs/polysemy{,_e5large}/cluster_assignments.csv`.

| Encoder | Mean purity | Range across 8 clusters |
|---|---:|---|
| e5-small | 61.2% | 38.0%–90.3% |
| e5-large | 62.0% | 36.4%–89.2% |

---

## Experiment 1 — Add tags to feed_e5

**Hypothesis.** YouTube user-tags carry author-curated semantic labels
that may be denser signal than the boilerplate tail of descriptions.
Adding them to `feed_e5` should surface more *newly-surfaced* videos
(videos without the literal *protest* keyword in title/description but
semantically relevant).

**Changes.**

- New script `scripts/enrich_with_tags.py` — `LEFT JOIN`
  `outputs/v2_feed_ready.csv.gz` with the
  `complete_video_info_202404251556.csv` on `YT_ID`. Output:
  `outputs/v2_feed_ready_with_tags.csv.gz` (18 MB).
- `pipeline/stage_a_embed.py` — new flag `--use-tags`. When set:
  - Truncate description to 1500 chars instead of 2000.
  - Append `" . теги: " + tags[:500]` to `feed_e5`.
  - Persist `tags` as a LanceDB column.
- New LanceDB tables:
  - `videos_with_tags` (e5-small)
  - `videos_e5large_with_tags` (e5-large, pending)

**Tag coverage on the politics subset.**

| Metric | Value |
|---|---|
| Videos with tags | 19,623 of 21,710 (90.4%) |
| Videos without tags | 2,087 (9.6%) |
| Median tags per video | 22 |
| Median tag-string length | 346 chars |
| Max tag-string length | 4,982 chars |

---

### Experiment 1.1 — e5-small, tags included

**Date.** 2026-05-16

**Files.**

| Artefact | Path |
|---|---|
| LanceDB table | `outputs/v2_lancedb/videos_with_tags.lance` |
| Stage B output | `outputs/retrieval_with_tags/topk_per_anchor.csv` |

**Stage B — per-anchor newly-surfaced rate (%)**

| Anchor | No tags | With tags | Δ (pp) |
|---|---:|---:|---:|
| BY-2020-protest | 55.0 | 57.0 | +2.0 |
| RU-Navalny | 32.0 | 30.0 | −2.0 |
| RU-antiwar-2022 | 52.0 | 39.0 | **−13.0** |
| RU-mobilisation-2022 | 46.0 | 44.0 | −2.0 |
| UA-Maidan-2014 | 75.0 | 64.0 | **−11.0** |
| UA-current-protest | 95.0 | 84.0 | **−11.0** |
| general-protest-action | 56.0 | 39.0 | **−17.0** |
| **median** | **55** | **39** | **−16** |

**Stage B — top-100 overlap between e5-small variants**

| Anchor | Common | Only no-tags | Only with-tags |
|---|---:|---:|---:|
| BY-2020-protest | 39 | 61 | 61 |
| RU-Navalny | 79 | 21 | 21 |
| RU-antiwar-2022 | 50 | 50 | 50 |
| RU-mobilisation-2022 | 74 | 26 | 26 |
| UA-Maidan-2014 | 57 | 43 | 43 |
| UA-current-protest | 69 | 31 | 31 |
| general-protest-action | 45 | 55 | 55 |
| **range** | **39–79** | | |

**Aggregate distinct counts**

| Method | Distinct videos | Newly-surfaced |
|---|---:|---:|
| e5-small **no tags** | 502 | 315 |
| e5-small **with tags** | 515 | 296 |
| **UNION** (no-tags ∪ with-tags, e5-small only) | **699** | **441** |

→ +40% newly-surfaced over the best single e5-small variant (315).

**Interpretation.** Adding tags to a single embedding does *not* lift
the newly-surfaced rate — it actually drops it by 16 pp at the median,
because tags amplify the signal for videos that already have surface
*protest* keywords (those videos tend to have related words in tags
too). However, the with-tags variant retrieves a *different* set of
videos: top-100 overlap with the no-tags variant ranges 39–79 / 100.
Treating the two variants as separate retrieval sources and taking
their UNION gives a +40% recall gain.

Tags carry complementary information, not better information. The
right architectural decision is *not* to replace the no-tags
embedding but to add the with-tags embedding as a parallel source in
the Stage D ensemble.

**Qualitative spot-check.** Among the 126 videos surfaced *only* by
the with-tags variant for `BY-2020-protest`, the leading pattern is
Belarusian-language oppositional commentary (Belsat-style journalism:
«Лукашэнка», «Эўропа», «змагары»). These are exactly the kinds of
videos whose surface text does not name protest but whose tags do.
The no-tags variant compensates with Russian-language news around
Lukashenko, which the tags-variant under-weights.

---

### Experiment 1.2 — e5-large, tags included

**Date.** 2026-05-16

**Files.**

| Artefact | Path |
|---|---|
| LanceDB table | `outputs/v2_lancedb/videos_e5large_with_tags.lance` (499 MB) |
| Stage B output | `outputs/retrieval_e5large_with_tags/topk_per_anchor.csv` |

**Stage A timing.** 40 minutes 23 seconds (2,422 s wall, 9.0 vec/s,
batch=8, fp16 on M2 16 GB MPS). Slower than the no-tags baseline
(32 min) because the average input string is longer after tag
concatenation. No thermal throttling observed.

**Stage B — per-anchor newly-surfaced rate (%)**

| Anchor | No tags | With tags | Δ (pp) |
|---|---:|---:|---:|
| BY-2020-protest | 50.0 | 28.0 | **−22.0** |
| RU-Navalny | 39.0 | 27.0 | **−12.0** |
| RU-antiwar-2022 | 63.0 | 48.0 | **−15.0** |
| RU-mobilisation-2022 | 63.0 | 63.0 | 0.0 |
| UA-Maidan-2014 | 85.0 | 81.0 | −4.0 |
| UA-current-protest | 82.0 | 79.0 | −3.0 |
| general-protest-action | 74.0 | 48.0 | **−26.0** |
| **median** | **63** | **48** | **−15** |

**Aggregate.** 509 distinct videos, 278 newly-surfaced. Slightly lower
recall than no-tags (498 / 329), confirming the Experiment 1.1
pattern: tags amplify the keyword signal, lowering newly-surfaced
rate when used as the *only* signal.

**Interpretation.** The drop on `BY-2020-protest` (−22 pp) and
`general-protest-action` (−26 pp) is striking. These two anchors
sit in dense regions of the embedding space where the tag string
contains many of the surface keywords. e5-large picks up on the tag
co-occurrence with *протест* / *protest* etc., which pulls
keyword-containing videos sharply upward.

---

### Experiment 1.3 — 4-way ensemble (final)

**Date.** 2026-05-16

**Method.** UNION over four retrieval sources:

1. `small_no_tags`   — e5-small, no tags
2. `large_no_tags`   — e5-large, no tags
3. `small_with_tags` — e5-small, with tags (Experiment 1.1)
4. `large_with_tags` — e5-large, with tags (Experiment 1.2)

Implementation: `scripts/four_way_ensemble.py`. Output:
`outputs/retrieval_nway/`.

**Stage D — distinct video coverage (final)**

| Method | Distinct videos | Newly-surfaced |
|---|---:|---:|
| `small_no_tags` alone | 502 | 315 |
| `large_no_tags` alone | 498 | 329 |
| `small_with_tags` alone | 515 | 296 |
| `large_with_tags` alone | 509 | 278 |
| 2-way UNION (no-tags only) | 799 | 527 |
| **4-way UNION** | **1,105** | **712** |

**Headline number: 712 newly-surfaced videos.**

- +35.1% over the existing 2-way no-tags UNION (527)
- +116% over the best single encoder (329, e5-large no-tags)
- Distinct video coverage: 1,105 — over half of the 2,034
  protest-mentioning subset.

**Per-anchor 4-way UNION newly-surfaced rate (%)**

| Anchor | UNION % | n_UNION |
|---|---:|---:|
| BY-2020-protest | 54.6 | 273 |
| RU-Navalny | 38.8 | 188 |
| RU-antiwar-2022 | 58.3 | 252 |
| RU-mobilisation-2022 | 59.2 | 218 |
| UA-Maidan-2014 | 76.2 | 231 |
| UA-current-protest | 80.1 | 191 |
| general-protest-action | 58.9 | 275 |

**Pairwise top-100 overlap (per-anchor average)**

| Pair | Avg overlap | Range |
|---|---:|---|
| `small_no_tags × large_no_tags` | 35.0 / 100 | 17–56 |
| `small_no_tags × small_with_tags` | 59.0 / 100 | 39–79 |
| `small_no_tags × large_with_tags` | 29.9 / 100 | 16–50 |
| `large_no_tags × small_with_tags` | 28.4 / 100 | 11–50 |
| `large_no_tags × large_with_tags` | 61.1 / 100 | 45–79 |
| `small_with_tags × large_with_tags` | 31.7 / 100 | 11–49 |

Pattern:

- **Same model, different text representation**: ~60% overlap — the
  model dominates over the input variation.
- **Different model, same text representation**: ~30–35% overlap — the
  model architecture matters more than the input.
- **Cross-model AND cross-text** (`small_no_tags × large_with_tags`
  or `large_no_tags × small_with_tags`): 28–30% overlap — the most
  complementary pairs.

This is the structural reason 4-way UNION delivers a substantial
gain over 2-way: the two "cross-cross" pairs surface the most
divergent slices of the corpus.

**Where the 185 extra newly-surfaced come from.**

In aggregate, the 712 newly-surfaced 4-way candidates break down as:

- 527 also present in the 2-way no-tags UNION (the existing pool)
- 185 new candidates surfaced *only* by adding the tags variants

Spot-checking the 185: the dominant pattern is content where the
title/description is short or generic but the tags carry explicit
event references. Examples (from `BY-2020-protest` only):

- Belarusian-language oppositional commentary (Belsat) where the
  title is generic ("Итоги недели") but tags include "Тихановская",
  "БЧБ-флаг", "протесты в Беларуси".
- Hashtag-heavy short-form video where the description is mostly URLs
  + hashtags, and tags are the primary semantic signal.

These are exactly the cases where the no-tags pipeline was blind.

---

## Final state of the pipeline

After Experiment 1.3, the recommended retrieval architecture is
4-source UNION:

```
                ┌─ e5-small ──┬─ no tags ──→ top-100 per anchor ─┐
                │             └─ with tags  → top-100 per anchor ─┤
   feed_text ──┤                                                  ├─ UNION → 1,105 distinct,
                │                                                  │           712 newly-surfaced
                └─ e5-large ──┬─ no tags ──→ top-100 per anchor ─┤
                              └─ with tags  → top-100 per anchor ─┘
```

Storage and runtime cost on M2 16 GB:

| Asset | Size | Wall time (one-off) |
|---|---|---|
| `videos.lance` | 95 MB | 6.5 min |
| `videos_e5large.lance` | 250 MB | 32 min |
| `videos_with_tags.lance` | ~95 MB | 12 min |
| `videos_e5large_with_tags.lance` | 499 MB | 40 min |
| **Total** | **~940 MB** | **~90 minutes** |

Stage B retrieval against any of the four tables: <1 second per
anchor query. The 4-way UNION analysis (`scripts/four_way_ensemble.py`):
~3 seconds.

---

## MariaDB restoration — 2026-05-21

**Goal.** Unblock SQL-side EXPORTs (10, 4, 3, 5, 2) per `docs/EXPORTS_ROADMAP.md` §9 by reloading the `metadata` database from the on-disk dump.

**Method.** Homebrew MariaDB 12.2.2 service was already running. Socket-auth verified for unix user `sulzhytski` (`GRANT ALL PRIVILEGES ... unix_socket WITH GRANT OPTION`) — no password set, by design. Loaded the dump:

```bash
mariadb -u sulzhytski -e "CREATE DATABASE metadata CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
time mariadb -u sulzhytski metadata < metadata_v2.sql   # 3 min 46 s
```

**Verification.** Row counts compared against the canonical reference in `memory/reference_dataset.md`:

| Table | Loaded | Reference | Δ |
|---|---:|---:|---:|
| VIDEOS | 401,105 | 401,105 | 0 |
| VIDEO_METADATA | 250,339 | 250,339 | 0 |
| STATS | 6,391,272 | 6,391,272 | 0 |
| TAGS | 947,302 | 947,302 | 0 |
| TOPICS | 61 | 61 | 0 |
| VID_TAGS | 7,445,183 | 7,445,183 | 0 |
| VID_TOPICS | 742,463 | 742,463 | 0 |
| SEARCHES | 15,240 | 15,240 | 0 |
| SEARCH_RESULTS | 6,585,886 | 6,585,886 | 0 |

All nine tables match exactly. Database is now the authoritative SQL source for EXPORTs 10/4/3/5/2; SQLite copy (`/tmp/metadata_v2.db`) is no longer required and the conversion scripts (`/tmp/fix_escapes.py`, `/tmp/mariadb_to_sqlite.py`) need not be reconstructed.

**Reproduction.** `mariadb -u sulzhytski metadata -e "<query>"` from any shell; no password, no `.my.cnf` needed.

---

## Validation pass — 2026-05-21

Before shipping all seven EXPORTs, ran a systematic QA pass: 32/32 tests pass, output rowcounts match the logged figures, cross-EXPORT YT_ID sets are identical (engagement / churn / search / hypergraph vertex_stats all = the 21,710 v2 feed set), every internal invariant holds (`best_rank ≤ median_rank`, `visibility_top10 ≤ visibility_top50`, `churned_90 ⊃ churned_30`, `first_seen ≤ last_seen`, per-anchor share_pct sums = 100 ± 0.1, hypergraph degree sums on both sides = incidence cardinality, z-scores ≈ N(0, 1) per cohort).

Three issues found and fixed during the pass; all numbers above are post-fix.

1. **EXPORT 2 collation bug.** Feasibility SQL used `COUNT(DISTINCT TITLE)` under `utf8mb4_unicode_ci`, which silently collapsed case-only and emoji-colour edits (e.g. `🟤 → 🔴`, `Alyona Alyona → alyona alyona`). Fix: `COUNT(DISTINCT BINARY TITLE)`. Headline: 214 → **218** title-edited videos.
2. **EXPORT 7 incidence duplication.** When two raw search terms folded to the same canonical edge on the same DATE (e.g. `беларусь` and `belarus` both → `belarus|2020-09-23`), the same `(video, edge)` pair appeared twice in `incidence.csv`. Fix: dedupe on `(edge_id, YT_ID)` keeping the smallest rank. Headline: 1,680,051 → **1,649,409** incidences. Vertex degrees and edge sizes were already correct (they used `nunique`); only the incidence file leaked the duplicates.
3. **EXPORT 6 output cosmetics.** Stats CSV first column was unnamed `index` (artefact of `reset_index()` over a dict-constructed DataFrame); now named `canonical_tag`. Added a reader note to the script docstring: pass `keep_default_na=False` when loading the map, because some YouTubers use string-literal tags like `"Null"` / `"NA"` that pandas' default na_values would silently coerce to NaN.

No EXPORT was structurally wrong; the substantive findings are unchanged (Belarus-centric discovery concentration, U > B churn delta, 1 five-term + 6 four-term brokers, etc.). The fixes tightened numerical precision and internal consistency.

---

## EXPORT 7 — search-discovery hypergraph (DONE, 2026-05-21)

**Goal.** Per `docs/EXPORTS_ROADMAP.md` §8: build a hypergraph over the v2 subset and identify *broker* videos that span multiple discovery channels. Direct reply to the manuscript-reviewer request for hypergraph methodology.

**Why hypergraph (not bipartite, not weighted graph).** Each `(canonical_term, DATE)` search event surfaces a *pool* of up to ~500 videos at once. The co-presence structure within a pool is genuine many-to-many: two videos that consistently appear in the same pools share an algorithmic neighbourhood that neither a bipartite projection nor a co-occurrence-weighted graph preserves. The hypergraph keeps the per-event grouping intact.

**Construction.**
- Vertices = 21,710 v2 videos
- Hyperedges = `(canonical_term, DATE)` pairs, term canonicalised via `data/tag_synonyms.csv` (collapses 17 raw → 6 canonical)
- Edge weight = mean RANK of constituent videos (lower = more visible pool)

**Implementation.** `scripts/build_hypergraph.py` — pulls SEARCH_RESULTS via pymysql, computes incidence + edge stats + three vertex centrality measures in pandas, optionally validates counts against `hypernetx.Hypergraph` (gated behind `--skip-hnx` because hypernetx 2.4.0 + recent pandas has a `misc_properties` AttributeError — known upstream issue; pure-pandas path is sufficient for all analyses, hnx is only used for cross-checking node/edge cardinality).

**Output.** Three files under `outputs/hypergraph/`:

| File | Rows | Size | Purpose |
|---|---:|---:|---|
| `incidence.csv` | 1,649,409 | 88 MB | long format `(edge_id, YT_ID, rank, term_canon, DATE)`, deduped on `(edge_id, YT_ID)` keeping best rank — re-importable into any hypergraph library |
| `edges.csv` | 5,388 | 271 KB | per-hyperedge: `term_canon, DATE, n_videos, mean_rank, min_rank` |
| `vertex_stats.csv` | 21,710 | 1.3 MB | per-video: `hyperedge_degree, unique_terms, mean_edge_size, broker_score, best_rank, mean_rank, first/last_seen` |

**Structural numbers.**

| Metric | Value |
|---|---:|
| Vertices | 21,710 |
| Hyperedges | 5,388 |
| Incidences | 1,649,409 |
| Edge size: median / p90 / max | 232 / 656 / 1,719 |
| Vertex degree: median / p90 / max | 6 / 238 / 1,703 |

**Cross-channel distribution** — number of distinct canonical terms each vertex touches:

| `unique_terms` | n_videos | Share |
|---:|---:|---:|
| 1 | 19,101 | 88.0% |
| 2 | 2,477 | 11.4% |
| 3 | 125 | 0.58% |
| 4 | 6 | 0.028% |
| 5 | 1 | 0.005% |

The long tail is the entire point: only 132 videos (0.6%) touch ≥3 canonical search clusters; the **6 four-term and 1 five-term videos are the structural brokers** of the corpus.

**Top brokers — qualitative validation** (described in aggregate; specific videos catalogued in local notes, not in this public log).

The single 5-term super-broker is a Russian-language post-Soviet news broadcaster's live-stream — covers all six canonical clusters by editorial mandate. Theoretically predictable; empirically confirmed.

The 6 four-term brokers are all **explicitly multi-actor in content** by editorial framing: documentaries spanning multiple post-Soviet countries, cross-border political interviews, and conflict explainers that name two or more anchor figures simultaneously. Country-combo distribution among them: UR ×3, BUR ×1, BR ×1, no-country ×1. Each is exactly the kind of cross-channel content the hypergraph metric is designed to surface, and none of them is the *highest-degree* video in the corpus.

By contrast, the **highest-degree videos** (degree 1,400–1,600) reach only 2 canonical terms each — they are *channel celebrities* popular within a single cluster, not brokers across clusters.

**Methodological implication.** Hypergraph degree-centrality on this corpus reveals two distinct video roles that bipartite-graph centrality would conflate:
1. **High-degree, low-term** — "celebrity" videos popular within a single discovery channel.
2. **Moderate-degree, multi-term** — "broker" videos that mediate between channels.

This is the substantive contribution promised to the manuscript reviewer; both populations are individually identifiable in `outputs/hypergraph/vertex_stats.csv` (regenerated locally from MariaDB; not redistributed).

---

## EXPORT 5 — search-rank trajectories + anchor cross-validation (DONE, 2026-05-21)

**Goal.** Per `docs/EXPORTS_ROADMAP.md` §5: per-video search-discovery features from `SEARCH_RESULTS ⋈ SEARCHES`, and a cross-validation check that the 7 v2 anchors retrieve videos surfaced via the *expected* search terms.

**Implementation.**
- `scripts/build_search_features.py` — pulls 1.68M `(YT_ID, DATE, SEARCH_TERM, RANK)` rows via pymysql temp-table join, canonicalises search terms with `canonical_tags` (reused from EXPORT 6), aggregates per video.
- `scripts/anchor_vs_searches.py` — joins per-anchor retrieval set (`outputs/retrieval_nway/all_sources_combined.csv`) with the per-video primary canonical search term.

**Three schema corrections** vs the roadmap, discovered during query construction:
1. `SEARCH_RESULTS.RANK`, not `RANK_POSITION`.
2. `SEARCH_RESULTS.DATE`, not `SEARCH_DATE`.
3. `SEARCHES` PK is composite `(DATE, SEARCH_ID)`. `SEARCH_ID` is *positional within a day* — NOT a term identifier. Joins must use both `DATE` and `SEARCH_ID`.

**Synonyms-table fix.** EXPORT 10 discovered `lukaschenko` (German transliteration) as a fourth Lukashenko spelling not previously catalogued. Added to `data/tag_synonyms.csv`; tests (12/12) still pass. After fix, 17 raw terms collapse to **6** canonical clusters (was 7). EXPORT 6 re-ran: 836,588 → 836,587 distinct canonical tags (negligible Δ).

**Outputs.**
- `outputs/search_features.csv` — 21,710 rows × 12 cols, 1.4 MB. Columns: `YT_ID, n_search_terms_raw, n_search_terms_canon, best_rank, median_rank, mean_rank, first_search_date, last_search_date, visibility_days_top10, visibility_days_top50, n_top10_events, primary_term_canon`.
- `outputs/anchor_vs_searches.csv` — 34 rows (long format), one per `(anchor, primary_term_canon)` cell.

**Discovery-channel concentration.** Sum of canonical search-discovery events for the v2 subset (1.68M rows total):

| Cluster | Events | Share |
|---|---:|---:|
| lukashenko | 835,787 | 49.7% |
| navalny | 389,282 | 23.2% |
| belarus | 221,145 | 13.2% |
| putin | 152,290 | 9.1% |
| ukraine | 81,445 | 4.8% |
| russia | 102 | <0.01% |

**~63% of discovery events came from Belarus-related queries** (lukashenko + belarus). The corpus is structurally a Belarus-centric collection that incidentally surfaced Russian and Ukrainian protest content via algorithmic neighbouring — a sampling-bias finding worth foregrounding in any future methodology section.

**Per-video distribution.** `best_rank` median = 57, p10 = 3, p90 = 369. **5,012 / 21,710 (23.1%)** of v2 videos appeared in top-10 of at least one (term, day). Median video was surfaced by a single canonical term (`n_search_terms_canon` median = 1, p90 = 2).

**Anchor cross-validation.** 100% of `(anchor, YT_ID)` pairs joined to a search-term row. Per-anchor surfacing distribution:

| Anchor | n_videos | Top surfacing terms |
|---|---:|---|
| BY-2020-protest | 273 | lukashenko 59.7%, belarus 39.2% (98.9% combined ✓) |
| RU-Navalny | 188 | navalny 93.6%, putin 4.3% (extremely focused ✓) |
| RU-antiwar-2022 | 252 | putin 43.7%, navalny 34.5%, ukraine 18.3% (diverse, expected) |
| RU-mobilisation-2022 | 218 | navalny 36.2%, ukraine 30.3%, putin 26.1% (multi-channel) |
| UA-Maidan-2014 | 231 | ukraine 60.2%, **lukashenko 18.6%** (unexpected — see below) |
| UA-current-protest | 191 | ukraine 81.7%, belarus 6.8% ✓ |
| general-protest-action | 275 | belarus 26.9%, ukraine 23.3%, lukashenko 22.2%, navalny 21.8% (well-balanced ✓) |

**Notable finding — UA-Maidan-2014 ⟵ lukashenko (18.6%).** 43 of 231 anchor-retrieved Maidan-2014 videos were primarily surfaced by Lukashenko-cluster searches. This is unlikely to be anchor noise (Maidan is well-defined); it reflects **genuine cross-channel overlap** — Belarusian commentary about Maidan circulating in the Lukashenko discovery channel. A previously-invisible cross-border media-flow pattern that the embedding model surfaced.

**Downstream readiness.** Stage E can now consume `visibility_days_top10`, `best_rank`, `n_search_terms_canon`, `n_top10_events` as numeric/categorical features. The `primary_term_canon` column is a clean discovery-channel categorical with 6 levels.

---

## EXPORT 4 — engagement velocity (DONE, 2026-05-21)

**Goal.** Per `docs/EXPORTS_ROADMAP.md` §3: derive per-video engagement features from `STATS` time-series, normalised per `country_combo` so a viral RU video doesn't dominate a quiet BY one. Headline feature for Stage E re-ranking.

**Implementation.** `scripts/build_engagement_features.py` — pulls STATS via pymysql temp-table join (1.6M rows for the v2 subset, in-memory pandas), joins `PUBLISHED_AT` and `country_combo` from `outputs/v2_feed_ready_with_tags.csv.gz`, computes views-by-age windows and z-scores per cohort. Note: actual STATS column is `DATE`, not `SNAPSHOT_DATE` as the roadmap pre-supposed.

**Coverage.** **100%** (21,710 / 21,710 v2 videos have ≥1 STATS snapshot). Of those, **88.3%** have an observation within day-7 of publish, **90.2%** within day-30.

**Output.** `outputs/engagement_features.csv` — 21,710 rows × 18 cols, 3.8 MB. Columns:

```
YT_ID, country_combo, n_snapshots, first_obs, last_obs, days_observed,
age_at_first_obs_days, views_total, views_d7, views_d30,
velocity_d7, velocity_d30, likes_total, comments_total,
like_rate, comment_rate, velocity_d7_z, velocity_d30_z
```

**Distribution sanity (matches roadmap expectations).**

| Feature | Median | p90 | Max |
|---|---:|---:|---:|
| `n_snapshots` | 6 | 237 | 1,213 |
| `days_observed` | 8 | 871 | 1,308 |
| `views_total` | 45,108 | 760,514 | 686,105,101 |
| `velocity_d7` (views/day in week 1) | 5,503 | 54,380 | 13,267,216 |

Heavy-tailed as expected; max-velocity videos correspond to viral mainstream content. Per-cohort z-score normalisation verified: `mean ≈ 0, std = 1` for every `country_combo`.

**Downstream readiness.** Drop-in feature source for Stage E. The `velocity_d7_z` column is the recommended re-ranking key for UNION candidates: highest-z scores within each cohort surface the most viral protest-relevant videos.

---

## EXPORT 3 — privacy / observation churn (DONE, 2026-05-21)

**Goal.** Per `docs/EXPORTS_ROADMAP.md` §4: per-video "churn" indicator based on STATS-gap. `VIDEO_METADATA.PRIVACY_STATUS` is uniformly `public` (verified in EXPORT 2) so STATS-gap is the only available signal.

**Implementation.** `scripts/detect_churn.py` — pulls per-video `MIN(DATE)` / `MAX(DATE)` / `COUNT(*)` from STATS, compares last-seen against the **global** max snapshot date (2024-04-23), labels videos lagging >30 d and >90 d.

**Output.** `outputs/churn_signal.csv` — 21,710 rows × 8 cols, 1.1 MB. Columns:

```
YT_ID, country_combo, first_seen, last_seen, n_snapshots,
churn_lag_days, churned_30, churned_90
```

**Headline numbers (with required caveat below).**

| Threshold | Videos flagged | Share |
|---|---:|---:|
| `churned_30` (>30 d lag) | 17,670 | 81.4% |
| `churned_90` (>90 d lag) | 6,144 | 28.3% |

By cohort (>30 d threshold):

| `country_combo` | n | rate_30 | rate_90 |
|---|---:|---:|---:|
| U | 3,272 | 94.1% | 35.8% |
| UR | 4,963 | 91.4% | 32.2% |
| (none) | 1,040 | 89.1% | 40.7% |
| R | 5,428 | 83.8% | 22.6% |
| BUR | 986 | 73.4% | 24.9% |
| BU | 887 | 72.8% | 29.8% |
| BR | 1,134 | 64.1% | 22.2% |
| B | 4,000 | 62.0% | 24.1% |

**Critical interpretation caveat.** The 81.4% headline figure **does not equal "81.4% of videos are deleted from YouTube"**. STATS row distribution by month is roughly uniform across 2022-09 → 2024-03 (~150K rows/mo) and then drops sharply to 5,980 in April 2024 (capture ended 2024-04-23). The "churn" label therefore conflates three causes:
1. **Search-term decommissioning** — e.g. when a term stopped being polled, every video previously found only through it goes silent.
2. **Top-K eviction** — a video that fell out of the top-K for its surfacing term is no longer touched by the daily scrape, even if YouTube still hosts it.
3. **Genuine privacy / deletion** — the originally-intended signal.

Disentangling these requires either (a) a sampling round against the live YouTube API on a stratified sample of "churned" videos to measure the true deletion rate, or (b) defining churn as a *sudden gap in a previously-dense series* rather than a simple lag-from-global-max. The CSV exposes `n_snapshots` per video so a downstream consumer can apply a stricter definition (e.g. *churned only if n_snapshots ≥ 10 and last_seen < global_max − 90 d*) without re-querying the DB.

Cohort differences are still informative under any interpretation: **Ukrainian-only (U) videos drop out at 94.1%, Belarus-only (B) at 62.0%** — a 32-pp difference that survives whatever cause-attribution one applies.

---

## EXPORT 2 — title / description edits (DONE, 2026-05-21)

**Goal.** Per `docs/EXPORTS_ROADMAP.md` §6: determine whether `VIDEO_METADATA` stores multiple snapshots per video (composite PK on `(YT_ID, DATE)`), and if so, surface per-video title and description edits within the 46-day capture window.

**Implementation.** `scripts/detect_title_edits.py` — connects via pymysql + UNIX socket (no password), runs a two-stage query (aggregate feasibility + full per-snapshot pull for changed videos), reduces to per-video transition counts. New dependency: `pymysql 1.2.0` installed into `.venv_v2`.

**Feasibility.** Confirmed positive on a substantial subset:

| Metric | Value | Share |
|---|---:|---:|
| Distinct videos in `VIDEO_METADATA` | 27,305 | 6.8% of `VIDEOS` (matches `reference_dataset.md`) |
| Multi-snapshot (≥2 captures) | 20,260 | 74.2% of covered videos |
| Capture window | 2024-01-01 → 2024-02-24 (46 days) | — |
| **With TITLE edit** | **218** | 1.08% of multi-snapshot |
| **With DESCRIPTION edit** | **352** | 1.74% of multi-snapshot |
| With UPLOAD_STATUS transition | 110 | 0.54% |
| **Union (any edit)** | **566 videos / 5,136 snapshot rows** | — |

`PRIVACY_STATUS` is invariant: all 250,339 rows are `public` (the snapshot capture only saw public videos). True privacy churn must still come from STATS-gap detection — EXPORT 3 remains unblocked but cannot use this column.

**Pipeline relevance.** 478 of the 566 edited videos (**84.5%**) intersect the v2 21,710-video feed-ready set. (NB: the initial pre-validation count was 214 title edits — the under-count came from a `utf8mb4_unicode_ci` collation that collapsed case-only and emoji-colour edits like `🟤→🔴` or `Alyona Alyona→alyona alyona`. The feasibility SQL now uses `COUNT(DISTINCT BINARY TITLE)` to match Python's binary equality; both sides agree at 218.) — i.e. the edit signal is directly usable as a Stage E feature without re-scoping.

**Outputs.**
- `outputs/title_edits_feasibility.csv` — one-row summary for citation.
- `outputs/title_edits.csv` — 566 rows × 11 cols `(YT_ID, n_snapshots, n_title_uniq, n_desc_uniq, n_upload_uniq, n_title_changes, n_desc_changes, first_date, last_date, first_title, last_title, all_titles)`. 253 KB.

**Notable patterns surfaced** (in aggregate; individual videos catalogued in local notes, not in this public log).

1. **Live-stream title re-purposing** — a small set of news outlets rewrite their live-stream title several times per day to track the news cycle; the most active case in the sample cycled through 18 distinct titles over 27 snapshots.
2. **Cyrillic-homoglyph circumvention** — at least one video cycles between two visually-near-identical versions of the same word by swapping Cyrillic ↔ Latin look-alikes (`е`/`e`, `р`/`p`), evidence of platform-moderation evasion. Full case retained in local notes.
3. **Capitalisation drift** — several videos shift from sentence-case to all-caps variants of the same headline, plausibly chasing thumbnail click-through.

**Research questions opened.** Are the 566 edited videos disproportionately from one `country_combo`? Do edit timestamps cluster around news events? Cross with EXPORT 3 churn signal: do videos that later disappear edit titles first?

---

## EXPORT 6 — canonical tag mapping (DONE, built 2026-05-20, logged 2026-05-21)

**Goal.** Per `docs/EXPORTS_ROADMAP.md` §2: produce a `raw_tag → canonical_tag` mapping that collapses casing, unicode-compatibility forms, whitespace noise, and a curated set of cross-script synonyms (Putin ≡ путин, Lukashenko ≡ лукашэнка, etc.). Fixes the v1 SemNA over-count and gives Stage E a clean tag-feature space.

**Implementation.**
- `scripts/canonical_tags.py` — pure functions `canonicalise()` (NFKC + casefold + strip + collapse whitespace) and `apply_synonyms()` (dict lookup, unknowns pass through). Conflict-detecting `load_synonym_table()`.
- `scripts/build_canonical_tag_map.py` — CLI driver, argparse, 5-step bracketed progress.
- `data/tag_synonyms.csv` — 32 curated `(canonical, variant)` rows seeded from roadmap §2.3.
- `tests/test_canonical_tags.py` — **12 unit tests** covering casefold, whitespace, NFKC, ß-handling, idempotence, conflict detection, end-to-end cross-script pipeline. All pass; full suite is now **32/32**.

**Run.**
```bash
.venv_v2/bin/python scripts/build_canonical_tag_map.py
```

**Results (reproduced 2026-05-21).**

| Metric | Value |
|---|---:|
| Source rows | 350,356 |
| Raw tag instances | 7,445,142 |
| Distinct raw tags | 931,377 |
| Distinct canonical tags | 836,588 |
| **Reduction ratio** | **10.18 %** |

Output files:
- `outputs/canonical_tag_map.csv` — 55 MB, 931,377 rows `(raw_tag, canonical_tag)`. Stage-E feature source.
- `outputs/canonical_tag_stats.csv` — 29 MB, 836,588 rows `(canonical_tag, n_raw_variants, n_instances)`. Citable appendix table.

**Cross-script merge — top fan-in (n_raw_variants).** Validates the curated synonym table is doing real work:

| canonical | n_raw_variants | n_instances |
|---|---:|---:|
| belarus | 23 | 77,329 |
| zelenskyy | 19 | 43,806 |
| lukashenko | 17 | 55,525 |
| ukraine | 16 | 160,054 |
| russia | 16 | 119,251 |
| navalny | 15 | 17,736 |
| putin | 9 | 105,971 |

**Reconciliation with prior estimate.** The roadmap and `reference_dataset.md` (pre-edit) quoted **3.86%** — that figure was case-only duplicates in the MariaDB TAGS dictionary. Full canonicalisation is **2.6× larger**: 10.18%. Three sources of additional collapse beyond plain casing:
1. NFKC compatibility forms (full-width, ligatures) and `casefold()` over `.lower()` (e.g. `ß` → `ss`).
2. Whitespace normalisation (`"foo   bar"` → `"foo bar"`).
3. Curated cross-script synonyms — the dominant contributor; cf. belarus collapsing 23 variants alone.

Memory file `memory/reference_dataset.md` already updated (2026-05-21) to ~10.18% with provenance.

**Downstream readiness.**
1. v1 SemNA bipartite-graph centrality has been overstated by an order of ~10%, not ~4%. v1 re-publish is now a more material change; recommend running the original notebook with the new mapping before any external citation.
2. Stage E can now consume the map directly — join `outputs/canonical_tag_map.csv` to `outputs/v2_feed_ready_with_tags.csv.gz` on tokenised raw tags.

---

## EXPORT 10 — sampling-validity (DONE, 2026-05-21)

**Goal.** Validate the day-count claims in `memory/reference_dataset.md` (Belarus ~1 200 days, Navalny ~1 100, Ukraine ~750, Russia 1) against the loaded MariaDB. Roadmap §7.

**Method.** One SQL against `SEARCHES` (note: actual columns are `DATE`/`SEARCH_ID`, not `SEARCH_DATE`/`id` as the roadmap pre-supposed):

```sql
SELECT SEARCH_TERM, MIN(DATE) AS first_date, MAX(DATE) AS last_date,
       COUNT(DISTINCT DATE) AS days_searched, COUNT(*) AS total_search_events
FROM SEARCHES GROUP BY SEARCH_TERM ORDER BY days_searched DESC;
```

Saved to `outputs/sampling_validity.csv` (17 rows, 805 bytes).

**Verification.** All headline claims confirmed. `SUM(total_search_events) = 15 240` exactly matches the SEARCHES row-count from §MariaDB-restoration above.

| Term (cluster) | days_searched | Reference claim | Match |
|---|---:|---|---|
| belarus / беларусь / белоруссия | 1 197–1 223 | ~1 200 | ✓ |
| лукашенко / лукашэнка / lukashenko / lukaschenko | 1 185–1 203 | (implied ~1 200) | ✓ |
| navalny / навальный | 1 077–1 099 | ~1 100 | ✓ |
| putin / путин | 1 073–1 074 | (implied ~1 100) | ✓ |
| україна / ukraine / украина | 733–739 | ~750 | ✓ |
| russia / russland / россия | 1 each | 1 (single day 2024-04-23) | ✓ |

**New observations not in memory before.**
1. Lukashenko has **four** spellings in the sampling vocabulary, not two: `лукашенко` (Russian), `лукашэнка` (Belarusian), plus Latin `lukashenko` and `lukaschenko` (German-style transliteration).
2. `russia` cluster is sampled on a single date (2024-04-23) by all three transliterations — meaning the "Russia-as-context is undersampled" claim is even stronger than written: it's not just thin, it's a one-day snapshot.
3. `navalny` (Latin) has `days_searched == total_search_events == 1 099` exactly — one search per day, no duplicates; whereas `навальный` shows 28 duplicate-day searches (1 077 days, 1 105 events). Worth checking before any time-series treatment.

---

## Decision log

| Date | Decision | Rationale |
|---|---|---|
| 2026-05-16 | Run Experiment 1.2 (e5-large with tags) | Experiment 1.1 showed +40% UNION gain on e5-small; verify same pattern on e5-large before committing to 4-way ensemble as the new default |
| 2026-05-16 | Treat tags as complementary source, not replacement | Per-anchor newly-surfaced rate *drops* by 15–16 pp when tags replace standard signal, but UNION of all four sources gains +35% over the 2-way no-tags ensemble |
| 2026-05-16 | Adopt 4-way UNION as the recommended retrieval architecture | Headline newly-surfaced rises 527 → 712 (+35%) and 1,105 distinct videos — a meaningful improvement over the previous default |
| 2026-05-21 | Use socket-auth on local MariaDB rather than setting a root password | Avoids storing credentials on disk; `GRANT ALL ... unix_socket` already in place for `sulzhytski@localhost`; matches user preference (verify locally, no extra surface area) |
| 2026-05-21 | Drop the SQLite-copy detour entirely | All SQL EXPORTs can now query MariaDB directly; the `\'`-escape gotcha that motivated the SQLite path no longer applies |
| 2026-05-21 | Treat canonical-tag reduction as ~10.18%, not 3.86% | Verified by re-running `scripts/build_canonical_tag_map.py`; the 3.86% figure was case-only duplicates in the MariaDB TAGS dict, while full NFKC+casefold+whitespace+synonym collapse yields 2.6× more reduction. v1 SemNA correction is therefore a more material change than previously thought |
| 2026-05-21 | Add `pymysql` to v2 environment | Cleanest way to drive MariaDB from Python without C-extensions; required by `scripts/detect_title_edits.py` and any future SQL-driven EXPORT script. Pure-Python, no version risk |
| 2026-05-21 | EXPORT 2 title-edit signal accepted as small but real | 566 videos with any edit; only 1–2% of multi-snapshot videos — but 84.5% intersect the v2 feed-ready set, and one cyrillic-homoglyph circumvention cluster is independently publishable. Worth including as a Stage E binary feature |
| 2026-05-21 | Use `velocity_d7_z` (per-cohort z-score) as primary engagement feature | Headline-velocity differences between RU/UA/BY cohorts swamp within-cohort variation if z-scoring is skipped; per-`country_combo` normalisation surfaces the most viral content *for its peer group*, which is the right notion for re-ranking UNION candidates |
| 2026-05-21 | EXPORT 3 churn signal shipped with explicit conflation caveat | Headline 81.4% "churned" conflates scraper-attention loss with real deletion; downstream consumers must apply a stricter definition (e.g. `n_snapshots ≥ 10 AND churn_lag_days > 90`) or sample-test against the live YouTube API. Cohort delta (U=94.1% vs B=62.0%) is robust under any interpretation |
| 2026-05-21 | Add `lukaschenko` (German transliteration) to synonym table | Discovered during EXPORT 10; was missing from initial `data/tag_synonyms.csv`. EXPORT 5 collapsed from 7 → 6 canonical clusters as a result; EXPORT 6 ratio unchanged (10.18%, Δ = 1 canonical out of 836K). Tests still 12/12 |
| 2026-05-21 | Foreground discovery-channel concentration as a corpus-bias finding | Lukashenko + belarus clusters account for 63% of all v2 search-discovery events; only 4.8% came from Ukraine-cluster queries; Russia barely any. The v2 set is structurally a Belarus-centric collection that algorithmically reached into RU/UA content — this should be stated upfront in any methodology section, not buried |
| 2026-05-21 | Pin `hypernetx>=2.0` with `--skip-hnx` fallback in `build_hypergraph.py` | hypernetx 2.4.0 + recent pandas has an unresolved `misc_properties` AttributeError on `Hypergraph()` construction. All actual analysis runs in pure pandas; hnx was only ever used to cross-check vertex/edge cardinality. Documented in `requirements_v2.txt` |
| 2026-05-21 | Distinguish *celebrities* from *brokers* via hypergraph centrality | Highest-degree videos (degree 1,400–1,600) are channel-internal celebrities reaching only 1–2 canonical clusters. The true cross-channel brokers — a single 5-term super-broker and 6 four-term videos — have moderate degree but span ≥4 canonical clusters. Bipartite-graph centrality would conflate these two roles; the hypergraph separates them |
| 2026-05-21 | Validation pass mandatory before each batch ships | The QA pass caught two real numerical bugs (collation-collapsed title edits, duplicated hypergraph incidences) that the original RESULTS_LOG had under-reported. The pass should be re-run after any future EXPORT script edits — output-vs-claim rowcount checks, cross-EXPORT YT_ID consistency, and within-EXPORT invariants (z-score normality, subset monotonicity, sum-of-parts) are the highest-yield checks |

---

## Next steps (post-experiment)

1. **Add ADR-12 in `ARCHITECTURE.md`** documenting the four-way
   ensemble decision.
2. **Update `notebooks/pipeline.ipynb`** Stage D section with the
   4-way coverage chart, and the cluster-stability section
   verifying that polysemy still reproduces with tags-included
   embeddings (open question, not yet tested).
3. **Extend `pipeline/stage_d_ensemble.py`** to accept N sources via
   a `--source` flag that can be repeated, deprecating the
   hard-coded `--small-csv` / `--large-csv` interface.
4. **Manual inspection of the 185 incremental videos** to verify they
   are genuinely relevant (vs precision loss).

