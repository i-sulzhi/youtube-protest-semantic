# χ² test — is framing independent of language? (N=200 sample, GPT-4o labels)

Items: 200  |  GPT-4o prompt A framing labels on the full stratified sample.

## Cross-tabulation: language × framing

```
framing        prokremlowski  antywojenny  prozachodni  bialorusko-narodowy  neutralny-informacyjny
language_norm                                                                                      
en                         1            4            2                    3                       4
other                      0            2            0                    1                       2
ru                         3           57            2                    9                      36
uk                         1           11            1                    1                       6
unset                      4           11            0                    7                      31
```

## χ² test of independence

- χ²(16) = **32.2**, p = **9.35e-03**
- Cramér's V = **0.201**  (0=independent, 1=perfect dependence)

> Framing and language are **statistically dependent** (p<0.05), but the association is **moderate** (V=0.201). 
> A moderate V means framing is **not reducible to language** — the same framing category appears across multiple languages, and each language hosts multiple framings. This supports the talk's thesis that **framing cross-cuts language**.

## Framing entropy (bits) — how mixed is each language's framing?

- Overall framing entropy: 1.74 bits (max for 5 classes = 2.32)

| Language | n | framing entropy |
|---|---:|---:|
| en | 14 | 2.18 |
| other | 5 | 1.52 |
| ru | 107 | 1.57 |
| uk | 20 | 1.64 |
| unset | 53 | 1.59 |

> High per-language entropy = that language hosts many framings (framing not determined by language). Low entropy = that language is dominated by one framing.

## Framing distribution by language (row %)

```
framing        prokremlowski  antywojenny  prozachodni  bialorusko-narodowy  neutralny-informacyjny
language_norm                                                                                      
en                       7.1         28.6         14.3                 21.4                    28.6
other                    0.0         40.0          0.0                 20.0                    40.0
ru                       2.8         53.3          1.9                  8.4                    33.6
uk                       5.0         55.0          5.0                  5.0                    30.0
unset                    7.5         20.8          0.0                 13.2                    58.5
```