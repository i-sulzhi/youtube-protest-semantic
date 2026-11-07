# Validation metrics — human × LLM

Human source: **coding_sheet_for_human_FILLED.csv**  |  N = 60 coded items

## Cohen's κ — human vs each LLM config

| Config | Cohen's κ | Accuracy |
|---|---:|---:|
| claude_A | 0.569 | 0.683 |
| claude_B | 0.554 | 0.667 |
| gpt_A | 0.405 | 0.567 |
| gpt_B | 0.428 | 0.583 |

## Krippendorff's α (nominal)

- Across {human_label, claude_A, gpt_A}: **α = 0.528**

## Per-class precision / recall / F1 — claude_A (human = gold)

| Class | precision | recall | F1 | support |
|---|---:|---:|---:|---:|
| prokremlowski | 0.67 | 0.57 | 0.62 | 7 |
| antywojenny | 0.67 | 0.67 | 0.67 | 18 |
| prozachodni | 1.00 | 1.00 | 1.00 | 3 |
| bialorusko-narodowy | 0.80 | 0.67 | 0.73 | 12 |
| neutralny-informacyjny | 0.61 | 0.70 | 0.65 | 20 |
| **macro avg** | 0.75 | 0.72 | 0.73 | 60 |
| **weighted avg** | 0.69 | 0.68 | 0.68 | 60 |

## Per-class precision / recall / F1 — gpt_A (human = gold)

| Class | precision | recall | F1 | support |
|---|---:|---:|---:|---:|
| prokremlowski | 0.25 | 0.14 | 0.18 | 7 |
| antywojenny | 0.56 | 0.78 | 0.65 | 18 |
| prozachodni | 1.00 | 0.67 | 0.80 | 3 |
| bialorusko-narodowy | 0.64 | 0.58 | 0.61 | 12 |
| neutralny-informacyjny | 0.56 | 0.50 | 0.53 | 20 |
| **macro avg** | 0.60 | 0.53 | 0.55 | 60 |
| **weighted avg** | 0.56 | 0.57 | 0.55 | 60 |

## Confusion matrices

See `figures/fig4_kappa.png`.
