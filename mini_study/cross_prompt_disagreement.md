# Cross-prompt disagreement — Claude-as-annotator pass

Source: 4 sub-agent runs (120 total predictions, 60 unique items)

This is the **prompt-stability** check that proxies the Yang & Wang 2025 "Benchmark Illusion" finding for a single-model setting. A high disagreement rate between Prompt A (terse/structured) and Prompt B (CoT/discursive) is itself a researcher-degree-of-freedom signal.


## Overall agreement

- Items where Prompt A == Prompt B: **53 / 60 (88.3%)**
- Disagreement rate: **11.7%**

## Disagreement by anchor

- `BY-2020-protest`: 1/12 disagree (8.3%)
- `RU-antiwar-2022`: 0/12 disagree (0.0%)
- `RU-mobilisation-2022`: 2/12 disagree (16.7%)
- `UA-current-protest`: 3/12 disagree (25.0%)
- `general-protest-action`: 1/12 disagree (8.3%)

## Label transitions A → B (mismatches only)

| Prompt A | Prompt B | n |
|---|---|---:|
| `neutralny-informacyjny` | `antywojenny` | 4 |
| `neutralny-informacyjny` | `prokremlowski` | 2 |
| `antywojenny` | `prokremlowski` | 1 |

## Mean confidence on matched vs mismatched items

- Prompt A: matched=2.04, mismatched=1.43
- Prompt B: matched=1.92, mismatched=1.71

If mismatched items consistently have lower confidence than matched items, the model has *some* awareness of its own uncertainty — useful for confidence-gated human review (cf. Gligorić et al. 2024 PPI extension to unconfident LLM labels).

## Label distribution per prompt

```
label   antywojenny  bialorusko-narodowy  neutralny-informacyjny  prokremlowski  prozachodni
prompt                                                                                      
A                18                   10                      23              6            3
B                21                   10                      17              9            3
```
