# Framing codebook v0.2 — drugi slój kodowania (osie wyprowadzone z komentarzy kodera)

Version: 0.2 — 2026-05-29
Authors: dr Ilya Sulzhytski (PI)
Builds on: `framing_codebook.md` (v0.1, 5 ram). Nie zastępuje v0.1 — **nadbudowuje**.
Source data: `coding_progress.json` (60 itemów, ręczne kodowanie z `coding_ui.html`: `label` + `confidence` + rozbudowane `notes`).
Operationalises: v0.1 §5.3 — *"No multi-label. v0.2 may add a secondary frame field for hybrid cases — open question."* Ten dokument zamyka ten otwarty punkt.

---

## 0. Po co drugi slój

Pierwszy slój (v0.1) wymusza **jedną** etykietę ramy na film — bo tego wymaga κ. Ale komentarze kodera (wszystkie 60 itemów mają rozbudowaną notatkę) pokazują, że pojedyncza etykieta **schłapuje** kilka niezależnych osi decyzji. Drugi slój koduje te osie jako osobne pola — to **axial coding** własnego rozumowania kodera.

Cel nie jest metryczny (nie liczymy tu κ). Cel jest **walidacyjny**: zamienić ręczne kodowanie z *linijki-wzorca* w **taksonomię niezgody** — mapę tego, *gdzie* i *dlaczego* etykieta jest trudna. To jest sens tezy "tu jest więcej niż agreement".

Jednostka analizy: ten sam film (`YT_ID`) co w v0.1. Wejście kodera-LLM to nadal **tylko `feed_text` = TITLE + DESCRIPTION**. Człowiek miał dostęp do większej liczby źródeł — i ta asymetria jest właśnie pierwszą osią.

---

## 1. Oś A — Baza dowodowa / asymetria informacyjna (`evidence_base`)

**Pytanie:** *na czym opiera się etykieta człowieka?* Pole multi-wartościowe (rozdzielone `|`).

| Wartość | PL | EN | Sygnał w notatce |
|---|---|---|---|
| `text` | tytuł + opis (to, co widzi model) | title + description (what the model sees) | "po nagłówku…", "z tekstu" |
| `close` | koder obejrzał film / transkrypcję | coder watched the video/transcript | "это я знаю просмотрев видео", "на видео…" |
| `channel` | tożsamość kanału/autora przesądziła | channel/author identity decided | "канал strana.ua", "Диана Панченко", "ОНТ", "УНИАН", "Дождь" |
| `context` | wiedza zewnętrzna o wydarzeniu | external world knowledge | "известно из контекста", "по дате" |

**Flagi pochodne:**
- `used_extratextual` (bool) — czy etykieta opiera się na czymś **spoza tekstu** (close/channel/context). **Jeśli `true`, to ewentualna niezgoda człowiek↔model NIE jest błędem modelu — jest asymetrią informacji.**
- `video_available` (bool) — czy materiał dało się obejrzeć. `false` = "видео недоступно / не нашёл" → ludzki "gold" jest tu częściowo inferencyjny (data decay).
- `text_underdetermined` (bool) — czy z **samego tekstu** etykieta byłaby inna lub nieokreślona. Koder czasem mówi to wprost: gmBPdjUjK_Q — *"для классификатора мог быть 5"*.

> **Reguła:** `used_extratextual=true` zawsze, gdy w bazie jest `close`, `channel` lub `context`. `text`-only (`used_extratextual=false`) zarezerwowane dla itemów, gdzie koder oparł się wyłącznie na nagłówku/opisie.

---

## 2. Oś B — Relewancja protestu (`protest_relevance`)

Codebook v0.1 to *protest framing*. Ale retrieval semantyczny (slajd 7) wyciągnął dużo treści **wojennej/mobilizacyjnej**, nie protestowej. Koder stale rozdziela *temat* od *ramy*.

| Wartość | Definicja | Przykład (YT_ID) |
|---|---|---|
| `direct` | film jest o proteście (często z ujęciami protestu) | `0JEQNwa9VB0` ("100% о протестах"), `oAY7OeR7zO4` (kadry zatrzymań) |
| `indirect` | protest peryferyjny: reakcja na protest, represje jako ciąg dalszy, kryzys migracyjny jako następstwo | `KlhPQBlQ2g8` (kontr-protest), `85dJ-1Y5DLQ` (kryzys migracyjny), `Top9J3IiWZE` (represje) |
| `absent` | nie o proteście (wojna / mobilizacja / inne) | `nwcaLjqh4h8` (czat-ruletka), `a-QON3Iv8Is` (przemówienie Putina) |

---

## 3. Oś C — Adekwatność kodbooka (`codebook_fit`)

Czy 5 kategorii v0.1 utrzymuje item?

| Wartość | Definicja |
|---|---|
| `fits` | czysto pasuje do przypisanej kategorii |
| `forced` | wciśnięty do najbliższej kategorii, niedopasowany (np. proukr./antyros. wpadające do `neutralny`; antymobilizacyjne strana.ua wpadające do `antywojenny`) |
| `missing` | **brak adekwatnej kategorii w schemacie** |

**Pole `shadow_label`** (free-text, PL) — wypełniane tylko przy `forced`/`missing`: ramę, której koder *naprawdę* chciał.

**Dwa przypadki `missing` — luki konstruktu, nie błędy kodera:**
- `R1-7q8xEk0A` → **rosyjski nacjonalizm** (imperialny: krytykuje Łukaszenkę *jako antyrosyjskiego*, "белорусская нация будет угрозой воссоединения русских земель"). Brak kategorii → wrzucone w `neutralny`.
- `IYVHA8p-IaY` → **pro-łukaszenkowskie / prorządowe** (kanał ONT). Koder wprost: *"не прокремлевское а про-лукашенковское"*. Brak kategorii → wciśnięte w `prokremlowski`.

> Wniosek: `prokremlowski` jest w v0.1 przeciążone — łączy *pro-rosyjski-stan* + *pro-Łukaszenko-stan* + *ukraińskie głosy prorosyjskie* (Panczenko, strana.ua). v0.3 powinno rozdzielić te konstrukty + dodać `rosyjsko-nacjonalistyczny`.

---

## 4. Oś D — Kontestowalność / pewność postawy (`contestedness`)

| Wartość | Definicja | Sygnał |
|---|---|---|
| `explicit` | postawa jawnie w tekście/treści | "явно", "декларативно" |
| `inferred` | prawdopodobna, koder wnioskuje | "скорее всего", "вероятность высокая" |
| `contested` | koder **sam** sygnalizuje spór/dwuznaczność | "открытый для интерпретации", "позиция неясна", współistnienie ram |

> **`contested` to klucz do slajdu 15 (killer).** Tam, gdzie koder-człowiek pisze "otwarte na interpretację", spodziewamy się rozejścia modeli. Niezgoda nie jest szumem — jest mapą realnego sporu (np. Białoruś-2020: rama "narodowa" ↔ "antywojenna").

---

## 5. Oś E (opcjonalna, extension) — Treść wizualna (`visual_footage`)

Most do filaru wideo. Koder odnotowuje, czy film **zawiera** ujęcia protestu, czy to gadająca głowa.

| Wartość | Definicja | Przykład |
|---|---|---|
| `present` | są realne ujęcia protestu | `i83B2D50RPg` ("удивительно богатое видео… кадров протеста"), `1d0eSMlD3hw` ("почти полностью из кадров протеста") |
| `talking_head` | analiza/komentarz, brak ujęć protestu | `rfvW28axDaw` ("нет кадров самого протеста — это обсуждение тремя экспертами"), `R1-7q8xEk0A` |
| `none` | są ujęcia, ale nie protestu (np. przemówienie Putina) | `a-QON3Iv8Is`, `c-N6tUhCbWQ` |
| `unknown` | nie da się ustalić (np. wideo niedostępne) | |

> **Dlaczego to ważne:** rama tekstowa i treść wizualna **rozchodzą się w samych danych**. Tekst "neutralno-analityczny" bywa pełen ujęć protestu; tekst "100% o proteście" bywa samą gadającą głową. To dosłowny argument za drugim, multimodalnym filarem ("od tekstu do obrazu").

---

## 6. Wynik (artefakt)

`coding_layer2.csv` — 60 wierszy × kolumny:
`yt_id, primary_label, confidence, evidence_base, used_extratextual, video_available, text_underdetermined, protest_relevance, codebook_fit, shadow_label, contestedness, visual_footage, note_excerpt`.

Generowany przez `build_layer2.py` (kodowanie ręczne w słowniku `SECOND_LAYER`, nie heurystyka). Tally opisowe → patrz `layer2_insights.md`.

---

## 7. Changelog

- **v0.2 (2026-05-29)** — dodano 4 osie wtórne (A–D) + opcjonalną E, wyprowadzone z axial codingu 60 notatek. Zamyka v0.1 §5.3.
- **v0.1 (2026-05-27)** — 5 ram, single-label.

## 8. Roadmap v0.3 (otwarte)
1. Rozbić `prokremlowski` → {pro-rosyjski-stan, pro-łukaszenkowski, ukr.-prorosyjski}.
2. Dodać kategorię `rosyjsko-nacjonalistyczny`.
3. Multi-label dla ram współistniejących (i83B2D50RPg ma 4).
4. Osobne pole `topic` (protest / wojna / mobilizacja / migracja) niezależne od `frame`.
