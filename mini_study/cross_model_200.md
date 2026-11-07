# Cross-model disagreement — FULL 200-item sample (Claude vs GPT-4o, prompt A)

N = 200 items with both labels.

## Headline

- **Cross-model disagreement (N=200): 50/200 = 25.0%**
- Agreement: 150/200 = 75.0%

> Confirms the 60-item finding (28.3%) on the full sample — robust, not a small-N artefact.

## By anchor

- `BY-2020-protest`: 17/35 (48.6%)
- `RU-antiwar-2022`: 5/30 (16.7%)
- `RU-mobilisation-2022`: 6/32 (18.8%)
- `UA-current-protest`: 13/55 (23.6%)
- `general-protest-action`: 9/48 (18.8%)

## By language

- en: 3/14 (21.4%)
- other: 1/5 (20.0%)
- ru: 26/107 (24.3%)
- uk: 7/20 (35.0%)
- unset: 13/53 (24.5%)

## Label transitions (Claude → GPT, mismatches only)

| Claude | GPT | n |
|---|---|---:|
| `neutralny-informacyjny` | `antywojenny` | 14 |
| `bialorusko-narodowy` | `antywojenny` | 7 |
| `antywojenny` | `neutralny-informacyjny` | 6 |
| `prokremlowski` | `neutralny-informacyjny` | 5 |
| `bialorusko-narodowy` | `neutralny-informacyjny` | 4 |
| `neutralny-informacyjny` | `bialorusko-narodowy` | 4 |
| `antywojenny` | `bialorusko-narodowy` | 2 |
| `antywojenny` | `prokremlowski` | 2 |
| `antywojenny` | `prozachodni` | 2 |
| `prozachodni` | `antywojenny` | 2 |
| `neutralny-informacyjny` | `prokremlowski` | 1 |
| `prokremlowski` | `antywojenny` | 1 |

## Label distribution

```
                        claude  gpt
antywojenny                 73   85
bialorusko-narodowy         27   22
neutralny-informacyjny      83   79
prokremlowski               12    9
prozachodni                  5    5
```