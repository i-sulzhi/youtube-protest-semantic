#!/usr/bin/env python3
"""
build_layer2.py — drugi (jakościowy) slой kodowania nad coding_progress.json.

NIE liczy κ ani żadnych metryk. Bierze ręczne kodowanie (layer 1: label/confidence/notes)
i dokłada cztery osie wyprowadzone z TREŚCI komentarzy kodera (axial coding):

  1. evidence_base       — na czym opiera się etykieta: text|close|channel|context (multi, '|')
     + used_extratextual (bool)   — czy koder użył informacji spoza tekstu (model widzi tylko tekst)
     + video_available   (bool)   — czy materiał był dostępny do obejrzenia
     + text_underdetermined (bool)— czy z samego tytułu/opisu etykieta byłaby inna / nieokreślona
  2. protest_relevance   — direct|indirect|absent  (codebook to "protest framing", ale wiele itemów nie jest o proteście)
  3. codebook_fit        — fits|forced|missing  (+ shadow_label gdy forced/missing)
  4. contestedness       — explicit|inferred|contested

  (+ opcjonalna 5. oś)  visual_footage — present|talking_head|none|unknown  (most do filaru wideo)

Wartości w SECOND_LAYER są kodowane ręcznie przez dr Sulzhytski (re-reading 60 notatek),
nie generowane heurystyką. Skrypt jedynie składa CSV i drukuje tally opisowe.
"""
import csv, json, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
# coding_progress.json leży w AGH_project/ oraz ~/Downloads/ (identyczne); preferuj AGH_project
CANDIDATES = [
    os.path.expanduser("~/Documents/claude_projects/AGH_project/coding_progress.json"),
    os.path.expanduser("~/Downloads/coding_progress.json"),
]
SRC = next((p for p in CANDIDATES if os.path.exists(p)), None)
if not SRC:
    sys.exit("coding_progress.json not found in AGH_project/ or ~/Downloads/")

# ---------------------------------------------------------------------------
# DRUGI SLOJ — ręczne kodowanie (yt_id -> dict). Kolejność jak w coding_progress.json.
# evidence: lista z {text, close, channel, context}
# protest:  direct | indirect | absent
# fit:      fits | forced | missing      shadow: '' chyba że forced/missing
# contest:  explicit | inferred | contested
# visual:   present | talking_head | none | unknown
# uX = used_extratextual, va = video_available, tu = text_underdetermined
# ---------------------------------------------------------------------------
SECOND_LAYER = {
 "AO2muYJEcrc": dict(evidence=["close","text"], uX=True, va=True, tu=True,
    protest="absent", fit="forced", shadow="ukr. nacjonalistyczny antywojenny; prokremlowość 'otwarta'",
    contest="contested", visual="unknown"),
 "YDCGx_ySDyg": dict(evidence=["close","text"], uX=True, va=True, tu=False,
    protest="absent", fit="forced", shadow="anti-russian pro-ukrainian (wojna), nie 'neutralny'",
    contest="explicit", visual="unknown"),
 "-oGmAM4AMjk": dict(evidence=["close","channel","text"], uX=True, va=True, tu=True,
    protest="absent", fit="forced", shadow="prawdopodobnie prokremlowski (strana.ua), podany jako ukr. opinia",
    contest="contested", visual="talking_head"),
 "kMLlqrEPzdg": dict(evidence=["channel","context","text"], uX=True, va=False, tu=False,
    protest="indirect", fit="fits", shadow="",
    contest="inferred", visual="unknown"),
 "gmBPdjUjK_Q": dict(evidence=["close","channel","text"], uX=True, va=True, tu=True,
    protest="absent", fit="forced", shadow="proukr. krytyka władzy (z tekstu klasyfikator dałby 'neutralny')",
    contest="explicit", visual="talking_head"),
 "gAhXLx34C8k": dict(evidence=["text","context"], uX=True, va=False, tu=False,
    protest="direct", fit="forced", shadow="antyrządowy митинг w UA; prokremlowość tylko potencjalna, deklaratywnie za ZSU",
    contest="contested", visual="unknown"),
 "0OfbJpTSgfo": dict(evidence=["close","text"], uX=True, va=True, tu=False,
    protest="absent", fit="forced", shadow="anty-kremlowski proukraiński (rozmowa z czat-ruletki)",
    contest="explicit", visual="talking_head"),
 "S61lTIzrtpc": dict(evidence=["close","channel","text"], uX=True, va=True, tu=False,
    protest="indirect", fit="forced", shadow="prokremlowski antymobilizacyjny (strana.ua, 'bandera-wioska')",
    contest="contested", visual="unknown"),
 "96sEU4VQ30g": dict(evidence=["text"], uX=False, va=False, tu=True,
    protest="absent", fit="fits", shadow="",
    contest="inferred", visual="unknown"),
 "nwcaLjqh4h8": dict(evidence=["close","text"], uX=True, va=True, tu=False,
    protest="absent", fit="fits", shadow="",
    contest="explicit", visual="talking_head"),
 "4FTjaUg7VDw": dict(evidence=["close","text"], uX=True, va=True, tu=False,
    protest="absent", fit="forced", shadow="proukraiński (ludzki wątek wojskowy)",
    contest="explicit", visual="talking_head"),
 "Viop-_Egtuc": dict(evidence=["text"], uX=False, va=False, tu=True,
    protest="absent", fit="fits", shadow="",
    contest="inferred", visual="unknown"),
 "9lnbuRtwEeU": dict(evidence=["channel","text"], uX=True, va=False, tu=True,
    protest="absent", fit="fits", shadow="",
    contest="inferred", visual="unknown"),
 "oct6C5KnRXQ": dict(evidence=["text","context"], uX=True, va=False, tu=False,
    protest="indirect", fit="fits", shadow="",
    contest="inferred", visual="unknown"),
 "0JEQNwa9VB0": dict(evidence=["text"], uX=False, va=True, tu=False,
    protest="direct", fit="fits", shadow="",
    contest="explicit", visual="talking_head"),
 "xCR4IUEfJpM": dict(evidence=["text"], uX=False, va=False, tu=False,
    protest="absent", fit="fits", shadow="",
    contest="explicit", visual="unknown"),
 "eAQa34wo76M": dict(evidence=["close","text"], uX=True, va=True, tu=False,
    protest="direct", fit="fits", shadow="",
    contest="explicit", visual="talking_head"),
 "KlhPQBlQ2g8": dict(evidence=["close","text","context"], uX=True, va=True, tu=False,
    protest="indirect", fit="fits", shadow="",
    contest="explicit", visual="present"),
 "gc21Qkfoqtg": dict(evidence=["close","context","text"], uX=True, va=True, tu=False,
    protest="absent", fit="fits", shadow="",
    contest="explicit", visual="unknown"),
 "iKfTygMMCkU": dict(evidence=["close","text"], uX=True, va=True, tu=True,
    protest="indirect", fit="fits", shadow="",
    contest="explicit", visual="unknown"),
 "85dJ-1Y5DLQ": dict(evidence=["text","context"], uX=True, va=True, tu=True,
    protest="indirect", fit="forced", shadow="kryzys migracyjny jako następstwo protestów; dyskurs narodowy domniemany",
    contest="inferred", visual="unknown"),
 "rfvW28axDaw": dict(evidence=["close","text"], uX=True, va=True, tu=False,
    protest="direct", fit="fits", shadow="",
    contest="explicit", visual="talking_head"),
 "1Wh-WPvWclE": dict(evidence=["close","text","context"], uX=True, va=True, tu=True,
    protest="absent", fit="forced", shadow="rosyjscy blogerzy, pozycja ambiwalentna ('między' obozami)",
    contest="contested", visual="unknown"),
 "Top9J3IiWZE": dict(evidence=["text","context"], uX=True, va=False, tu=False,
    protest="indirect", fit="fits", shadow="",
    contest="inferred", visual="unknown"),
 "jybxN0COXzk": dict(evidence=["text"], uX=False, va=False, tu=True,
    protest="indirect", fit="fits", shadow="",
    contest="inferred", visual="unknown"),
 "qp0_9UWDntQ": dict(evidence=["close","context","text"], uX=True, va=True, tu=False,
    protest="absent", fit="fits", shadow="",
    contest="explicit", visual="none"),
 "2RF8r8Q3iEo": dict(evidence=["text"], uX=False, va=False, tu=False,
    protest="direct", fit="fits", shadow="",
    contest="explicit", visual="unknown"),
 "WahG0Lgk_MM": dict(evidence=["close","text"], uX=True, va=True, tu=False,
    protest="indirect", fit="forced", shadow="proukraiński satyryczny",
    contest="contested", visual="talking_head"),
 "z4z57zGabP4": dict(evidence=["close","channel","text"], uX=True, va=True, tu=False,
    protest="direct", fit="fits", shadow="",
    contest="explicit", visual="present"),
 "MdUyiofx2i4": dict(evidence=["close","channel","context"], uX=True, va=True, tu=False,
    protest="indirect", fit="forced", shadow="BN + prozachodni (obramowanie DW), podwójny dyskurs",
    contest="contested", visual="present"),
 "IYVHA8p-IaY": dict(evidence=["channel","text"], uX=True, va=False, tu=False,
    protest="indirect", fit="missing", shadow="pro-łukaszenkowskie / prorządowe (ONT) — BRAK kategorii, wciśnięte w prokremlowski",
    contest="explicit", visual="unknown"),
 "4tR301yEKXI": dict(evidence=["close","text"], uX=True, va=True, tu=False,
    protest="absent", fit="fits", shadow="",
    contest="explicit", visual="talking_head"),
 "1iuqfpdQDRw": dict(evidence=["close","channel","text"], uX=True, va=True, tu=False,
    protest="absent", fit="fits", shadow="",
    contest="explicit", visual="talking_head"),
 "v4J1Wjwvs3w": dict(evidence=["close","text"], uX=True, va=True, tu=False,
    protest="indirect", fit="forced", shadow="ukr. satyra solidarnościowa (nie do końca BN, 'autonomiczny przekrój')",
    contest="contested", visual="talking_head"),
 "QJrNdplYsko": dict(evidence=["close","channel","text"], uX=True, va=True, tu=False,
    protest="direct", fit="fits", shadow="",
    contest="explicit", visual="present"),
 "DlADE0A_Rdw": dict(evidence=["close","channel","context"], uX=True, va=True, tu=False,
    protest="direct", fit="forced", shadow="kanał BN (strana dlja żyzni) relacjonuje antywojenny protest w Baszkortostanie (RF)",
    contest="explicit", visual="present"),
 "wjKxTeRtgYA": dict(evidence=["text"], uX=False, va=True, tu=True,
    protest="absent", fit="forced", shadow="prorządowe (domniemane, jedyny marker = emoji czerwono-zielonej flagi)",
    contest="inferred", visual="unknown"),
 "Yn8SHRtsZrE": dict(evidence=["close","text"], uX=True, va=True, tu=False,
    protest="absent", fit="forced", shadow="prorządowa propaganda (podana jako news)",
    contest="explicit", visual="unknown"),
 "JN6HJdNlzhw": dict(evidence=["close","channel","text"], uX=True, va=True, tu=False,
    protest="direct", fit="forced", shadow="proukr. UNIAN o protestach socjalnych w RF (ogrzewanie, nie wojna)",
    contest="inferred", visual="present"),
 "ZgVTraqYS-s": dict(evidence=["text","context"], uX=True, va=False, tu=True,
    protest="absent", fit="forced", shadow="prozachodni domniemany (ICC/ang.)",
    contest="inferred", visual="unknown"),
 "u0p579BYKdU": dict(evidence=["close","channel","text"], uX=True, va=True, tu=False,
    protest="indirect", fit="forced", shadow="proukr. antykremlowski (Cymbaluk); 'gadająca głowa', protest niepokazany",
    contest="explicit", visual="talking_head"),
 "oAY7OeR7zO4": dict(evidence=["close","channel","text"], uX=True, va=True, tu=False,
    protest="direct", fit="fits", shadow="",
    contest="explicit", visual="present"),
 "a-QON3Iv8Is": dict(evidence=["close","text"], uX=True, va=True, tu=False,
    protest="absent", fit="forced", shadow="ukr. antykremlowski sarkazm (treść = przemówienie Putina)",
    contest="explicit", visual="none"),
 "WOAISsyCT5E": dict(evidence=["close","channel","text"], uX=True, va=True, tu=True,
    protest="absent", fit="forced", shadow="'za pokojem RU-UA' — ambiwalentne, flagi pod muzykę",
    contest="contested", visual="none"),
 "i83B2D50RPg": dict(evidence=["close","text"], uX=True, va=True, tu=False,
    protest="direct", fit="forced", shadow="multirama: antywojenny + ros. opozycja + zachodni frejm (koder wymienia 4)",
    contest="contested", visual="present"),
 "1d0eSMlD3hw": dict(evidence=["close","text"], uX=True, va=True, tu=False,
    protest="direct", fit="fits", shadow="",
    contest="explicit", visual="present"),
 "2YhbQXARVTI": dict(evidence=["close","channel","text"], uX=True, va=True, tu=True,
    protest="absent", fit="forced", shadow="proukr./antyros. (po kanale ZupyniLosia); treść = przemówienie Putina",
    contest="inferred", visual="none"),
 "i3OXLpbbgsM": dict(evidence=["close","text"], uX=True, va=True, tu=False,
    protest="direct", fit="fits", shadow="",
    contest="explicit", visual="present"),
 "sSSwdgIRAxk": dict(evidence=["text","context"], uX=True, va=False, tu=False,
    protest="direct", fit="forced", shadow="antywojenny + zachodni adresat + meta o framingu prokremlowskich mediów",
    contest="contested", visual="unknown"),
 "8pHGCGEhOqs": dict(evidence=["close","channel","text"], uX=True, va=True, tu=False,
    protest="direct", fit="forced", shadow="proukr. UNIAN o antymobilizacyjnym proteście w RF",
    contest="explicit", visual="present"),
 "IOB0eHIT7Nw": dict(evidence=["text"], uX=False, va=False, tu=True,
    protest="absent", fit="fits", shadow="",
    contest="inferred", visual="unknown"),
 "R1-7q8xEk0A": dict(evidence=["close","channel","context"], uX=True, va=True, tu=False,
    protest="indirect", fit="missing", shadow="rosyjski nacjonalizm (imperialny, anty-Łukaszenko ale antyzachodni) — BRAK kategorii, wciśnięte w neutralny",
    contest="explicit", visual="talking_head"),
 "3q8R8z4r1rA": dict(evidence=["close","channel","text"], uX=True, va=True, tu=False,
    protest="direct", fit="forced", shadow="proukr. propaganda o antymobilizacyjnym proteście w RF",
    contest="explicit", visual="present"),
 "2Bdbil_YnDQ": dict(evidence=["close","text"], uX=True, va=True, tu=False,
    protest="indirect", fit="fits", shadow="",
    contest="inferred", visual="unknown"),
 "53QcuExOgEI": dict(evidence=["close","context","text"], uX=True, va=True, tu=True,
    protest="direct", fit="fits", shadow="",
    contest="inferred", visual="present"),
 "c-N6tUhCbWQ": dict(evidence=["close","text"], uX=True, va=True, tu=False,
    protest="absent", fit="forced", shadow="proukr./antyros. (wątek wojskowy, nie protest)",
    contest="explicit", visual="none"),
 "-frGI47B_LM": dict(evidence=["text","context"], uX=True, va=False, tu=True,
    protest="indirect", fit="fits", shadow="",
    contest="inferred", visual="unknown"),
 "xyIcmgqybUw": dict(evidence=["text","context"], uX=True, va=False, tu=True,
    protest="indirect", fit="fits", shadow="",
    contest="inferred", visual="unknown"),
 "N_C2TMRzw9o": dict(evidence=["close","channel","text"], uX=True, va=True, tu=False,
    protest="direct", fit="forced", shadow="proukr. media o antywojennym proteście w RF (Baszkortostan)",
    contest="explicit", visual="present"),
 "ePY-_nBlGuw": dict(evidence=["text","context"], uX=True, va=False, tu=True,
    protest="absent", fit="forced", shadow="proukr. antykremlowski (mobilizacja)",
    contest="inferred", visual="unknown"),
}


def excerpt(s, n=140):
    s = " ".join(s.split())
    return s[:n] + ("…" if len(s) > n else "")


def main():
    layer1 = json.load(open(SRC, encoding="utf-8"))["data"]
    missing = set(layer1) - set(SECOND_LAYER)
    extra = set(SECOND_LAYER) - set(layer1)
    assert not missing, f"layer-2 brakuje itemów: {missing}"
    assert not extra, f"layer-2 ma nadmiarowe itemy: {extra}"

    out = os.path.join(HERE, "coding_layer2.csv")
    cols = ["yt_id", "primary_label", "confidence", "evidence_base",
            "used_extratextual", "video_available", "text_underdetermined",
            "protest_relevance", "codebook_fit", "shadow_label",
            "contestedness", "visual_footage", "note_excerpt"]
    rows = []
    for yt, l1 in layer1.items():
        s = SECOND_LAYER[yt]
        rows.append({
            "yt_id": yt,
            "primary_label": l1.get("label", ""),
            "confidence": l1.get("confidence", ""),
            "evidence_base": "|".join(s["evidence"]),
            "used_extratextual": str(s["uX"]).lower(),
            "video_available": str(s["va"]).lower(),
            "text_underdetermined": str(s["tu"]).lower(),
            "protest_relevance": s["protest"],
            "codebook_fit": s["fit"],
            "shadow_label": s["shadow"],
            "contestedness": s["contest"],
            "visual_footage": s["visual"],
            "note_excerpt": excerpt(l1.get("notes", "")),
        })
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    # ---- tally OPISOWE (nie metryki) ----
    n = len(rows)
    print(f"napisano {out}  ({n} wierszy)\n")
    def tally(key):
        return Counter(r[key] for r in rows)
    print("protest_relevance:", dict(tally("protest_relevance")))
    print("codebook_fit:     ", dict(tally("codebook_fit")))
    print("contestedness:    ", dict(tally("contestedness")))
    print("used_extratextual:", dict(tally("used_extratextual")))
    print("video_available:  ", dict(tally("video_available")))
    print("text_underdeterm.:", dict(tally("text_underdetermined")))
    print("visual_footage:   ", dict(tally("visual_footage")))
    ev = Counter()
    for r in rows:
        for e in r["evidence_base"].split("|"):
            ev[e] += 1
    print("evidence_base(any):", dict(ev))
    print(f"\nshadow_label wypełniony: {sum(1 for r in rows if r['shadow_label'])} / {n}")
    # przekrój: gdzie etykieta opiera się na info spoza tekstu
    nx = sum(1 for r in rows if r["used_extratextual"] == "true")
    print(f"used_extratextual=true: {nx}/{n} ({100*nx/n:.0f}%)  -> model widzi tylko tekst")
    nu = sum(1 for r in rows if r["text_underdetermined"] == "true")
    print(f"text_underdetermined=true: {nu}/{n} ({100*nu/n:.0f}%)")
    na = sum(1 for r in rows if r["protest_relevance"] != "direct")
    print(f"NIE 'direct' protest: {na}/{n} ({100*na/n:.0f}%)")


if __name__ == "__main__":
    main()
