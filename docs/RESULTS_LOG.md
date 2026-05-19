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

## Decision log

| Date | Decision | Rationale |
|---|---|---|
| 2026-05-16 | Run Experiment 1.2 (e5-large with tags) | Experiment 1.1 showed +40% UNION gain on e5-small; verify same pattern on e5-large before committing to 4-way ensemble as the new default |
| 2026-05-16 | Treat tags as complementary source, not replacement | Per-anchor newly-surfaced rate *drops* by 15–16 pp when tags replace standard signal, but UNION of all four sources gains +35% over the 2-way no-tags ensemble |
| 2026-05-16 | Adopt 4-way UNION as the recommended retrieval architecture | Headline newly-surfaced rises 527 → 712 (+35%) and 1,105 distinct videos — a meaningful improvement over the previous default |

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

