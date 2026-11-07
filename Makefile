# Stage E+ pipeline — one command per step. `make help` lists everything.
# Scripts are checkpointed/guarded: anything waiting on input (PI coding,
# YT_API_KEY, OPENAI_API_KEY) exits with instructions instead of failing.

# Python: the project's own .venv (Mac or Windows), else the Mac's shared env next door, else python3.
# Override with `make V=path/to/python`.
V ?= $(firstword $(wildcard .venv/bin/python .venv/Scripts/python.exe ../protest_tags/.venv_v2/bin/python) python3)

.PHONY: help verify test flags events channels expand-channel rank gate \
        gold-v2 flips audit-wave api-video api-bulk churn-attr ensemble \
        ensemble-report distill ltr modalities retune

help:           ## list targets
	@grep -E '^[a-z0-9-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

verify:         ## what's cached vs needs regen (tiers A–D)
	$(V) scripts/verify_outputs.py

test:           ## full pytest suite incl. golden-number invariants
	$(V) -m pytest tests/ -q

# --- features (run NOW, no external input) --------------------------------- #
flags:          ## static flags from MariaDB (topics, captions, license…)
	$(V) scripts/build_static_flags.py

events:         ## event-window features from data/event_calendar.csv
	$(V) scripts/build_event_features.py

channels:       ## channel features (proxy now; API when video_api.csv exists)
	$(V) scripts/build_channel_features.py $(if $(wildcard outputs/video_api.csv),--api-csv outputs/video_api.csv,)

expand-channel: ## candidates from protest-heavy channels (Block 1.3)
	$(V) scripts/channel_expand_pool.py $(if $(wildcard outputs/video_api.csv),--api-csv outputs/video_api.csv,)

# --- core Stage E ----------------------------------------------------------- #
rank:           ## composite ranking over the 4-way pool
	$(V) scripts/stage_e_rank.py --pool outputs/retrieval_nway/all_sources_combined.csv

gate:           ## LLM gate + κ (+ stratified by round when gold has one)
	$(V) scripts/stage_e_gate.py $(if $(wildcard mini_study/coding_gold_v2.csv),--gold mini_study/coding_gold_v2.csv,)

retune:         ## tuning harness on the best available gold
	$(V) scripts/stage_e_tune.py $(if $(wildcard mini_study/coding_gold_v2.csv),--gold mini_study/coding_gold_v2.csv,)

# --- after the PI codes (Block 0) ------------------------------------------- #
gold-v2:        ## merge round-2 labels → coding_gold_v2.csv (refuses if uncoded)
	$(V) mini_study/merge_round2_gold.py

flips:          ## did the active-learning targeting work? (after gold-v2)
	$(V) mini_study/analyze_round2_flips.py

audit-wave:     ## (re)build the random audit instrument (already generated)
	$(V) mini_study/build_audit_wave.py

# --- YouTube API (Block 1/4; need YT_API_KEY env) --------------------------- #
api-video:      ## channels + availability for the 1,099 pool (~22 quota units)
	$(V) scripts/fetch_video_api.py --scope pool

api-video-feed: ## same for all 21,710 (~435 units)
	$(V) scripts/fetch_video_api.py --scope feed

api-bulk:       ## backfill 261K missing Politics metadata (~5,222 units)
	$(V) scripts/fetch_metadata_bulk.py --quota-budget 9000

churn-attr:     ## deletion vs scraper-loss attribution (needs video_api.csv)
	$(V) scripts/disentangle_churn.py

# --- second annotator / distillation (Block 2) ------------------------------ #
ensemble:       ## GPT-4o double-labels the pool (needs OPENAI_API_KEY, ~$$4)
	$(V) scripts/gate_ensemble.py

ensemble-report: ## agreement report from existing GPT predictions (no key)
	$(V) scripts/gate_ensemble.py --report-only

distill:        ## train the local distilled gate + corpus-scale inference
	$(V) scripts/train_distilled_gate.py

distill-mine:   ## recall candidates from the distilled corpus scan
	$(V) scripts/distill_expand_pool.py

rationales:     ## cluster the gate's rationales → systematic error modes
	$(V) scripts/mine_rationales.py

trajectory:     ## curve-shape + rank-dynamics features from STATS/SEARCH_RESULTS
	$(V) scripts/build_trajectory_features.py

tags-db:        ## rebuild the with-tags feed from MariaDB (no big-CSV dependency)
	$(V) scripts/enrich_with_tags.py --from-db

# --- ranking research / analytics (Blocks 3/5) ------------------------------ #
ltr:            ## learned ranker OOF vs hand-set composite (real run: gold v2)
	$(V) scripts/stage_e_ltr.py $(if $(wildcard mini_study/coding_gold_v2.csv),--gold mini_study/coding_gold_v2.csv,)

modalities:     ## semantic ∪ hypergraph ∪ channel complementarity (Stage F)
	$(V) scripts/stage_f_modalities.py

# --- analytics layer --------------------------------------------------------- #
analytics-master: ## rebuild the canonical master dataset (21,710 × everything)
	$(V) analytics/build_master.py

analytics:      ## run all analysis modules → outputs/analytics/INDEX.md
	$(V) analytics/run_all.py

slice:          ## ad-hoc: make slice Q='--where in_pool --by country_combo'
	$(V) analytics/slice.py $(Q)
