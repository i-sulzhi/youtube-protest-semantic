# Language vs framing — the talk's central empirical test

N = 2,045 protest-mentioning videos (e5-large embeddings, 8 KMeans senses).

All embeddings L2-normalised; cosine = dot product.

## (1) Within-group mean cosine similarity

| Grouping | Mean cosine |
|---|---:|
| overall (baseline) | 0.7941 |
| same language | 0.8150 |
| same country_combo | 0.8134 |
| same cluster (event/sense) | 0.8386 |

**Reading:** videos sharing a *cluster (event/sense)* are more similar (cos=0.8386) than videos sharing a *language* (cos=0.8150). → semantic space is organised more by **FRAMING/EVENT** than by the other axis on this metric.

## (2) Nearest-neighbour concordance

- Each video's single nearest neighbour shares its **language** in **82.5%** of cases.
- Each video's single nearest neighbour shares its **cluster (event/sense)** in **88.8%** of cases.
- → nearest-neighbour structure is dominated by **EVENT/FRAMING**.

## (3) Centroid cosine — headline pairs

Belarus-2020 coverage across **different languages**:
- C0 (DE) ↔ C3 (EN): **0.9451**
- C1 (RU) ↔ C3 (EN): **0.9318**
- C0 (DE) ↔ C1 (RU): **0.9373**

Russian-language clusters with **different framing/event**:
- C1 (Belarus-RU) ↔ C7 (RU-opposition): **0.9669**
- C1 (Belarus-RU) ↔ C5 (RU/UA-war): **0.9758**
- C5 (RU/UA-war) ↔ C7 (RU-opposition): **0.9825**

- Mean centroid cosine, **same event / different language**: **0.9381**
- Mean centroid cosine, **same language (RU) / different event**: **0.9751**

> **FINDING (qualifies the thesis):** on centroids, shared *language* (0.975) binds at least as tightly as shared *event* (0.938). This is a presentable, honest counter-result — the model partly organises by language, marking a boundary where validation matters.

## Full centroid cosine matrix

See `mini_study/centroid_cosine.csv` and `figures/fig3_cluster_map.png`.

```
                                C0 BY-2020 (DE)  C1 Belarus opp. (RU)  C2 Russia/Navalny (EN)  C3 BY-2020 (EN)  C4 War analysis (EN/US)  C5 RU/UA war commentary (RU)  C6 Belsat opp. (BE/RU)  C7 RU opposition/anti-war (RU)
C0 BY-2020 (DE)                           1.000                 0.937                   0.907            0.945                    0.938                         0.926                   0.916                           0.915
C1 Belarus opp. (RU)                      0.937                 1.000                   0.895            0.932                    0.939                         0.976                   0.978                           0.967
C2 Russia/Navalny (EN)                    0.907                 0.895                   1.000            0.933                    0.946                         0.907                   0.889                           0.927
C3 BY-2020 (EN)                           0.945                 0.932                   0.933            1.000                    0.944                         0.903                   0.920                           0.894
C4 War analysis (EN/US)                   0.938                 0.939                   0.946            0.944                    1.000                         0.963                   0.935                           0.943
C5 RU/UA war commentary (RU)              0.926                 0.976                   0.907            0.903                    0.963                         1.000                   0.962                           0.982
C6 Belsat opp. (BE/RU)                    0.916                 0.978                   0.889            0.920                    0.935                         0.962                   1.000                           0.951
C7 RU opposition/anti-war (RU)            0.915                 0.967                   0.927            0.894                    0.943                         0.982                   0.951                           1.000
```