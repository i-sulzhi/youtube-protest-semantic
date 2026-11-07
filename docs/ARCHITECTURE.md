# Architecture and design decisions

This document captures the substantive design choices behind the v2
semantic-retrieval pipeline. Each entry records the problem the
decision addresses, the choice made, the alternatives considered, and
the trade-offs accepted. Future readers — collaborators, reviewers, or
the author's later self — can use this document to reconstruct *why*
the pipeline looks the way it does.

The format is loosely modelled on [architecture decision records
(ADRs)](https://github.com/joelparkerhenderson/architecture-decision-record).
Decisions are numbered in the order they affected the codebase, not
necessarily the order in which they were made.

---

## 1. Why an embedding-based pipeline at all

**Context.** The v1 pipeline ([`youtube-protest-tags`][v1]) is a
tag co-occurrence semantic network analysis. It treats each video as
a bag of its YouTube tags and builds a bipartite video × tag graph.
Two findings from the v1 work motivated the move:

- 12.6% of videos have no tags at all — invisible to any tag-only
  method.
- The literal token *protest* (in any language) appears in the
  title or description of only 9.4% of the politics-topic subset.

So most politically relevant material in the corpus is either
tag-less or names protest through metonymy (event names, people,
slogans) rather than by the surface keyword.

**Decision.** Replace tag-based retrieval with multilingual sentence
embeddings + cosine similarity search. Use a fixed catalogue of
*anchor queries* — short Russian-language event descriptions — as the
retrieval interface, instead of the user-supplied tag vocabulary.

**Alternatives considered.**

- *Expanded keyword regex.* Hand-crafting a regex from a thesaurus of
  protest synonyms in four languages. Rejected: every event has its own
  vocabulary (Майдан, Болотная, Тихановская, мобилизация), the regex
  becomes unwieldy and still misses the periphery.
- *Topic models (LDA, BERTopic) over title+description.* Rejected at
  this stage: topic models give clusters but not direct retrieval
  against a research question. They remain a candidate for a later
  comparative exercise.
- *Full-text LLM scoring.* "Does this video discuss the 2020 Belarus
  protests?" asked of each video individually via a generative LLM
  call. Rejected on cost and reproducibility grounds — embeddings are
  deterministic and re-runnable.

**Trade-offs.** Embeddings depend on the encoder model. The same
corpus embedded with different encoders gives different best matches
(see Decision 5). The mitigation is to use two encoders and ensemble
their results (Decision 8).

[v1]: https://github.com/i-sulzhi/youtube-protest-tags

---

## 2. Why the 21,710-video subset, not the full 401K corpus

**Context.** The full project corpus is 401,105 videos. However:

- Title and description (`VIDEO_METADATA`) were captured only during a
  46-day window in early 2024 — covering 27,305 videos (6.8% of the
  total).
- After intersecting that with the YouTube auto-classification
  `Politics` topic, 21,710 videos remain.

**Decision.** Work on the 21,710-video subset for now. Document the
coverage gap explicitly. Plan re-fetching the missing metadata via the
YouTube Data API as a first-year work-package of subsequent funding.

**Alternatives considered.**

- *Use tags as a proxy for title/description.* Rejected — tags are
  much shorter and have a strong fashion / SEO bias that makes them a
  poor signal for semantic content.
- *Re-fetch metadata immediately.* Rejected at this stage on quota and
  scheduling grounds; not on technical grounds. Estimated cost is
  approximately 7,500 batch requests to `videos.list?part=snippet`
  (50 IDs per request) — well within standard quota of 10,000
  units/day.

**Trade-offs.** Findings are pilot evidence on a high-quality
subsample, not on the full corpus. The 27,305-video capture window
biases toward whichever events were active in early 2024 (the
Russo-Ukrainian war and continuing Belarus aftermath); pre-2024
events such as Euromaidan-2014 are present mainly through
retrospective coverage rather than contemporaneous reporting.

**Quantified funnel (validated against MariaDB, 2026-06-10).** The
search archive discovered **282,809** Politics-topic videos in total;
the 21,710 in the corpus are **7.7%** of that population — the subset
still public and surfacing during the Jan–Feb 2024 capture window.
Capture rate by publish year:

| Publish year | In corpus | All Politics | Capture rate |
|---|---:|---:|---:|
| ≤2019 | 756 | 7,040 | 10.7% |
| 2020 | 939 | 15,566 | 6.0% |
| 2021 | 1,134 | 37,338 | 3.0% |
| 2022 | 1,489 | 95,178 | **1.6%** |
| 2023 | 5,037 | 103,416 | 4.9% |
| 2024 (Jan–Feb) | 12,355 | 24,271 | 50.9% |

57% of the corpus was published in Jan–Feb 2024; ~80% in 2023–24. The
protest waves of interest (Belarus 2020, Navalny 2021, antiwar /
mobilisation 2022) sit in the worst-covered years, and content deleted
before January 2024 cannot appear at all (survivorship). Any claim
about the historical waves must carry this table.

---

## 3. Why `multilingual-e5` as the encoder family

**Context.** The corpus is multilingual (Russian, Ukrainian,
Belarusian, German, English). The retrieval queries are Russian. A
mono-lingual encoder is therefore unsuitable.

**Decision.** Use `intfloat/multilingual-e5-small` (384-dim, 118 M
parameters) and `intfloat/multilingual-e5-large` (1024-dim, 560 M
parameters) — both run locally on Apple Silicon via MPS.

**Alternatives considered.**

- *LaBSE* (Language-Agnostic BERT Sentence Embedding). Older, slower,
  weaker on retrieval benchmarks per the e5 technical report (Wang et
  al., 2024).
- *paraphrase-multilingual-mpnet-base-v2*. Solid baseline, but
  outperformed by `e5-large` on MIRACL and other multilingual
  retrieval evaluations.
- *bge-m3*. Strong on benchmarks but its tokenizer treatment of mixed
  Cyrillic + Latin scripts in our corpus was noisier in pilots; e5
  preserved better behaviour on hashtag-heavy descriptions.
- *OpenAI ada-002 or text-embedding-3-large.* Rejected for
  reproducibility (closed-source, may change), cost, and the explicit
  goal of an offline pipeline.

**Trade-offs.** e5-small is fast (6:34 on 21,710 videos) but coarser;
e5-large captures finer distinctions but takes 32 minutes and requires
thermal management on M2 (Decision 4). We use both, deliberately.

---

## 4. Why `--batch 8` for `e5-large` on M2 16 GB

**Context.** Empirically tested three batch sizes on M2 16 GB with
MPS backend and fp16 weights:

| Batch | Throughput | Behaviour |
|---:|---:|---|
| 32 | starts 6 vec/s, falls to 3 vec/s | Severe thermal throttling; killed after timeout |
| 16 | 3 vec/s sustained | Mild throttling, estimated 2 h total |
| 8 | ~11 vec/s | No throttling, 32 minutes total |

**Decision.** Default to `--batch 8` for `e5-large`. Document the
constraint in the README and in `requirements.txt` comments.

**Alternatives considered.**

- *Smaller batch (4).* Even more thermal headroom but lower
  throughput; no advantage on M2 16 GB.
- *Mixed precision (fp32 + fp16 fallback).* The current `model.half()`
  setup already uses fp16 for inference; no further gain available.
- *Cloud GPU.* Cost and the offline-pipeline goal argue against; would
  also reduce reproducibility of the timing claims.

**Trade-offs.** The batch=8 setting is hardware-specific. On NVIDIA
or larger Apple Silicon (M3 Max, M4 Max with more memory) larger
batches would likely be optimal. The CLI flag `--batch` makes this
adjustable without code changes.

---

## 5. Why two encoders rather than one

**Context.** Empirical observation early in the pipeline: the top-100
hit lists from `e5-small` and `e5-large` for the same anchor query
overlap by only 17–56 of 100 videos. The two encoders surface different
videos from the same corpus.

**Decision.** Run both encoders, persist both LanceDB tables, and
build the ensemble (Decision 8) on top.

**Alternatives considered.**

- *Use the larger encoder only.* The marginal recall gain in
  newly-surfaced material from adding the small encoder via UNION is
  +60% on the full corpus. Discarding e5-small loses that gain.
- *Train a custom encoder fine-tuned on protest-relevant texts.* No
  labelled training set available. Reserved for future work after a
  human-labelled validation set is built.

**Trade-offs.** Doubles storage and Stage A runtime. The storage cost
is modest (95 MB + 250 MB = 345 MB total), the runtime cost is bounded
because Stage A runs only once per corpus version.

---

## 6. Why LanceDB rather than FAISS / Qdrant / Pinecone

**Context.** Need a way to persist 21,710 vectors per encoder, search
them by cosine similarity, and keep the surrounding metadata
(country combo, publication date, protest flags) for post-filtering.

**Decision.** Use [LanceDB](https://lancedb.com): embedded vector
store, files on local disk, no daemon, Python-first API.

**Alternatives considered.**

- *FAISS* (Facebook AI Similarity Search). Vectors only; no metadata
  columns. Would need a parallel SQLite store for metadata, with
  manual join logic at search time.
- *Qdrant* / *Weaviate.* Excellent feature sets but require running a
  service. Mismatch with the offline-pipeline goal.
- *Pinecone.* Cloud-hosted, paid, ties to a vendor. Same reasons as
  the OpenAI-encoder rejection in Decision 3.
- *Plain numpy + dot product.* Adequate for 21,710 vectors; would
  become awkward when the corpus grows. The LanceDB API is also more
  ergonomic for filter-then-search ("only videos with
  `protest_anywhere = True`").

**Trade-offs.** LanceDB is a younger project than FAISS or Qdrant —
API has changed between versions during development. The
`requirements.txt` pin (`lancedb>=0.10`, tested 0.30.2) is the
mitigation. The reliance on `pyarrow` as a transitive dependency
adds some installation weight.

### 6a. Why explicit `.metric("cosine")` at search time

LanceDB's default search metric is squared L2 (Euclidean). For
L2-normalised vectors this is monotonic with cosine similarity, so the
ranking is correct, but the absolute distance values returned are
`2 - 2·cos_sim`, not `1 - cos_sim`. Reporting "similarity = 1 - _distance"
under the default metric therefore gives `2·cos_sim - 1`, off by a
linear transformation from true cosine.

This was a latent bug in early Stage B drafts. Stage B now calls
`.metric("cosine")` explicitly so that `_distance = 1 - cos_sim`
unambiguously. The fix preserves backward-compatible rankings (the
transform is linear monotonic) but makes the reported numbers
interpretable as cosine similarity.

---

## 7. Why KMeans (k=8) for polysemy induction

**Context.** Stage C asks: when we restrict to videos that mention
protest by surface keyword, does the embedding space group them into
distinct sub-senses? The answer is an empirical clustering question.

**Decision.** Run `sklearn.cluster.KMeans` with `n_clusters=8` and
fixed `random_state=42`. Report per-cluster top language, country
combo, year range, and exemplar titles.

**Alternatives considered.**

- *HDBSCAN.* Density-based, no need to specify cluster count. Was
  tried in a pilot: it produced a single large noise cluster plus
  several small dense ones. The number of "real" clusters varied
  unpredictably with the `min_cluster_size` parameter, making
  cross-encoder comparison harder.
- *Gaussian mixture models.* Allow soft cluster assignments and
  non-spherical clusters. Reserved for future work; harder to
  interpret as discrete "senses".
- *Different k.* Tried k = 4, 6, 8, 10, 12 informally. k = 8 was the
  smallest k that consistently produced separable language × country
  combinations across both encoders.

**Trade-offs.** KMeans assumes approximately spherical clusters in
embedding space, which is restrictive but interpretable. The fact
that the same eight clusters emerge from two independent encoders
(small and large) is the main robustness check; the consequence is
that the *interpretation* of clusters as discrete senses is robust
even if the clustering algorithm itself is simplistic.

---

## 8. Why three fusion strategies, and why UNION won

**Context.** Two encoders, two top-100 lists per anchor. Need a
principled way to combine them.

**Decision.** Produce three fused result sets:

- **RRF** (Reciprocal Rank Fusion, k=60) — rank-based, robust to
  score-scale differences, biases toward consensus picks.
- **CombSUM** with min-max normalised similarity — score-based,
  balanced between precision and recall.
- **UNION** — keep every video appearing in either top-100, rank by
  best-rank-across-rankers.

Compare all three by per-anchor newly-surfaced rate and by distinct
video coverage.

**Outcome.** RRF and CombSUM keep top-K per anchor, so distinct
video coverage stays near the single-encoder count (~500). RRF
additionally *lowers* the newly-surfaced rate because consensus
picks tend to share surface keywords. UNION lifts the distinct count
to 799 (a 60% gain) and the newly-surfaced count to 527 (against
315 / 329 for the single encoders).

**Decision.** Ship all three; recommend UNION as the default for the
project's downstream task (broad human review of candidate
material), with the explicit caveat that UNION is wider and noisier.

**Trade-offs.** UNION's wider candidate set is a feature for recall
and a liability for precision. A future Stage E (classifier-based
re-ranking on a labelled set) would address the precision side.

---

## 9. Why anchor queries are in Russian, not English

**Context.** The corpus is multilingual but Russian-dominant
(approximately 80% of the politics-topic subset by language
heuristics on text). Anchor query language affects which subset of
the corpus is best matched.

**Decision.** Write all seven anchor queries in Russian, with explicit
mentions of event names in their original spelling (Майдан, Болотная,
Тихановская, бело-красно-белый флаг). Treat anchor wording as data,
not code — defined in `pipeline/stage_b_retrieve.py::ANCHORS` and
expected to be revised across project iterations.

**Alternatives considered.**

- *English-language anchors.* Would shift retrieval toward the
  English-language subset (DW, Reuters, AP, ARTE). Useful as a
  comparison/ablation but loses the dominant-language slice.
- *Anchor per language.* One query each in Russian, English, German,
  Ukrainian. Increases anchor count by 4× and makes per-anchor
  newly-surfaced metrics harder to interpret. Reserved as a future
  ablation.

**Trade-offs.** Russian-only anchors give us the cleanest baseline
for the dominant-language slice, at the cost of under-sampling
videos whose entire surface vocabulary is in English or German.
Multilingual e5 still retrieves cross-language matches — the top-100
for `BY-2020-protest` includes English-language DW videos — but a
dedicated English anchor would surface different material.

---

## 10. Why the demo dataset strips TITLE and DESCRIPTION

**Context.** The demo dataset (`data/demo/`) ships pre-computed
embedding vectors for 200 videos so that someone cloning the repo
can verify the pipeline end-to-end without API access to YouTube.
The vectors are derivatives of the original title + description text.

**Decision.** Ship the embedding vectors and aggregate metadata
(language, country combo, publication date, protest flags) but blank
the `TITLE`, `DESCRIPTION`, and `feed_text` columns to empty strings.

**Alternatives considered.**

- *Ship YT_IDs only, no vectors.* Maximally conservative, but the
  demo could not exercise Stages B/C/D — defeats the purpose of
  demonstrating the pipeline.
- *Ship vectors **with** original text.* Maximally reproducible, but
  redistributes copyright-bearing creator content under a wide-open
  MIT-licensed repository — a stretch even under academic fair use,
  and arguably contravenes the YouTube API Services Terms of
  Service (§4 on redistribution of content).
- *Encrypted text shipped under a click-through agreement.* Out of
  scope for a research code repository.

**Trade-offs.** The pipeline runs cleanly on the demo (Stage B
returns rankings, Stage C clusters, Stage D fuses), but the
output CSVs have empty title and description columns. A user who
wants to see the actual matched videos must re-fetch the texts via
`videos.list?part=snippet&id=...` against the YouTube Data API. This
is a deliberate trade-off in favour of clean licensing.

---

## 11. Why `pytest` and twenty unit tests over fusion helpers

**Context.** During development we found three correctness bugs in
the fusion logic (UNION rank discarded, boolean parsing fragile,
LanceDB metric defaulting to L2²). All three slipped past visual
inspection because the *aggregate* metrics they affect remained
plausible.

**Decision.** Add `tests/test_fusion.py` with twenty unit tests
covering `_to_bool`, `add_rank_and_norm`, `merge_rankers`,
`fusion_rrf`, `fusion_combsum`, and `fusion_union`. Four of them are
explicit regression tests against the bugs we fixed.

**Alternatives considered.**

- *Integration tests with the real corpus.* Useful but slow; require
  the LanceDB tables and the encoder weights. Belong in a separate
  `tests/integration/` directory if added later.
- *Property-based testing (Hypothesis).* Considered for the rank
  functions. Postponed — the current explicit test cases give better
  human-readable failure modes for the regressions we have already
  encountered.

**Trade-offs.** Twenty tests run in 0.5 seconds and need no external
data, so adding them to a CI run is essentially free. The four
regression tests are the highest-leverage: each documents a real bug
and ensures it cannot return.

---

## 12. Why the four-way ensemble includes tags as a parallel input

**Context.** The default v2 pipeline (Decisions 5, 8) was a two-way
ensemble of `e5-small` and `e5-large` over the same `feed_text`
representation (title + description). YouTube user-tags from the
`VID_TAGS` table were *not* used at this stage. A pilot experiment
asked: does adding the tags column to `feed_e5` improve retrieval?

**Empirical answer.**

When tags are added to a *single* encoder (replacing some of the
description budget with `" . теги: " + tags[:500]`), the per-anchor
newly-surfaced rate *drops* by 15–16 percentage points at the
median:

| Source | Newly-surfaced count |
|---|---:|
| `e5-small` no tags (baseline) | 315 |
| `e5-small` with tags | 296 |
| `e5-large` no tags (baseline) | 329 |
| `e5-large` with tags | 278 |

But the top-100 lists of the with-tags and no-tags variants overlap
by only 28–61% within a single encoder family (and 28–30% across
encoder families). The two variants surface *different* videos.
Taking their UNION as a four-way ensemble yields:

| Method | Distinct videos | Newly-surfaced |
|---|---:|---:|
| 2-way UNION (no tags only) | 799 | 527 |
| **4-way UNION** | **1,105** | **712** |

A +35% gain in newly-surfaced over the previous 2-way default, and
+116% over the best single encoder. The architecture rationale is
identical to Decision 5 (two encoders rather than one): adding a
complementary perspective lifts recall at the cost of some
precision, and the precision cost is the right side of the
trade-off for our downstream task of broad human review.

**Why tags hurt single-encoder retrieval but help fusion.**

Tags often contain protest-related words directly (e.g.
*«беларусь протесты»*, *«митинг»*) even when the title and
description do not. When concatenated into the encoder input, they
*amplify* the keyword signal for videos whose surface text was
already protest-relevant — those videos rank higher, displacing the
*newly-surfaced* candidates the embedding was designed to find.
Used as a *separate* retrieval source and then UNION-ed, the
with-tags variant complements rather than competes with the
no-tags one: it surfaces a different slice of the corpus
(Belarusian-language Belsat-style commentary, hashtag-heavy
short-form video) that the no-tags pipeline systematically misses.

**Decision.** Persist four LanceDB tables — `videos`,
`videos_e5large`, `videos_with_tags`, `videos_e5large_with_tags` —
and combine all four at retrieval time via UNION. The implementation
lives in `scripts/four_way_ensemble.py` for now; a future refactor
will extend `pipeline/stage_d_ensemble.py` to accept a list of
sources via repeated `--source` flags.

**Alternatives considered.**

- *Replace the no-tags embedding with the with-tags embedding.*
  Rejected: single-encoder newly-surfaced rate drops without
  compensating gain.
- *Use tags only for post-filtering* (e.g., re-rank candidates by
  tag-anchor TF-IDF). Reasonable, but harder to evaluate and not
  yet implemented. Reserved as a Stage E refinement.
- *Train a fine-tuned encoder on (title + description + tags).*
  Out of scope until a labelled validation set is built.

**Trade-offs.**

- Storage cost doubles for embeddings: ~940 MB of LanceDB tables
  for the four sources (from ~345 MB for two).
- Stage A runtime doubles: ~90 minutes for all four, vs ~45 for the
  no-tags pair.
- The 4-way candidate set is wider and necessarily noisier than the
  2-way one. Precision-recall trade-off — for the project's broad
  recall task, the trade-off is acceptable.

The full empirical reasoning is logged in
[`RESULTS_LOG.md`](RESULTS_LOG.md).

---

## Decisions explicitly deferred

The following choices are not yet made and are flagged for future
work:

- **Stage E classifier.** A re-ranker on (embedding + country combo +
  tag features + channel proxy) trained on a human-labelled set.
  Blocked on the labelled set, which is the next research output.
- **Multimodal extension.** Use of vision-language models on
  thumbnails or selected frames. Mentioned in funding documents as a
  later project phase; no code yet.
- **Anchor refinement.** Narrower temporal anchors (Bolotnaya-2011,
  October-2020 Belarus women's march, autumn-2022 mobilisation) and
  anchor-language ablations.
- **Full-corpus extension.** Re-fetch metadata for the remaining
  ~374,000 videos via YouTube API, embed, and rerun the polysemy
  clustering on the larger sample.

---

## References

- Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009). Reciprocal
  rank fusion outperforms Condorcet and individual rank learning
  methods. *SIGIR '09*, 758–759.
- Wang, L., Yang, N., Huang, X., Yang, L., Majumder, R., & Wei, F.
  (2024). Multilingual E5 text embeddings: A technical report.
  *arXiv:2402.05672*.
- Ziems, C., Held, W., Shaikh, O., Chen, J., Zhang, Z., & Yang, D.
  (2024). Can large language models transform computational social
  science? *Computational Linguistics*, 50(1), 237–291.
