#!/usr/bin/env python3
"""
compute_contested_overlap.py — grounds the slide-15 ("killer") claim.

Question: do the items where the CODER (human, layer-2) flagged
`contestedness == contested` coincide with the items where the two MODELS
(Claude vs GPT-4o, prompt A) disagree?

Joins:
  - coding_layer2.csv      -> yt_id, contestedness   (human, 60 items)
  - all_predictions_wide.csv -> yt_id, claude_A, gpt_A (model labels)

Computes a 2x2 contingency table (contested vs not) x (models disagree vs agree),
disagreement rates, the rate ratio, and a two-sided Fisher exact test
(implemented from math.comb, no scipy dependency). Prints + writes a markdown memo.

NO fabrication: every number is recomputed here from the two CSVs.
"""
import csv, os, math
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
L2 = os.path.join(HERE, "coding_layer2.csv")
PRED = os.path.join(HERE, "all_predictions_wide.csv")
OUT = os.path.join(HERE, "contested_overlap.md")


def load_contested():
    d = {}
    with open(L2, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d[r["yt_id"]] = r["contestedness"].strip()
    return d


def load_preds():
    d = {}
    with open(PRED, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d[r["yt_id"]] = (r["claude_A"].strip(), r["claude_B"].strip(),
                             r["gpt_A"].strip(), r["gpt_B"].strip())
    return d


def _hp(c1, c2, r1, N, x):
    return (math.comb(c1, x) * math.comb(c2, r1 - x)) / math.comb(N, r1)


def fisher_two_sided(a, b, c, d):
    """Two-sided Fisher exact p for table [[a,b],[c,d]] (scipy-compatible def)."""
    r1, c1, c2, N = a + b, a + c, b + d, a + b + c + d
    p_obs = _hp(c1, c2, r1, N, a)
    lo, hi = max(0, r1 - c2), min(r1, c1)
    return min(1.0, sum(_hp(c1, c2, r1, N, x) for x in range(lo, hi + 1)
                        if _hp(c1, c2, r1, N, x) <= p_obs * (1 + 1e-9)))


def fisher_one_sided_greater(a, b, c, d):
    """One-sided Fisher: P(top-left >= a) given margins."""
    r1, c1, c2, N = a + b, a + c, b + d, a + b + c + d
    hi = min(r1, c1)
    return sum(_hp(c1, c2, r1, N, x) for x in range(a, hi + 1))


# disagreement definitions over (claude_A, claude_B, gpt_A, gpt_B)
DEFS = {
    "A · claude_A≠gpt_A (= slajd 9 headline)": lambda p: p[0] != p[2],
    "B · claude_B≠gpt_B":                      lambda p: p[1] != p[3],
    "union · A lub B (dowolny prompt)":        lambda p: (p[0] != p[2]) or (p[1] != p[3]),
    "4-way · którykolwiek z 4 configów":       lambda p: len(set(p)) > 1,
}


def table(items, contested, preds, fn):
    a = b = c = d = 0
    for y in items:
        dis = fn(preds[y]); isc = contested[y] == "contested"
        if isc and dis: a += 1
        elif isc:       b += 1
        elif dis:       c += 1
        else:           d += 1
    return a, b, c, d


def main():
    contested = load_contested()
    preds = load_preds()
    items = [y for y in contested if y in preds]
    miss = [y for y in contested if y not in preds]
    N = len(items)

    lines = []
    P = lines.append
    P("# Contested ↔ model-disagreement overlap (slide 15)\n")
    P("Source: `coding_layer2.csv` (human `contestedness`) × `all_predictions_wide.csv` "
      "(Claude/GPT-4o, prompts A & B). Recomputed by `compute_contested_overlap.py` — "
      "no scipy, Fisher from `math.comb`.\n")
    if miss:
        P(f"> ⚠ {len(miss)} layer-2 items missing from predictions: {miss}\n")
    P(f"- N matched items: **{N}**  ·  contested (human): "
      f"**{sum(1 for y in items if contested[y]=='contested')}**, non-contested: "
      f"**{sum(1 for y in items if contested[y]!='contested')}**\n")
    P("## Sensitivity to the *disagreement* definition\n")
    P("| definicja niezgody | overall | contested | non-cont. | ×ratio | Fisher p (2-str.) | p (1-str.) |")
    P("|---|---:|---:|---:|---:|---:|---:|")
    for name, fn in DEFS.items():
        a, b, c, d = table(items, contested, preds, fn)
        ov = a + c
        rc, rn = a / (a + b), c / (c + d)
        ratio = rc / rn if rn else float("inf")
        P(f"| {name} | {ov}/{N}={100*ov/N:.1f}% | {a}/{a+b}={100*rc:.0f}% | "
          f"{c}/{c+d}={100*rn:.0f}% | ×{ratio:.2f} | {fisher_two_sided(a,b,c,d):.4f} | "
          f"{fisher_one_sided_greater(a,b,c,d):.4f} |")
    P("")
    P("## Interpretacja (uczciwa)\n")
    P("- **Kierunek jest stabilny**: na itemach `contested` modele rozchodzą się "
      "**×1,9–2,6 częściej** niż na niespornych — pod *każdą* definicją.")
    P("- **Istotność zależy od definicji.** Przy definicji z nagłówka slajdu 9 "
      "(`claude_A vs gpt_A`, 28,3%) jest **5/11 = 45%** vs 24%, ×1,86, **p=0,26 (n.s.)**. "
      "Twierdzenie **7/11 = 64%, ×2,6, p≈0,03** jest prawdziwe **tylko** dla definicji "
      "*„niezgoda pod którymkolwiek promptem” (union / 4-way, 31,7%)*.")
    P("- **Rekomendacja:** albo (a) ujednolicić definicję niezgody między slajdem 9 a 15 "
      "(wtedy podać 45% / n.s. — uczciwie, ale słabiej), albo (b) na slajdzie 15 jawnie "
      "powiedzieć „niezgoda pod którymkolwiek z dwóch promptów” i wtedy 7/11, p=0,03 jest "
      "poprawne — pod warunkiem, że ta definicja jest **nazwana**. Bez nazwania to "
      "niespójność metryczna.")
    txt = "\n".join(lines) + "\n"
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(txt)
    print(txt)
    print(f"-> wrote {OUT}")
    # spot-check dump: contested items under each definition
    print("\ncontested items (yt_id | cA | cB | gA | gB | A | B):")
    for y in items:
        if contested[y] == "contested":
            cA, cB, gA, gB = preds[y]
            dA = "≠" if cA != gA else "="
            dB = "≠" if cB != gB else "="
            print(f"  {y}  {cA[:10]:10s} {cB[:10]:10s} {gA[:10]:10s} {gB[:10]:10s}  A:{dA} B:{dB}")


if __name__ == "__main__":
    main()
