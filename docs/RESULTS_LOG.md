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

---

## Stage E v1 — ranked protest-video index (DONE, 2026-06-02)

**Goal.** Turn the recall-maximised retrieval pool into a *clean ranked index
of protest videos*. Directly addresses the precision gap the codebook
experiment measured: ~70% of retrieved videos are not *directly* about protest
(`mini_study/` layer-2: 42/60 non-direct). This is the long-deferred Stage E
(ADR §"Decisions deferred"), now unblocked by (a) the 60-item human gold and
(b) the multi-signal EXPORT features.

**Precondition — regen.** Most pipeline outputs were not persisted on disk.
Re-derived the four structural feature tables from MariaDB by pointing the
EXPORT scripts at the no-tags feed (`--feed outputs/v2_feed_ready.csv.gz`):
`engagement_features.csv`, `churn_signal.csv`, `search_features.csv`,
`hypergraph/vertex_stats.csv` — all 21,710 rows, numbers reproduce the figures
logged above. Candidate pool for v1 = the existing e5-large no-tags retrieval
(`outputs/retrieval_e5large/topk_per_anchor.csv`, 496 distinct videos). Full
4-way UNION (1,105) deferred to a background embedding run.

**Component 1 — composite ranking** (`scripts/stage_e_rank.py`). One row per
video; z-scored weighted sum of semantic similarity + `velocity_d7_z` +
hypergraph `broker_score` + search `visibility_days_top10`, plus an
anchor↔`primary_term_canon` consistency bonus and a `churned_90` penalty.
Weights hand-set and documented (60 labels too few to fit). Validated on the
60 gold:

| Ranker | AUC relevant-vs-absent | AUC direct-vs-absent |
|---|---:|---:|
| cosine similarity (baseline) | 0.662 | 0.711 |
| **composite (Stage E)** | 0.667 | **0.744** |

Spearman(composite, relevance ordinal) = 0.355 (p=0.005). Mean index rank
direct 153 < indirect 226 < absent 266 (monotone). Structure adds precision on
the clean direct-vs-absent contrast; the embedding already does most of the
coarse relevant/absent split.

**Component 2 — LLM relevance gate** (`scripts/build_relevance_briefings.py` +
6 Claude sub-agents + `scripts/stage_e_gate.py`). Claude-as-annotator (6
independent sub-agents, Write-only, 83 items each) labelled all 496 on the
`protest_relevance` topic axis (direct/indirect/absent), codebook v0.2 §2.
LLM distribution: direct 123 / indirect 64 / **absent 309 (62%)**. Validated
vs the 60 human gold on the same axis:

| Metric | Value |
|---|---:|
| 3-class accuracy / Cohen κ | 0.750 / **0.611** |
| binary relevant-vs-absent acc / κ | 0.867 / **0.735** |
| human-absent correctly cut | 24/25 |
| human-direct preserved (never cut) | **18/18** |

Confusion shows the gate's only false-negatives are `indirect` (peripheral)
videos pushed to `absent` — `direct` protest is never dropped, the right
failure mode for a precision gate. The LLM (text-only) over-calls `absent`
relative to the human (who watched videos / knew the channel) — the same
info-asymmetry the codebook's 87%-extratextual finding predicts.

**Deliverable.** `outputs/stage_e/protest_index_gated.csv` — **187 videos**
(496 → 187, 38% kept), composite-ranked, direct∪indirect only. Quality on the
29 gold items that survive: **28/29 = 97% are human-protest** (1 absent leaked).
Top-10 is all genuine protest (Navalny court speech / protests; Belarus-2020
post-election protests and dispersals). Per-anchor survivors concentrate on
BY-2020 (62) and RU-Navalny (59), consistent with the Belarus-centric corpus
bias. Trade-off: high precision (97%) at some recall cost (LLM cut 7/35
human-relevant, all peripheral) — the right side for a "clean index".

**Artefacts.** `scripts/stage_e_rank.py`, `scripts/build_relevance_briefings.py`,
`scripts/stage_e_gate.py`; `outputs/stage_e/{protest_index,protest_index_scored,
protest_index_gated}.csv`, `{validation_report,gate_report}.md`,
`relevance_pred/claude_chunk*.jsonl`.

**Next.** Expand pool to full 4-way UNION (1,105); tune composite weights now
that a gate exists; route `indirect`/low-confidence items to human review
(active learning); add channel prior (87%-extratextual lever). Then the
analytics phase (semantic ∪ hypergraph ∪ channel as a structural result).

## Stage E v1.1 — pool expansion to the full 4-way UNION (DONE, 2026-06-02)

**Goal.** Roadmap Task 1: widen the gate's input from the 496-video e5-large
no-tags pool to the recall-max UNION, so more true-protest videos reach the
gate. Done in two increments — first the unblocked **2-way no-tags UNION**, then
(once the user restored `complete_video_info_202404251556.csv`) the **full 4-way
UNION** (no-tags ∪ with-tags × e5-small/large).

**Method.** Stage A embeds of the 21,710-video subset on MPS fp16: e5-small
no-tags (348s → table `videos`), then — after `enrich_with_tags.py` produced
`v2_feed_ready_with_tags.csv.gz` (90.4% tag coverage, median 22 tags/video) —
e5-small+tags (421s → `videos_with_tags`) and e5-large+tags (2582s →
`videos_e5large_with_tags`). Stage B retrieved the 7 anchors top-100 for each.
`scripts/four_way_ensemble.py` UNION:

| pool | distinct | newly-surfaced |
|---|---:|---:|
| e5-large no-tags (v1) | 496 | 327 |
| **2-way** (small ∪ large, no-tags) | **796** | 525 |
| **4-way** (+ both with-tags) | **1,099** | 709 |

Adding the tags variants gives **+184 newly (+35%)** over the 2-way no-tags
UNION — reproduces the historical 4-way finding (1,105 / 712). Pairwise top-100
overlap stays low across encoder×tags configs (28–61/100), confirming the four
sources are complementary, not redundant.

**Incremental gate.** Extended `build_relevance_briefings.py` with
`--exclude-pred-glob` + `--chunk-offset` so each expansion only briefs the NEW
videos and reuses prior labels: 496 → +300 (2-way, chunks 7–10) → +303 (4-way,
chunks 11–14). Claude sub-agents labelled the new chunks. **Both rounds the
agents silently dropped a few items while reporting completeness** (4 in 2-way,
3 in 4-way); a briefing-vs-JSONL coverage diff caught them and they were
hand-labelled into `claude_chunk_fix_dropped*.jsonl`. All 1,099 now carry a
`protest_relevance` label (0 missing, validated).

**Validation (unchanged, by construction).** The 60-item gold is a subset of all
pools and its labels were reused verbatim, so the gate metrics are identical
across v1 / 2-way / 4-way: 3-class κ **0.611**, binary κ **0.735**, **18/18**
human-direct preserved, **24/25** human-absent cut, gold-survivor purity
**28/29 = 97%**. The expansion is precision-neutral on the gold by construction;
it buys recall.

**Deliverable.** `outputs/stage_e/protest_index_gated.csv` — **387 videos**
(v1 187 → 2-way 263 → **4-way 387**, +200 / +107% over v1), 1,099 → 387 kept
(35%). LLM relevance over the 1,099: direct 249 / indirect 138 / absent 712 (65%
cut as topic-noise). Per-anchor survivors (v1 → 2-way → 4-way): BY-2020
62→84→**135**, RU-Navalny 59→79→**96**, general-protest →32→**58**, RU-antiwar
→25→**43**, RU-mobilisation →28→**30**, **UA-Maidan 3→9→14**, UA-current
6→**11**. Every anchor grew; the under-sampled UA anchors more than tripled /
doubled. Top-12 is all genuine `direct` protest (DW News Belarus crackdown /
rallies / strikes, Navalny court speech, Minsk Aug-9 dispersal, Bashkiria
clashes).

**Ranking note (for Task 2).** `best_similarity` is `max` over sources with
different cosine scales. This dipped composite ranking on the noisy 2-way pool
(AUC direct-vs-absent 0.673) but **recovered on the 4-way** (0.740, ≈ v1's
0.744; relevant-vs-absent 0.632; Spearman 0.316, p=0.014) — more videos found by
multiple sources stabilise the max. Composite still beats raw cosine on both
contrasts. Gate **membership** is LLM-label driven (unaffected by score); only
within-index ordering uses the composite. Per-source similarity normalisation
remains a clean Task-2 improvement.

## Stage E v2 — Task 2: composite tuning & ablation (DONE, 2026-06-03)

**Goal.** Roadmap Task 2: with the gate in place, optimise the *ranking* (not
membership). New research harness `scripts/stage_e_tune.py` runs three analyses
on the 60 gold over the 4-way pool — similarity-aggregation comparison, a
leave-one-component ablation, and a 5-fold cross-validated weight search — and
writes `outputs/stage_e/tuning_report.md`. Guarded against overfitting: only the
weight *magnitudes* could overfit (60 labels), so those are reported OOF and the
v1 hand-set magnitudes are kept; the adopted changes are either unsupervised or
ablation-robust.

**Finding 1 — similarity aggregation is the biggest lever.** `best_similarity`
was a `max` over four sources with different cosine scales (the Task-1 caveat).
Z-scoring cosine *within each source* before the cross-source max (`zmax`) is an
unsupervised transform (no label use → no overfit risk) and lifts AUC
direct-vs-absent **0.740 → 0.802**. (`rankmax` 0.782, `zmean` 0.773 also beat raw
max.) Adopted as the default `--sim-agg zmax` in `stage_e_rank.py`.

**Finding 2 — ablation: two components don't earn their weight.** Leave-one-out
on the gold (Δ = full − without, AUC dir-abs): similarity dominates (Δ +0.204),
velocity helps (+0.022), broker a little (+0.004), visibility ≈ 0; but
**consistency_bonus (−0.009) and churn_penalty (−0.029) are negative** — dropping
them *improves* ranking. The 5-fold search independently zeroes both in ~5/5
folds. Mechanism: the LLM gate now does the anti-false-positive job the
consistency bonus proxied for; and the churn penalty demotes genuine *old*
protest content — on the gold, direct videos churn *more* than absent (33% vs
28%), because 2020-era protest footage lost engagement. Both set to **0**.

**Finding 3 — magnitude search is noise.** CV weight search beat hand-set by only
**+0.020** AUC dir-abs (OOF 0.822 vs 0.802) with unstable broker/visibility
magnitudes across folds → kept the documented sim/vel/broker/vis magnitudes
rather than chase 60-label noise. Revisit after Task 4 enlarges the gold.

**Adopted (v2) = `zmax` + `consistency_bonus=0` + `churn_penalty=0`**, sim/vel/
broker/vis unchanged. Re-ran rank + gate on the 4-way pool:

| Ranker | AUC dir-abs | AUC rel-abs | Spearman | mean rank dir/ind/abs |
|---|---:|---:|---:|---|
| v1 (max_raw, hand-set) | 0.740 | 0.632 | 0.316 | 446 / 688 / 729 |
| **v2 (zmax, tuned)** | **0.840** | **0.753** | **0.493** | **274 / 458 / 599** |

The adopted 0.840 sits at the optimistic refit (0.844) yet uses *no* searched
magnitudes, so the gain is principled, not overfit. **Gate membership is
unchanged** — still **387** videos, κ 0.611/0.735, 18/18 direct kept, 24/25
absent cut, 97% gold-survivor purity (the gate is LLM-label driven; only the
within-index ordering improved). Top-10 unchanged in spirit (DW News Belarus
crackdown/rallies/strikes, Navalny court speech) but better separated: mean rank
of `direct` moved 446 → 274. `protest_index.csv` now carries a `sim_agg` column.
Reproduce v1 ranking with `--sim-agg max_raw` and the old weights.

## Stage E Task 3 — channel prior (description-proxy) (DONE, 2026-06-03)

**Blocker resolved by proxy.** Roadmap Step 0 assumed a channel/uploader field in
MariaDB — there is **none** (checked every table in every DB, the feed, and
`complete_video_info`; the only canonical source is the YouTube Data API, which
needs a key + network). With the user's go-ahead we used a **description-proxy
channel**: the Telegram / YouTube-channel / Instagram handle each video promotes
(`scripts/build_channel_features.py`). Imperfect (a promoted link ≠ always the
uploader; ~57% pool coverage) but it cleanly surfaces the codebook-named outlets.

**Channel rates** (over the LLM-labelled pool): top proxy channels by
protest-relevant rate are exactly the expected ones — DW (English/Russian) 100%,
`varlamov` 100%, SOTA Vision 90%, Vot-Tak 85%, Belsat 72%, **UNIAN 71%**,
Current Time, Euroradio, Maxim Katz. 74 channels have ≥2 pool videos (544 videos).

**Concentration (structural finding for Task 5).** Over the 387-video gated
index, 258 (67%) carry a proxy across **89 channels**: **Gini 0.515** (counts are
unequal — a few big outlets + a long singleton tail) but **HHI 0.030 (diffuse)** —
no single dominant hub, top-5 channels = 30% of proxy-covered survivors. So
protest coverage is *spread across many outlets but unevenly* — not the
hub-and-spoke pattern of the PI's Telegram work, at least at this proxy
resolution.

**Ranking lift (honest, leave-one-out).** `channel_relevant_rate_loo` (excludes
the scored video's own label), z-scored, added to the v2 composite. AUC dir-abs
peaks at **w=0.5: 0.840 → 0.860 (+0.020)**, Spearman 0.493 → 0.514; degrades for
w≥1.0. But only **16/60** gold items are proxy-covered → suggestive, not
conclusive, and in the same noise band Task 2 rejected. (With the *full* rate,
production-style, the lift looks bigger — 0.871 — but that has mild self-leak and
is optimistic.)

**Decision.** Wired channel into `stage_e_rank.py` as an **optional, off-by-default**
feature (`--channel-weight`, `CHANNEL_WEIGHT=0`): the capability + table
(`outputs/channel_features.csv`) ship, the qualitative signal is strong, but the
production index is **unchanged** (still 0.840 / 387) — reshaping the public index
on a half-coverage proxy validated by 16 gold items isn't justified. Recommended
`--channel-weight 0.5` once API channels give full coverage or Task 4 enlarges
the gold. Artefacts: `scripts/build_channel_features.py`,
`outputs/channel_features.csv`, `outputs/stage_e/channel_report.md`.

## Stage E Task 4 — active learning: grow the gold (INSTRUMENT READY, 2026-06-03)

**Goal.** Roadmap Task 4: expand the 60-item human gold with the most
*informative* items so κ (which validates the gate) rests on more than 60 labels.
The agent prepares the instrument + the κ-recompute path; it does **not**
fabricate human labels — the PI codes.

**Selection** (`mini_study/build_active_learning_sheet.py`). From the 1,039
uncoded pool videos, tag the gate's uncertain zone: LLM `confidence==1` (97),
`indirect` predictions (130), gate-`absent`-but-high-composite-rank (possible
false-negatives, 130), and kept-but-low-rank (56) — 342 items carry ≥1 tag. An
uncertainty score (3·conf1 + 2·indirect + 2·gate_fn + 1·lowrank) + round-robin
across anchors picks a balanced **wave of 50**: 7–8 per anchor; by LLM label 30
indirect / 19 absent / 1 direct; 48/50 are LLM-low-confidence. This is exactly
the κ-fragile zone (the confident `direct` mass is deliberately under-sampled).

**Instrument (blind, no anchoring).** Three artefacts:
- `mini_study/coding_sheet_round2.csv` — blind sheet (TITLE/DESC/anchor/lang +
  empty `protest_relevance`/confidence/notes; **no LLM label or score shown**).
- `mini_study/coding_round2.html` — self-contained click-to-code UI (direct/
  indirect/absent buttons, 1/2/3 keys, YouTube links so the PI can watch,
  localStorage autosave, Export-CSV). Embeds the 50 items; no server needed.
- `mini_study/round2_selection_manifest.csv` — internal provenance (why each item
  was picked: tags, LLM label, confidence, rank) for the post-hoc flip analysis.

**Recompute path** (`mini_study/merge_round2_gold.py`). Folds round-1 (60) +
the PI's round-2 labels → `mini_study/coding_gold_v2.csv` (≤110 items), skipping
any blank/invalid rows (verified: refuses to run on the empty sheet — no
fabrication), and reports human↔LLM agreement on the new items. Then
`stage_e_gate.py --gold coding_gold_v2.csv` and `stage_e_tune.py --gold …`
recompute κ and re-run the ablation/weight search on the larger gold — which
also firms up the two findings parked on 60 labels (Task-2 magnitude search,
Task-3 channel lift) and answers the roadmap's open question (v1 cut 7/35
human-relevant — does more gold recover any?).

**Status.** Everything is ready; **κ recompute awaits the PI's hand-coding** of
the 50-item sheet (the one step the agent must not do).


## Validation pass — raw dataset (2026-06-10)

Systematic QA of the raw layer (MariaDB dump, `complete_video_info` CSV, feed
derivation). **Everything structural verified exactly**: all 9 table row counts
match the reference; `VIDEOS.YT_ID` and `VIDEO_METADATA (YT_ID, DATE)` are
unique (the latest-snapshot join cannot explode); VID_TOPICS has no duplicate
pairs and no orphans; Politics ∩ metadata = 21,710 exactly; the tags CSV is
key-unique (350,356) with v2 coverage 19,623 / 21,710 = 90.4% (median 22 tags /
346 chars, max 4,982); STATS covers 21,710/21,710; EXPORT-10 day counts
reproduce (incl. `navalny` = exactly 1 search/day, 1,099 = 1,099).

Three issues found and fixed:

1. **«стачк» regex bug.** The protest pattern's `stachk\w*` branch was Latin
   script and matched 0 videos; Belarusian «стачка» (strike) is Cyrillic. Six
   videos contain «стачк», four of which carried no other protest keyword and
   were mislabelled non-protest-mentioning. Fix: added `стачк\w*` to
   `scripts/regen_feed_ready.py` + `notebooks/EDA.ipynb`; regenerated both feeds
   (diff-verified: only the 3 flag columns changed, only those 4 videos;
   `feed_text` byte-identical → embeddings unaffected). `protest_anywhere`
   2,045 → **2,049**. One affected video (`xhwJQhamI_w`, BY-2020 pool) flowed
   downstream: patched `retrieval_e5large_with_tags/topk_per_anchor.csv`, then
   re-ran `four_way_ensemble.py` → `stage_e_rank.py` → `stage_e_gate.py`.
   4-way UNION newly-surfaced **709 → 708** (+183 from tags variants, was
   +184). **All production numbers unchanged**: pool 1,099, gated 387 (same
   membership, same order), AUC 0.840 / 0.753, Spearman 0.493, κ 0.611 / 0.735.
   The lance tables keep the stale flag for the 4 videos until the next
   re-embed (see DATA_MANIFEST flag-drift note).

2. **Corpus funnel quantified** (was qualitative in ADR-2): 282,809
   Politics-topic videos discovered; 21,710 (7.7%) metadata-captured. Capture
   rate by publish year: 2020 6.0%, 2021 3.0%, **2022 1.6%**, 2023 4.9%,
   2024 50.9% — 57% of the corpus published Jan–Feb 2024. Table added to
   `ARCHITECTURE.md` §2; must accompany any claim about historical protest
   waves (survivorship: content deleted before Jan 2024 is invisible).

3. **`outputs/sampling_validity.csv` re-emitted** (17 rows; was missing from
   disk) and added to the DATA_MANIFEST.

Also documented: regenerated-feed flag drift vs historical logs (2,034 → 2,045
pre-fix → 2,049 post-fix; `country_combo` cells ±9) is snapshot/regex
dependence, not a data error — see DATA_MANIFEST note.

## Block-0 instruments ready (2026-06-10)

Pre-built everything that runs the moment the PI codes round-2 (per the
approved development plan, Block 0):

1. **`stage_e_gate.py` upgraded** (output CSVs verified byte-identical):
   κ stratified by gold `round` (round-2 is uncertainty-selected → pooled κ
   is composition-biased; report rounds separately); automatic
   briefing-vs-JSONL coverage check (the sub-agent-drop gotcha is now a loud
   warning, not a manual ritual); confidence-calibration table — already
   informative on round-1 gold: **conf=1 → acc 0.46 (n=13), conf=2 → 0.79,
   conf=3 → 0.89** — supports auto-routing conf=1 to human review.
2. **`mini_study/analyze_round2_flips.py`** — post-hoc flip analysis of the
   active-learning wave (per-tag flip rates, confusion, gate consequences);
   refuses to run on an uncoded sheet.
3. **`mini_study/build_audit_wave.py`** — RANDOM 20-item wave (seed=42),
   stratified by retrieval provenance (8 tags_only / 6 mixed / 6 no_tags_only),
   excludes the 110 coded/queued; blind sheet + `coding_audit.html`. Gives the
   unbiased gate-accuracy estimate on the 603 expansion videos that round-2
   (adversarial by design) cannot. Merge as round 3:
   `merge_round2_gold.py --filled coding_sheet_audit_FILLED.csv
   --round1 coding_gold_v2.csv --round-label 3 --out coding_gold_v3.csv`
   (merge script now preserves/labels rounds).
4. **`tests/test_stage_e_invariants.py`** — golden-numbers regression
   (pool 1,099; gated 387 = direct∪indirect; dist 249/138/712; newly 708;
   κ 0.611/0.735; feed flag 2,049; full label coverage). Suite: **40/40**.

PI workload queued: 50 (round-2) + 20 (audit) items in two click-to-code HTML
instruments. After coding: merge → `stage_e_gate.py --gold coding_gold_v2.csv`
(stratified κ) → `stage_e_tune.py --gold …` → `analyze_round2_flips.py`.

## Infrastructure pass — DB audit + ready-to-run scaffolding (2026-06-11)

**DB audit** (`docs/DATA_GAPS.md`): full column sweep of all 9 tables. Found
unused: topic flags beyond Politics (Military 1,105 / TV 737 — cheap relevance
features; Society degenerate at 99.3%), CAPTION=true 1,638 (also a future
caption-text source), creativeCommon 452, age-restricted 47, EMBEDDABLE=0 249,
live 246, DEFAULT_LANG 12,817. Dead: FAVORITE_COUNT (all 0), SEARCHES.LIMIT
(constant). **Tags are fully regenerable from VID_TAGS (19,624 ≥ CSV's
19,623)** — the complete_video_info CSV dependency is droppable.

**Built and tested** (every script either ran end-to-end or proved its
graceful waiting-for-input exit; suite 40/40; `make help` lists all):

| Block | Script | Status |
|---|---|---|
| audit | `build_static_flags.py` → static_flags.csv | ✅ ran (21,710) |
| 1.1 | `fetch_video_api.py` (+ shared `yt_api.py`, checkpointed) | ⏳ YT_API_KEY (dry-run OK: pool=22 units) |
| 1.2 | `build_channel_features.py --api-csv` (proxy fallback; regression: shared cols identical) | ✅ |
| 1.3 | `channel_expand_pool.py` | ✅ ran (200 cands from 6 channels on proxy) |
| 1.4 | `disentangle_churn.py` | ⏳ video_api.csv |
| 2.1 | `gate_ensemble.py` (same codebook as Claude briefings; disagreements → next human wave) | ⏳ OPENAI_API_KEY |
| 2.4 | `train_distilled_gate.py` | ✅ ran: student OOF-vs-teacher κ3 0.491; vs human κ3 0.375 / κ2 0.385 (teacher 0.611/0.735) — retrain after gold v2 / pool growth; corpus inference 21,710 written |
| 3.1 | `stage_e_ltr.py` | ✅ smoke on 60: LTR LOSES to hand-set (−0.04/−0.10 OOF) — confirms Task-2; real run on gold v2 |
| 3.2 | `data/event_calendar.csv` (17 events) + `build_event_features.py` | ✅ ran (96 in ±7d window) |
| 4.1 | `fetch_metadata_bulk.py` (priority 2022→2021→2020; id cache built: 261,099 ≈ 5,222 units) | ⏳ YT_API_KEY |
| 5.1 | `stage_f_modalities.py` | ✅ ran: hypergraph k=3 → 14,301 (too broad, threshold is the analysis knob), pool-precision proxy 0.183 vs semantic 0.352 |
| 6.1 | `Makefile` (22 targets) | ✅ |

Production index untouched throughout (gate 387 byte-identical; suite green).

## Analytics layer — end-to-end scaffolding (2026-06-11)

New `analytics/` package: every analytical task starts from ONE canonical
table and ends in a markdown report.

- **`analytics/build_master.py`** (`make analytics-master`) — the master join:
  **21,710 × 74** (feed + engagement + churn + search + hypergraph + static
  flags + distilled gate + pool/Stage-E layers + channels + events + gold +
  modalities), prefixed where sources collide, integrity-asserted.
- **`analytics/lib.py`** — shared load/report/figure helpers + Gini/HHI +
  **capture-rate correction** (`data/capture_rates.csv`, from the audited
  funnel; ≤2019 pooled).
- **`analytics/slice.py`** (`make slice Q='…'`) — ad-hoc filter→group→agg CLI
  for questions that don't deserve a module.
- **5 modules + `run_all.py`** (`make analytics`) → `outputs/analytics/INDEX.md`.
  First findings, all 5 green:
  | module | first result |
  |---|---|
  | temporal | raw publish peak 2024-01, but **capture-corrected peak = 2021** — the funnel inverts the temporal story |
  | channels | 89 channels, Gini 0.51 / HHI 0.030; **28 multi-anchor channels** (channel-level brokers) |
  | anchors | 2 off-diagonal discovery anomalies ≥10% (cross-border circulation candidates) |
  | cohorts | B over-represented in the index 1.7× vs feed share |
  | brokers | **hypergraph brokers are a blind spot**: 1/132 of ≥3-term videos in the index (gated rate 1% vs 1.8% baseline) — they rarely enter the semantic pool at all |
- Tests: `tests/test_analytics_master.py` (master invariants + capture-rate
  provenance). Suite **45/45**.

Module contract: `an_<topic>.py` exposing `run(master) -> (path, summary)`,
registered in `run_all.MODULES`. Master rebuild is idempotent and must follow
any upstream artefact change (`make analytics-master && make analytics`).

## Max-out pass — remaining no-input blocks closed (2026-06-11)

1. **Tags from DB** (`make tags-db`): `enrich_with_tags.py --from-db` pulls
   VID_TAGS⋈TAGS — verified **100.0% identical tag SETS** vs the CSV on all
   19,623 shared videos (+1 extra covered). The 174-MB
   `complete_video_info_*.csv` dependency is now removable (tag order differs
   → switch at the next planned re-embed).
2. **EXPORT trajectory** (`make trajectory`): curve shapes from 1.62M STATS
   snapshots + rank dynamics from 1.68M SEARCH_RESULTS rows →
   `outputs/trajectory_features.csv` (burst_ratio, t50, growth_after_d30,
   revival, rank_slope/volatility). **Finding: `direct` videos revive 2.4×
   more often than `absent` (27% vs 11%) and gain 41% vs 22% of views after
   day 30** — protest footage is resurrected, not just consumed at publish.
   Wired into the master (81 cols) and stage_e_ltr features.
3. **Rationale mining** (`make rationales`): 1,099 gate rationales embedded
   (e5-small) + KMeans-12 → `outputs/stage_e/rationale_clusters.md`; most
   error-prone cluster #11 (5/10 gold wrong, n=87) = codebook-v0.3 input.
4. **Distilled gate honesty + mining**: gold now HELD OUT of student training
   → honest κ3 0.311 / κ2 0.276 (was 0.375 optimistic; teacher 0.611/0.735).
   `make distill-mine`: **1,189 outside-pool videos with P(direct)≥0.5**;
   top-200 exported as the third expansion source (67 carry no protest
   keyword = pure embedding blind-spot finds).
5. **Modality threshold sweep** in stage_f: precision proxy rises 0.173→0.258
   for k=2→50, all below semantic 0.352 — the knob + its trade-off are now in
   the report.
6. **Datasheet** `docs/DATASHEET_protest_index.md` (Gebru-style, full lineage
   + limitations) and a **Current state map** section in README.

Suite: 45/45. Master: 21,710 × 81. Production index untouched (387).
