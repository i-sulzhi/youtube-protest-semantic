# Contested ↔ model-disagreement overlap (slide 15)

Source: `coding_layer2.csv` (human `contestedness`) × `all_predictions_wide.csv` (Claude/GPT-4o, prompts A & B). Recomputed by `compute_contested_overlap.py` — no scipy, Fisher from `math.comb`.

- N matched items: **60**  ·  contested (human): **11**, non-contested: **49**

## Sensitivity to the *disagreement* definition

| definicja niezgody | overall | contested | non-cont. | ×ratio | Fisher p (2-str.) | p (1-str.) |
|---|---:|---:|---:|---:|---:|---:|
| A · claude_A≠gpt_A (= slajd 9 headline) | 17/60=28.3% | 5/11=45% | 12/49=24% | ×1.86 | 0.2647 | 0.1528 |
| B · claude_B≠gpt_B | 16/60=26.7% | 6/11=55% | 10/49=20% | ×2.67 | 0.0528 | 0.0304 |
| union · A lub B (dowolny prompt) | 19/60=31.7% | 7/11=64% | 12/49=24% | ×2.60 | 0.0267 | 0.0175 |
| 4-way · którykolwiek z 4 configów | 19/60=31.7% | 7/11=64% | 12/49=24% | ×2.60 | 0.0267 | 0.0175 |

## Interpretacja (uczciwa)

- **Kierunek jest stabilny**: na itemach `contested` modele rozchodzą się **×1,9–2,6 częściej** niż na niespornych — pod *każdą* definicją.
- **Istotność zależy od definicji.** Przy definicji z nagłówka slajdu 9 (`claude_A vs gpt_A`, 28,3%) jest **5/11 = 45%** vs 24%, ×1,86, **p=0,26 (n.s.)**. Twierdzenie **7/11 = 64%, ×2,6, p≈0,03** jest prawdziwe **tylko** dla definicji *„niezgoda pod którymkolwiek promptem” (union / 4-way, 31,7%)*.
- **Rekomendacja:** albo (a) ujednolicić definicję niezgody między slajdem 9 a 15 (wtedy podać 45% / n.s. — uczciwie, ale słabiej), albo (b) na slajdzie 15 jawnie powiedzieć „niezgoda pod którymkolwiek z dwóch promptów” i wtedy 7/11, p=0,03 jest poprawne — pod warunkiem, że ta definicja jest **nazwana**. Bez nazwania to niespójność metryczna.
