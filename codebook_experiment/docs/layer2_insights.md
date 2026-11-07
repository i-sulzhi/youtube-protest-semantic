# Layer-2 insights — "tu jest więcej niż agreement"

Data: 2026-05-29. Źródło: `coding_layer2.csv` (60 itemów, drugi slój kodowania nad `coding_progress.json`).
**Uwaga:** to są tally **opisowe**, NIE metryki (κ/α nie liczone — osobny, odłożony krok).

---

## 1. Liczby (z `build_layer2.py`)

| Oś | Rozkład | Co mówi |
|---|---|---|
| **protest_relevance** | direct **18** · indirect **17** · absent **25** | **42/60 (70%) NIE jest wprost o proteście.** Kodbook "protest framing", ale retrieval wyciągnął głównie wojnę/mobilizację. |
| **codebook_fit** | fits **29** · forced **29** · missing **2** | **31/60 (52%) wymaga shadow-label** — 5 kategorii nie utrzymuje połowy próby czysto. |
| **contestedness** | explicit **31** · inferred **18** · contested **11** | **29/60 (48%) nie jest w pełni jawne**; 11 to realny spór, który koder sam zaznaczył. |
| **used_extratextual** | **true 52** · false 8 | **87% etykiet opiera się na informacji spoza tekstu** (close/channel/context). Model widzi tylko tekst. |
| **text_underdetermined** | true **19** · false 41 | **32% itemów** — z samego tytułu/opisu etykieta byłaby inna/nieokreślona. |
| **video_available** | true 43 · **false 17** | **17/60 (28%) niedostępnych** → gold częściowo inferencyjny (data decay). |
| **visual_footage** | present 14 · talking_head 14 · none 5 · unknown 27 | wśród ustalonych: rama tekstowa ≠ treść wizualna. |
| **evidence_base (any)** | text 57 · close 40 · channel 20 · context 18 | kanał/kontekst napędzają 1/3 decyzji. |

---

## 2. Cztery wnioski (struktura niezgody, nie szum)

Komentarze pokazują, że niezgoda (człowiek↔model i model↔model) jest **strukturyzowana** przez cztery *poznawalne* czynniki — nie jest losowa:

**(1) Asymetria informacyjna — 87%.**
W 52/60 przypadków moja etykieta opiera się na tym, czego model nie widzi: obejrzeniu filmu, tożsamości kanału (strana.ua, Panczenko, ONT, UNIAN, Dożd), wiedzy o wydarzeniu. To **honest answer na pytanie "czemu κ nie jest wyższe"**: w 1/3 itemów (32%) sam tekst **niedookreśla** konstrukt — i potrafię wskazać *które to itemy*. Niski κ tu mierzy lukę informacyjną, nie niekompetencję modelu.

**(2) Temat ≠ postawa — 70% nie-direct.**
Tylko 30% próby jest wprost o proteście. Dla reszty pytanie "jaka rama protestu?" jest częściowo źle postawione — to treść wojenna/mobilizacyjna. To źródło **legalnej** niezgody: koder i model mogą rozsądnie różnić się, bo obiekt jest rozmyty. Wiąże się ze slajdami 7–8 (retrieval semantyczny wyciąga metonimię, ale i szum tematyczny).

**(3) Luki kodbooka — 52% forced, 2 missing.**
Połowa itemów wciśnięta w najbliższą kategorię. Dwa nie mają poprawnej odpowiedzi w 5 kategoriach:
- `R1-7q8xEk0A` → **rosyjski nacjonalizm** (anty-Łukaszenko, ale imperialny/antyzachodni) → wrzucone w `neutralny`.
- `IYVHA8p-IaY` → **pro-łukaszenkowski** (ONT), wprost ≠ prokremlowski → wciśnięte w `prokremlowski`.
Tu niezgoda jest **winą typologii, nie kodera**. `prokremlowski` jest przeciążone (3 różne konstrukty).

**(4) Kontestowalność — 11 contested.**
Gdzie piszę "otwarte na interpretację" (AO2muYJEcrc — czy ukr. antywojenny jest prokremlowski?; gAhXLx34C8k — antyrządowy митинг a "за ZSU"; i83B2D50RPg — 4 ramy naraz), to **realny spór badawczy**, nie pomyłka. To dokładnie miejsca, gdzie spodziewamy się rozejścia modeli.

---

## 3. Przeładowanie tezy: od "linijki" do "taksonomii niezgody"

W oryginalnym planie ręczne kodowanie miało dać **jedną liczbę** (κ na slajdzie 9). Drugi slój zmienia jego rolę:

> Ręczne kodowanie nie jest *wzorcem do zmierzenia modelu*. Jest **mapą tego, gdzie i dlaczego znaczenie jest trudne** — a niezgoda człowiek↔model rozkłada się na cztery nazwane, mierzalne przyczyny.

To jest "więcej niż agreement": κ samo w sobie **ukrywa** wszystkie cztery czynniki. Ujawnione, zamieniają deflacyjny wynik ("κ niewysokie") w wynik pozytywny ("oto anatomia niezgody — i jest czytelna").

To także **podwójnie uziemia slajd 15 (killer)**: modele rozchodzą się tam, gdzie (a) tekst niedookreśla, (b) kodbook ma lukę, (c) człowiek sam zaznaczył spór. Niezgoda modeli = niezgoda badaczy — teraz pokazana w **ludzkim rozumowaniu**, nie tylko w zachowaniu modeli.

---

## 4. Co wstawić do `talk_outline_PL.md`

- **Slajd 9 (κ):** dodać uczciwą oświetlającą uwagę: *"κ nie jest wyższe, bo w 87% itemów kodowałem na podstawie informacji spoza tekstu, a w 1/3 sam tekst niedookreśla ramę — to mierzalne, nie wymówka."* κ staje się wejściem do taksonomii, nie oceną.
- **Slajd 15 (killer):** wzmocnić — niezgoda modeli pokrywa się z itemami, które **człowiek** oznaczył jako `contested`; + dwie luki kodbooka (rosyjski nacjonalizm, pro-Łukaszenko) jako dowód, że część "błędów" to wina typologii.
- **Nowy backup B11:** "4-osiowa taksonomia niezgody" — tabela z §1 + dwa przypadki `missing`.

---

## 5. Most do filaru wideo (oś E)

`visual_footage`: wśród 33 ustalonych itemów rama tekstowa i treść wizualna **rozchodzą się** —
- `rfvW28axDaw`: tekst "100% o proteście", ale ZERO ujęć protestu (trzej eksperci gadają).
- `i83B2D50RPg` / `1d0eSMlD3hw`: tekst analityczny/zachodni, ale film prawie w całości z ujęć protestu.

To dosłowny, dane-poziomowy argument, że **tekst nie wystarcza** (slajd 4) i że potrzebny jest drugi, multimodalny filar (slajd 13). Tę samą lukę widać w dwóch modalnościach.
