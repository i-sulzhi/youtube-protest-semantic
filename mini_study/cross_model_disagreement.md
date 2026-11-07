# Cross-model & cross-prompt disagreement — Claude vs GPT-4o

Source: 4 annotator configs × 60 items = 240 predictions.

- **Claude** (agent mode): 2 prompt formulations (A=terse, B=CoT)
- **GPT-4o** (`gpt-4o-2024-08-06`, temp=0): same 2 prompt formulations, same codebook

This operationalises the Yang & Wang (2025) "Benchmark Illusion": two models with comparable benchmark accuracy can still disagree on a substantial share of items. We measure both cross-MODEL (Claude vs GPT, same prompt) and cross-PROMPT (within model) disagreement.

## Pairwise disagreement matrix (% items where the two configs differ)

| | claude_A | claude_B | gpt_A | gpt_B |
|---|---|---|---|---|
| **claude_A** | — | 11.7% | 28.3% | 26.7% |
| **claude_B** | 11.7% | — | 25.0% | 26.7% |
| **gpt_A** | 28.3% | 25.0% | — | 1.7% |
| **gpt_B** | 26.7% | 26.7% | 1.7% | — |

## Headline numbers

- **Cross-MODEL, prompt A** (Claude_A vs GPT_A): **17/60 = 28.3%**
- **Cross-MODEL, prompt B** (Claude_B vs GPT_B): **16/60 = 26.7%**
- Cross-PROMPT, Claude (A vs B): 7/60 = 11.7%
- Cross-PROMPT, GPT-4o (A vs B): 1/60 = 1.7%

## Four-way unanimity

- All 4 configs identical: **41/60 = 68.3%**
  - 1 distinct label(s) across 4 configs: 41 items (68.3%)
  - 2 distinct label(s) across 4 configs: 18 items (30.0%)
  - 3 distinct label(s) across 4 configs: 1 items (1.7%)

## Cross-model (prompt A) disagreement by anchor

- `BY-2020-protest`: 4/12 (33.3%)
- `RU-antiwar-2022`: 3/12 (25.0%)
- `RU-mobilisation-2022`: 3/12 (25.0%)
- `UA-current-protest`: 4/12 (33.3%)
- `general-protest-action`: 3/12 (25.0%)

## Label distribution per config

```
label     antywojenny  bialorusko-narodowy  neutralny-informacyjny  prokremlowski  prozachodni
config                                                                                        
claude_A           18                   10                      23              6            3
claude_B           21                   10                      17              9            3
gpt_A              25                   11                      18              4            2
gpt_B              24                   11                      19              4            2
```

## Cross-model label transitions (prompt A, mismatches only)

| Claude_A | GPT_A | n |
|---|---|---:|
| `neutralny-informacyjny` | `antywojenny` | 5 |
| `neutralny-informacyjny` | `bialorusko-narodowy` | 3 |
| `prokremlowski` | `neutralny-informacyjny` | 3 |
| `antywojenny` | `prokremlowski` | 2 |
| `bialorusko-narodowy` | `antywojenny` | 2 |
| `prokremlowski` | `antywojenny` | 1 |
| `prozachodni` | `antywojenny` | 1 |

## Interpretation for the talk

- Cross-model disagreement is the *model-choice researcher degree of freedom*: switching Claude→GPT changes the label on a measurable share of items even at temperature 0.
- Both models individually may achieve high agreement with humans (F1) and still disagree with **each other** — this is precisely the Benchmark Illusion. "Which model is right?" is a question for the researcher, not the model.
- Disagreement concentrates on specific category boundaries (see transitions table), which is where construct validity is weakest and where moderation / disinformation policy is most consequential.
