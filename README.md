# Eastern Slavic Protests on YouTube — Semantic Pipeline (v2)

*Project code — semantic retrieval, polysemy induction, ensemble fusion over a multilingual protest-video corpus*

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Jupyter](https://img.shields.io/badge/notebook-jupyter-orange.svg)](https://jupyter.org/)
[![Tests: pytest](https://img.shields.io/badge/tests-pytest-brightgreen.svg)](#testing)
[![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey.svg)](#license)

This repository holds the second-generation analytical pipeline for an
ongoing project on the visual dissemination of Eastern Slavic
anti-government protests on *YouTube*. The project is conducted at the
Department of Slavonic Studies, University of Innsbruck, with support
from the Austrian Academy of Sciences (*go!digital 3.0* programme). The
companion v1 repository ([`youtube-protest-tags`][v1]) implements the
tag-based semantic-network analysis. This v2 pipeline reframes the same
research question through dense multilingual embeddings, vector
retrieval, and ensemble fusion.

[v1]: https://github.com/i-sulzhi/youtube-protest-tags

---

## Authors

- **Ilya Sulzhytski** — PhD Researcher, Department of Slavonic Studies,
  University of Innsbruck (author of this pipeline).
- **Gernot Howanitz** — University of Innsbruck (co-investigator).
- **Magdalena Kaltseis** — University of Innsbruck (co-investigator).

---

## Motivation: what tag-only analysis cannot answer

The earlier tag-based pipeline ([v1][v1]) treats each video exclusively
through its user-supplied tags. Exploratory analysis of the broader
corpus shows two structural limits of that approach:

- **12.6 per cent of videos have no tags at all** — invisible to any
  tag-only method.
- **The literal token *protest* appears in only 9.4 per cent** of the
  21,710-video politics-topic subset used here. The remaining 90.6 per
  cent name protest events through metonymy: by event titles
  (*Майдан*, *Болотная*), by people (*Тихановская*, *Навальный*), by
  slogans, or by visual symbols described in the text (*бело-красно-белый
  флаг*).

A keyword- or tag-anchored retriever therefore misses most of the
material that researchers actually want to study. The v2 pipeline
replaces literal matching with a *semantic-anchor* design: each event
or political context is represented by a short Russian-language
description, and videos are retrieved by their proximity to that
description in a multilingual embedding space.

The methodological contribution is twofold:

- *Empirical.* A reproducible protocol for surfacing politically
  relevant *YouTube* videos that do not name the event by its surface
  keyword, evaluated against the regex-keyword baseline.
- *Theoretical.* A demonstration — using a dual-encoder cross-check
  — that the polysemy of *«протест»* is a property of the Eastern
  Slavic corpus itself, not an artefact of any one embedding model.

---

## Pipeline overview

The pipeline is four sequential stages, each producing inspectable
intermediate artefacts. Each script is a standalone CLI.

| Stage | Input | Operation | Output |
|---|---|---|---|
| **A. Embed** | `outputs/v2_feed_ready.csv.gz` (21,710 videos with title + description) | Encode `passage: TITLE . DESCRIPTION` with both `multilingual-e5-small` (384-dim) and `multilingual-e5-large` (1024-dim) on Apple Silicon MPS, persist with metadata to LanceDB | `outputs/v2_lancedb/` (two tables) |
| **B. Retrieve** | LanceDB table + seven Russian-language *anchor queries* | Cosine search for top-100 videos per anchor; flag whether the literal protest keyword appears in the surface text | `outputs/retrieval{,_e5large}/topk_per_anchor.csv`, `newly_surfaced.csv` |
| **C. Polysemy** | LanceDB filtered to protest-mentioning videos | KMeans (k=8) over the embeddings; report per-cluster top languages, country combos, year range, exemplars | `outputs/polysemy{,_e5large}/cluster_assignments.csv`, `cluster_summary.csv` |
| **D. Ensemble** | Stage B outputs from both encoders | Three fusion strategies — Reciprocal Rank Fusion, CombSUM with min-max normalisation, UNION (recall-max) | `outputs/retrieval_ensemble/{topk,combsum,union}_per_anchor.csv`, `comparison_summary.csv`, `newly_surfaced.csv` |

The `v2_pipeline.ipynb` notebook reads the artefacts and renders the
comparative analysis: encoder cost, per-anchor recall gain, cluster
stability across encoders, and fusion-strategy comparison.

### Seven anchor queries

The anchors are short Russian-language descriptions, chosen to cover
the principal political contexts of the corpus:

- BY-2020-protest *(Belarusian post-election protests)*
- RU-Navalny *(opposition mobilisations 2021)*
- RU-antiwar-2022 *(domestic Russian anti-war actions)*
- RU-mobilisation-2022 *(autumn-2022 partial mobilisation)*
- UA-Maidan-2014 *(Revolution of Dignity)*
- UA-current-protest *(Ukrainian wartime protest action)*
- general-protest-action *(generic protest scene)*

Anchor text is defined in `v2_stage_b_retrieve.py::ANCHORS` and is
treated as data, not code — it is the most important parameter of the
pipeline and is expected to be revised in subsequent iterations of the
research.

---

## Selected findings

Reported in full, with figures, in `v2_pipeline.ipynb`. The headline
findings are:

- **Recall gain over the regex baseline.** Across seven anchors, the
  median share of top-100 hits that contain no surface protest keyword
  is 55 per cent for `e5-small` and 63 per cent for `e5-large`. On hard
  anchors (mobilisation, anti-war, generic protest-action), `e5-large`
  outperforms `e5-small` by 11–18 percentage points.
- **Encoder complementarity.** The two encoders' top-100 lists overlap
  by only 17–56 of 100 videos per anchor. They retrieve different best
  matches, which motivates the ensemble in Stage D.
- **Polysemy is encoder-stable.** KMeans on the protest-mentioning
  subset (k=8) produces eight clusters whose senses correspond
  one-to-one between encoders. Mean cluster purity against country
  combinations is 61–62 per cent in both. This appears to be evidence
  that the polysemy is a property of the corpus rather than an artefact
  of any one model. The eight inferred senses are: EN/DE/RU coverage of
  Belarus 2020; Belsat-style opposition journalism; Russian talk-show
  framing of Lukashenka; EN/RU coverage of Russia and Navalny; bloggers
  on Navalny and the war; mixed-language war commentary; and EN/DE war
  analysis.
- **Ensemble fusion (UNION) compounds recall.** Rank-based and
  score-based fusion (RRF, CombSUM) do not improve recall on this
  corpus because both keep top-K per anchor. UNION fusion — keep every
  video appearing in either ranker's top-K, rank by best-rank-across-
  rankers — surfaces 527 distinct *newly-surfaced* videos (no protest
  keyword in title or description) versus 315 for `e5-small` alone and
  329 for `e5-large` alone. The trade-off is broader candidate sets at
  some cost to precision; the strategy is therefore best paired with
  downstream human review or classifier-based re-ranking.

These findings are pilot evidence in support of the project's main
methodological hypothesis: that multilingual semantic retrieval with
anchor queries surfaces substantially more politically relevant material
than classical lexical search. A direct benchmark against the
regex-keyword baseline is the natural next step.

---

## Repository structure

```
youtube-protest-semantic/
├── pipeline/
│   ├── stage_a_embed.py        Stage A — encode and persist to LanceDB
│   ├── stage_b_retrieve.py     Stage B — anchor retrieval with cosine metric
│   ├── stage_c_polysemy.py     Stage C — KMeans polysemy induction
│   └── stage_d_ensemble.py     Stage D — RRF, CombSUM, UNION fusion
├── notebooks/
│   ├── pipeline.ipynb          Notebook synthesising all four stages
│   └── EDA.ipynb               Exploratory analysis of the text-ready subset
├── scripts/
│   ├── overnight_chain.sh      Sequential orchestrator for the e5-large run
│   └── build_demo_dataset.py   Reproducible demo-data generator
├── tests/
│   ├── conftest.py             pytest path configuration
│   └── test_fusion.py          Twenty unit tests over the fusion helpers
├── data/
│   └── demo/                   Small reproducer dataset (200 YT_IDs + vectors)
├── docs/
│   ├── ARCHITECTURE.md         Design decisions with rationale (ADRs)
│   └── RUNBOOK.md              Common operational tasks
├── requirements.txt            Pinned Python dependencies
├── README.md                   This file
└── LICENSE                     MIT
```

The `outputs/` directory is `.gitignored`. All artefacts are regenerated
by running the four stage scripts in order.

For *why* the pipeline is structured this way, see
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). For step-by-step
procedures (adding an anchor, swapping the encoder, debugging a stage
failure, reproducing a published number), see
[`docs/RUNBOOK.md`](docs/RUNBOOK.md).

---

## Quick start

The pipeline expects a single input artefact, `outputs/v2_feed_ready.csv.gz`,
containing the title, description, country combination, and metadata for
the videos in scope. Producing this file requires access to the
underlying corpus (see [Data access](#data-access)).

```bash
git clone https://github.com/i-sulzhi/youtube-protest-semantic.git
cd youtube-protest-semantic
python3.11 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt

# Stage A — embed
python pipeline/stage_a_embed.py --model intfloat/multilingual-e5-small \
        --batch 32 --table videos
python pipeline/stage_a_embed.py --model intfloat/multilingual-e5-large \
        --batch 8 --table videos_e5large

# Stage B — retrieve
python pipeline/stage_b_retrieve.py --table videos \
        --model intfloat/multilingual-e5-small --out-dir outputs/retrieval
python pipeline/stage_b_retrieve.py --table videos_e5large \
        --model intfloat/multilingual-e5-large --out-dir outputs/retrieval_e5large

# Stage C — polysemy
python pipeline/stage_c_polysemy.py --table videos --out-dir outputs/polysemy
python pipeline/stage_c_polysemy.py --table videos_e5large --out-dir outputs/polysemy_e5large

# Stage D — ensemble
python pipeline/stage_d_ensemble.py

# Notebook
jupyter lab notebooks/pipeline.ipynb
```

End-to-end runtime on a 16 GB M2 (Apple Silicon, MPS): about 40 minutes,
dominated by the `e5-large` Stage A. The remaining stages run in seconds
each.

### Encoder performance on M2 16 GB

| Model | Params | Dim | Batch | Vec/sec | Wall time |
|---|---:|---:|---:|---:|---:|
| `multilingual-e5-small` | 118 M | 384 | 32 | ~25 | 6:34 |
| `multilingual-e5-large` | 560 M | 1024 | **8** | ~11 | 32:01 |

Batch sizes are tuned to avoid thermal throttling. Batches of 16 and 32
on `e5-large` collapse to 3 vec/sec under sustained load; batch 8 holds
its throughput.

---

## Data access

The 21,710-video text-ready subset is the intersection of three
sources:

- The project's *YouTube* metadata collection (~401 K videos,
  September 2020 – May 2024), held in a MariaDB instance.
- The 27,305 videos for which titles and descriptions were captured
  during a 46-day window in early 2024.
- *YouTube*'s `Politics` topic auto-classification.

Re-running the full pipeline therefore requires access to the
underlying corpus or an equivalent *YouTube* fetch. The repository
itself does not ship video content; the `data/demo/` directory (when
present) contains a sample of `YT_ID` values and instructions for
re-fetching titles and descriptions via the *YouTube* Data API v3.

---

## Testing

Twenty unit tests cover the fusion helpers and the boolean-parsing
helper. Four of them are explicit regression tests against bugs found
during development (silent sort-discard in UNION fusion; misclassified
`protest_anywhere` for `NaN` and string-typed inputs).

```bash
pytest tests/ -v
```

The tests run on mock data, complete in under a second, and do not
require the corpus or the embedding models. They are the recommended
way to verify a clean installation.

---

## Limitations

- **Coverage of the corpus.** The 21,710-video subset is 5.4 per cent
  of the 401 K total. Title and description were fetched for only one
  46-day window; full coverage requires further *YouTube* API calls.
- **Linguistic balance.** The corpus is dominated by Russian-language
  content. Ukrainian and Belarusian material is present but much
  smaller; German appears mainly in Western coverage of Belarus 2020
  and the Russo-Ukrainian war. Results are therefore most reliable for
  the Russian-language slice of the ecosystem.
- **No labelled validation set.** Precision of the retrieved candidates
  is assessed qualitatively from sample inspection. A stratified human
  annotation of the *newly-surfaced* set is the planned next step.
- **Clustering assumption.** Stage C uses KMeans, which assumes
  approximately spherical clusters in embedding space. HDBSCAN or
  Gaussian-mixture variants would be more flexible but less directly
  interpretable.
- **Anchor language.** All anchor queries are in Russian. An
  English-language or Ukrainian-language reformulation may surface a
  different slice and is left as an ablation for future work.

---

## Ethical considerations

The corpus consists of metadata from publicly available *YouTube*
videos. The repository does not redistribute the underlying video
content or full text descriptions; only embeddings, retrieval rankings,
and aggregate statistics are persisted. Channel names that appear in
descriptions are not extracted as such; a description-head boilerplate
clustering is reported as a *channel proxy* in aggregate form only.
Use of the embeddings is governed by the *YouTube* API Services Terms
of Service.

---

## Stack

`pandas`, `numpy`, `pyarrow` for the data layer; `sentence-transformers`
with `torch>=2.4` for embedding inference on Apple Silicon MPS;
`lancedb` as an embedded vector store; `scikit-learn` for KMeans;
`matplotlib` and `seaborn` for figures; `pytest` for tests. Pinned
versions are in `requirements_v2.txt`.

---

## References

The companion project notebook ([`youtube-protest-tags`][v1])
contains the project's full bibliography. Methodological references
specific to the v2 design:

- Bail, C. A. (2024). Can generative AI improve social science?
  *PNAS*, 121(21), e2314021121.
- Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009). Reciprocal
  rank fusion outperforms Condorcet and individual rank learning
  methods. *SIGIR '09*, 758–759.
- Wang, L., Yang, N., Huang, X., Yang, L., Majumder, R., & Wei, F.
  (2024). Multilingual E5 text embeddings: A technical report.
  *arXiv:2402.05672*.
- Ziems, C., Held, W., Shaikh, O., Chen, J., Zhang, Z., & Yang, D.
  (2024). Can large language models transform computational social
  science? *Computational Linguistics*, 50(1), 237–291.

---

## Funding

Austrian Academy of Sciences, *go!digital 3.0* programme.

---

## Tooling and assistance

The v2 pipeline was developed with the assistance of Anthropic's
Claude (Opus model family), used as an interactive coding
collaborator for refactoring, regression-bug discovery, unit-test
design, and documentation drafting. The collaboration log is partly
preserved in the commit history (`Co-Authored-By` trailers) and
in [`docs/RESULTS_LOG.md`](docs/RESULTS_LOG.md).

The research question, the corpus design, the anchor formulations,
the choice of methodology, and the interpretation of results are
the responsibility of the authors.

---

## License

Code: MIT (see `LICENSE`). Text and figures: CC BY 4.0. *YouTube*
metadata derivatives are made available under the *YouTube* API
Services Terms of Service.
