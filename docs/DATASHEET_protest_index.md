# Datasheet — `protest_index_gated.csv` (v2, 387 videos)

Datasheet (Gebru et al. 2021 style) for the project's main deliverable: the
clean, ranked, relevance-gated index of post-Soviet protest videos. Update
this file whenever the index changes (membership diff + new κ required).

## Motivation

A precision layer over recall-maximised semantic retrieval: ~70% of retrieved
candidates are not *about* protest (codebook experiment, layer-2). The index
answers: *which YouTube videos in the corpus are actually protest content,
ranked by relevance?* Created within the *Kaleidoscopic Patterns of Protest*
project; built by the PI (Ilya Sulzhytski) with LLM-assisted annotation.

## Composition

- **387 videos** (YT_ID + metadata + scores; no media content), one row each.
- Membership: LLM relevance label ∈ {direct (249 in pool → 230 gated…), see
  `gate_report.md`} — gate keeps direct ∪ indirect from a 1,099-candidate pool.
- Ordering: composite score (z-scored semantic similarity `zmax` + engagement
  velocity + hypergraph brokerage + search visibility; weights documented in
  `stage_e_rank.py`).
- Per-anchor: BY-2020 135, RU-Navalny 96, general 58, RU-antiwar 43,
  RU-mobilisation 30, UA-Maidan 14, UA-current 11.

## Collection process (full lineage)

1. **Discovery** (2020-09 → 2024-04-23): daily YouTube searches, 17 terms in
   6 canonical clusters; 63% of discovery events are Belarus-cluster —
   the corpus is structurally Belarus-centric.
2. **Capture funnel**: of 282,809 discovered Politics-topic videos, 21,710
   (7.7%) got title/description snapshots (Jan–Feb 2024 window); per-year
   capture: 2020 6.0%, 2021 3.0%, **2022 1.6%**, 2024 50.9%
   (`data/capture_rates.csv`). Content deleted before 2024 is invisible.
3. **Retrieval**: 4-way UNION (e5-small/large × ±tags), 7 anchor queries,
   top-100 each → 1,099 distinct candidates.
4. **Gate**: Claude-as-annotator, codebook v0.2 §2 topic axis
   (direct/indirect/absent), every candidate labelled; gate = direct∪indirect.

## Validation (as of 2026-06-11)

| metric | value |
|---|---|
| 3-class κ vs 60-item human gold | 0.611 |
| binary κ | 0.735 |
| human-direct preserved | 18/18 |
| human-absent cut | 24/25 |
| gold-survivor purity | 28/29 (≈97%, CI ~82–100%) |
| ranking AUC direct-vs-absent | 0.840 (in-sample-selected; upper bound) |

Pending: κ on gold v2 (round-2, 50 uncertainty-selected items — report
stratified) + random audit wave (20 items) for the expansion region.

## Known limitations (must travel with the data)

1. Survivorship at the corpus root (funnel above) — historical waves are
   under-covered and deletion-censored.
2. Gate is text-only; 87% of human coding decisions used extra-textual
   information (channel, video) — κ ceiling, not annotator noise.
3. Gold provenance: all 60 round-1 items lie in the original 496-pool region.
4. Channel identity is a description-proxy (57% coverage) until the API fetch.
5. Hypergraph brokers are under-represented (1/132 in the index) — the
   semantic modality misses cross-channel content (see `an_brokers`).

## Recommended uses / non-uses

✔ case selection for qualitative work; ranking protest coverage by outlet,
country cohort, period (with capture correction); seed set for expansions.
✘ prevalence claims about "protest content on YouTube" (sampling); per-year
raw counts without `capture_weight`; stance/framing inference (topic axis
only — frames are a separate, lower-κ layer).

## Distribution & maintenance

YT_ID + labels + scores only (no video content redistributed). Regeneration:
`make rank && make gate` from preserved labels (`relevance_pred/*.jsonl`,
Tier D). Maintainer: the PI. Changes require: membership diff, κ re-check,
RESULTS_LOG entry, golden-test update (`tests/test_stage_e_invariants.py`).
