# mini_study — walidacja LLM-anotacji ram (AGH talk)

Mini-study dla wystąpienia «Czy można ufać AI w badaniach społecznych?». Testuje, czy modele językowe (Claude, GPT-4o) klasyfikują *ramę polityczną* wielojęzycznych filmów YouTube wystarczająco wiarygodnie, by im ufać — przez porównanie z kodowaniem ludzkim (κ, F1) i między modelami (Benchmark Illusion).

Wszystko odtwarzalne. Środowisko: `protest_tags/.venv_v2` (sentence-transformers 5.4.1, lancedb 0.30.2, openai 2.38, scikit-learn 1.8, scipy 1.17).

---

## Pipeline (kolejność uruchamiania)

```
# 0. (raz) regeneracja danych z MariaDB
python scripts/regen_feed_ready.py                  # → outputs/v2_feed_ready.csv.gz (21 710)
python pipeline/stage_a_embed.py --model intfloat/multilingual-e5-large --batch 8 --table videos_e5large
python pipeline/stage_b_retrieve.py --table videos_e5large --model intfloat/multilingual-e5-large --out-dir outputs/retrieval_e5large
python pipeline/stage_c_polysemy.py --table videos_e5large --out-dir outputs/polysemy_e5large

# 1. próbka + kodbook
python mini_study/build_sample.py                   # → sample.csv (200 stratified)
python mini_study/build_human_coding_sheet.py       # → coding_sheet_for_human.csv (60)
#   framing_codebook.md — kodbook 5 ram (ręcznie)

# 2. klasyfikacja LLM
python mini_study/build_classification_briefings.py # → llm_input/ (4 briefings)
#   → 4 Claude sub-agenty piszą llm_predictions/claude_prompt{A,B}_chunk{1,2}.jsonl
python mini_study/build_briefings_complement.py     # → briefings na pozostałe 140
#   → 4 Claude sub-agenty piszą claude_promptA_extra{1..4}.jsonl
OPENAI_API_KEY=... python mini_study/classify_with_gpt.py                          # 60×2 prompty
OPENAI_API_KEY=... python mini_study/classify_with_gpt.py --input sample.csv --prompts A --suffix _full200

# 3. agregacja + metryki
python mini_study/aggregate_predictions.py          # cross-prompt (Claude)
python mini_study/aggregate_all.py                  # cross-model (Claude+GPT, 60) → 28,3%
python mini_study/cross_model_200.py                # cross-model (200) → 25,0%
python mini_study/language_vs_framing.py            # centroidy: język vs rama
python mini_study/chi2_language_framing.py          # χ² (V=0,20)

# 4. PO ręcznym kodowaniu:
#   coding_ui.html → Export CSV → coding_sheet_for_human_FILLED.csv
python mini_study/compute_metrics.py                # κ, α, F1, confusion → validation_metrics.md + fig4

# 5. figury
python figures/make_fig0_timeline.py    # slajd 3
python figures/make_fig1_maturity_axis.py  # slajd 5
python figures/make_fig2_recall_gain.py    # slajd 7
python figures/make_fig3_cluster_map.py    # slajd 8
python figures/make_fig5_disagreement.py   # slajd 10
python figures/make_fig6_formulas.py       # backup B3
#   fig4_kappa.png — z compute_metrics.py
```

---

## Wyniki (zweryfikowane 2026-05-28)

| Pytanie | Wynik | Plik |
|---|---|---|
| Recall semantyczny vs słowa kluczowe | +60% (2-way) / +116% (4-way) | `../docs/RESULTS_LOG.md` |
| Czystość klastrów (8 sensów) | 36–89%, śr. ~60% | `../outputs/polysemy_e5large/` |
| Język czy rama (lokalnie) | rama: NN 88,8% vs 82,5% | `language_vs_framing.md` |
| Język czy rama (makro) | język: RU centroidy 0,97 vs 0,94 | `centroid_cosine.csv` |
| χ² rama × język | V = 0,20 (słaba zależność) | `chi2_language_framing.md` |
| Cross-prompt (Claude) | 11,7% | `cross_prompt_disagreement.md` |
| Cross-prompt (GPT-4o) | 1,7% | `cross_model_disagreement.md` |
| **Cross-model (60)** | **28,3%** | `cross_model_disagreement.md` |
| **Cross-model (200)** | **25,0%** | `cross_model_200.md` |
| Jednomyślność 4 konfiguracji | 68,3% | `cross_model_disagreement.md` |
| Bias modeli | GPT→antywojenny (+12), Claude→neutral | `cross_model_200.md` |
| κ człowiek × LLM | **czeka na kodowanie ręczne** | `validation_metrics.md` |

---

## Uwagi metodologiczne

- **Claude = tryb agentowy**, nie API. 8 niezależnych instancji Claude (sub-agenty) z ograniczeniem narzędzi do Read/Write. Metodologicznie równoważne wywołaniom API.
- **GPT-4o** = `gpt-4o-2024-08-06`, temp=0, `response_format=json_object`. Klucz tylko przez env, nigdy do pliku. Raw responses w `llm_predictions/raw/`.
- **Próba**: 200 stratyfikowanych (anchor × język) z 5 kotwic protestowych. 60 z nich = arkusz kodowania ręcznego.
- **Klasy**: prokremlowski / antywojenny / prozachodni / bialorusko-narodowy / neutralny-informacyjny (ASCII).
- **Bias korpusu** (uczciwie): białorusko-centryczny (63% odkryć), Rosja spróbkowana z 1 dnia. Klasa `prokremlowski` rzadka (~5%) — korpus opozycyjny.

## Bezpieczeństwo
Klucz OpenAI nie jest zapisany w żadnym pliku repo (sprawdzone `grep -r sk-proj`). Po użyciu **rotować klucz**.
