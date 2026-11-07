# Framing codebook — multilingual YouTube politics corpus

Version: 0.1 — draft, 2026-05-27
Authors: dr Ilya Sulzhytski (PI)
Corpus: `outputs/v2_feed_ready.csv.gz` — 21,710 YouTube videos with the Politics auto-topic, multilingual (RU/UA/BE/EN/DE/PL), 09/2020–04/2024 capture window.

This codebook defines the framing categories that human coders and LLM annotators will apply to TITLE + DESCRIPTION pairs in the AGH mini-study. The unit of analysis is a single video (one row per `YT_ID`); the input to the coder is the concatenated `feed_text` ≈ `TITLE + " . " + DESCRIPTION`.

---

## 1. Scope and assumptions

- **Languages.** The codebook is operationalised primarily in **Polish (PL)** and **English (EN)**. Source videos appear in Russian, Ukrainian, Belarusian, German, English and Polish; coders may apply the labels regardless of source language using the underlying definitions.
- **Coding unit.** One framing label per video. Mutually exclusive at the categorical level (no multi-labels in v0.1) — if two frames coexist, code the **dominant** one (≥60% of evaluative content) or fall back to `neutralny-informacyjny`.
- **What is being coded.** The framing of the *speaker/channel/text*, not of the event itself. A video reporting *on* protests against Lukashenka in a neutral news-format is `neutralny-informacyjny`, not `białorusko-narodowy`.
- **Construct validity hazard.** The dominant axis is "which side does the text take?" — not "what does the text describe?" Coders must distinguish *topic* from *stance*.

---

## 2. Categories

### 2.1 `prokremlowski` / pro-Kremlin

**Definition (PL).** Tekst przyjmuje perspektywę rosyjskiej władzy państwowej lub jej sojuszników. Charakterystyczne sygnały: określanie inwazji 2022 r. jako «specjalna operacja wojskowa» / «СВО» bez cudzysłowów dystansujących; delegitymizacja ukraińskiej państwowości lub białoruskiej opozycji; oskarżenia Zachodu o eskalację; nazewnictwo opozycjonistów («tak zwany», «agent Zachodu», «нацистский режим»); brak alternatywnych głosów w narracji.

**Definition (EN).** The text adopts the Russian state's framing or the framing of its allies. Signals: calling the 2022 invasion "special military operation" / "СВО" without distancing quotes; delegitimising Ukrainian statehood or the Belarusian opposition; blaming the West for escalation; pejoratives for opposition ("так называемые", "Western agents", "нацистский режим"); absence of alternative voices.

**Empirical examples from the corpus:**

| YT_ID | TITLE (truncated) | Why this category |
|---|---|---|
| `-C2EQObGebo` | «Беларусь и весь мир: успехи дипломатии 2023-го \| Итоги года \| САСС уполномочен заявить» | Official state framing: «дипломаты… невзирая на откровенную враждебность коллективного Запада…» «Беларусь является донором стабильности» — это official BelTA-style narrative |
| `-bfLaE56ckM` | «Лукашенко: Я в вертолёте летел и говорю: ну, нарочно сделал Караник! // Совещание в Гродно» | Direct broadcast of Lukashenko official meeting with no editorial framing/critique |

**Expected class size in 200-video sample:** small (≤15%). The corpus was collected via opposition-leaning anchor terms (Belsat, Navalny, anti-war), so genuine pro-Kremlin material is under-sampled. **This is a documented class imbalance** — coders should be ready for `prokremlowski` to be the rarest class.

---

### 2.2 `antywojenny` / antiwar

**Definition (PL).** Tekst eksplicytnie sprzeciwia się wojnie rosyjsko-ukraińskiej lub represjom państwowym (Białoruś 2020+, Rosja 2022+). Sygnały: protestowe hasła («нет войне», «свободу политзаключённым», «свободу Навальному»); relacje o zatrzymaniach, więzieniach, emigracji; głosy uchodźców/mobilizowanych; opozycyjna perspektywa przedstawiana jako prawomocna.

**Definition (EN).** The text explicitly opposes the Russo-Ukrainian war or state repression (Belarus 2020+, Russia 2022+). Signals: protest slogans ("нет войне", "free Navalny", "stop the war"); reports on arrests, political prisoners, exile; voices of refugees / mobilised soldiers / their families; opposition perspective treated as legitimate.

**Empirical examples:**

| YT_ID | TITLE (truncated) | Why this category |
|---|---|---|
| `-R_hgQ2YBKo` | «Приговор Навальному. 19 лет тюрьмы. Эфир из суда» | Live coverage of Navalny sentencing with explicit anti-regime framing |
| `-w6kJThXxXs` | «💥МИЛОВ: Всё накаляется! Путин готовит СИЛОВИКОВ / Россияне на грани БУНТА» | Opposition political analysis (Vladimir Milov), framing Putin as adversary |
| `-ybKzzmDDms` | «❗️Итоги дня \| Жёны мобилизованных подали в суд на Путина» | Anti-mobilisation grassroots framing — mothers/wives as resistance subject |

**Expected class size:** medium-large (≈20–25%) — overrepresented by sampling design.

---

### 2.3 `prozachodni` / pro-Western

**Definition (PL).** Tekst zajmuje perspektywę instytucji zachodnich (UE, NATO, USA) jako normatywnego punktu odniesienia. Sygnały: format «explainer» zachodnich mediów (DW, Reuters, BBC, Euronews, Voice of America); kadrowanie wojny w kategoriach «wartości demokratyczne vs autorytaryzm»; wsparcie integracji UA/BY z UE/NATO; perspektywa polityków i ekspertów zachodnich jako głównych źródeł.

**Definition (EN).** The text treats Western institutions (EU, NATO, US) as the normative reference. Signals: Western media explainer format (DW, Reuters, BBC, Euronews, VoA); framing the war as "democratic values vs authoritarianism"; advocacy for UA/BY integration with EU/NATO; Western politicians/experts as primary sources.

**Empirical examples:**

| YT_ID | TITLE (truncated) | Why this category |
|---|---|---|
| `--JP9cs0K1I` | «Belarus has been taken 'hostage' by Russia — DW Conflict Zone» | DW format, Belarusian opposition as guest, EN-language framing for Western audience |
| `-hIwtECfxGs` | «Ukrainian family await father's return from Russian captivity \| REUTERS» | Reuters explainer, war-victim humanisation, EN-US for Western audience |
| `-c6FzA5VYl8` | «La mort de Navalny va-t-elle changer quelque chose en Russie ?» | French public-broadcast format (C Ce soir, France 5), Western institutional perspective |

**Expected class size:** medium (≈15–20%).

---

### 2.4 `białorusko-narodowy` / Belarusian-national

**Definition (PL).** Tekst opiera się na białoruskiej tożsamości narodowej jako odrębnej od rosyjskiej. Sygnały: flaga biało-czerwono-biała / «БЧБ»; Cichanouska, Calinowski, Bialous; historia WKL i opozycja wobec «русского мира»; białoruski język w narracji; redakcje emigracyjne (Belsat z Warszawy, Radio Swaboda z Wilna, Nasza Niwa, Wokrug niemnu); odniesienia do Polski i Litwy jako schronienia.

**Definition (EN).** The text grounds itself in Belarusian national identity as distinct from Russian. Signals: BCB flag / "БЧБ"; Tsikhanouskaya, Kalinouski, Bialous; references to GDL history and opposition to "русский мир"; Belarusian language in the narrative; émigré editorial centres (Belsat from Warsaw, Radyjo Svaboda from Vilnius, Nasha Niva); references to Poland/Lithuania as refuge.

**Empirical examples:**

| YT_ID | TITLE (truncated) | Why this category |
|---|---|---|
| `-2Vd96bAxJg` | «У Лідскім РАУС памёр паэт Дзмітрый Сарокін. Лукашэнка пагражае краінам Балтыі / Навіны дня» | Belarusian-language Belsat news, frames Lukashenka as threat to Baltic states |
| `-C-cuaySvm0` | «❓Што забойства Навальнага азначае для Беларусі? / Аб'ектыў» | Belsat editorial in Belarusian, frames Navalny's death from Belarusian-national perspective |
| `-DfohAus4-w` | «Лукашэнка і Пуцін пахавалі Саюзную дзяржаву» | Belarusian-language framing of Lukashenka–Putin dynamic via national lens |

**Expected class size:** medium (≈15–20%) — overrepresented in the corpus due to the Belarus-centric search-discovery bias documented in EXPORT 5.

**Boundary note vs `prozachodni`.** Belsat in Belarusian = `białorusko-narodowy`; DW in English about Belarus = `prozachodni`. When both frames coexist (Belarusian opposition speaks via DW), code by *who is the implied addressee*: Belarusian diaspora → BN; Western audience → PZ.

---

### 2.5 `neutralny-informacyjny` / neutral-informational

**Definition (PL).** Tekst utrzymuje format newsowy bez wyraźnej oceny: streszczenia, briefingi, aktualności, raporty. Brak języka oceniającego, brak otwartego stronniczenia. To również **kategoria domyślna** w przypadku, gdy coder waha się 50/50 między dwoma framingami.

**Definition (EN).** The text maintains a news-format without explicit evaluation: summaries, briefings, updates, reports. No evaluative language, no overt partisanship. This is also the **default category** when the coder hesitates 50/50 between two framings.

**Empirical examples:**

| YT_ID | TITLE (truncated) | Why this category |
|---|---|---|
| `176sBlGslSA` | «"Новости. Сейчас" / 13:00 / 07.02.2024» (Belarusian state TV bulletin) | Bulletin-format with timecodes, no explicit evaluative stance even though source is state media |
| `2DjVGGKt6QI` | «Лукашенко прилетел в Москву / Протесты экоактивистов в Европе / Новости 24 мая» | Multi-item news roundup with descriptive timecodes, no editorial framing |
| `-8qNEuaAA9I` | «⚡️НОВОСТИ \| АТАКА НА ПОЛИЦИЮ В ЦЕНТРЕ МОСКВЫ \| «БИ-2» СОДЕРЖАТ В ДИКИХ УСЛОВИЯХ» | News-aggregator headline format, multiple items, no overt stance taken |

**Expected class size:** medium-large (≈25–30%) — many state-TV and news-aggregator videos default here even when their *source* is biased, because the text itself is presented as factual reporting.

**Construct validity hazard.** This is the category most likely to absorb genuinely pro-Kremlin or pro-opposition content that *presents* as news. The codebook deliberately accepts this trade-off — distinguishing covert framing from overt news requires inferential coding, which would lower inter-coder agreement.

---

## 3. Decision rules and edge cases

### 3.1 Conflict resolution priority

When two frames coexist:

1. Find the **dominant evaluative voice** (≥60% of speaker time / text content).
2. If unclear, ask: **who is the implied addressee?** (Diaspora / Western / Russian-speaking domestic / no-explicit-target.)
3. Default to `neutralny-informacyjny` when in genuine doubt.

### 3.2 Known ambiguities (document in coder notes)

- **`prokremlowski` vs `neutralny-informacyjny`** — most frequent. State-media bulletins (Беларусь 1, СТВ, Russia 1) often present pro-regime narrative *as news*. Rule: code `prokremlowski` only if explicit evaluative markers are present («так называемая оппозиция», «нацистский режим», «героические защитники»). Otherwise `neutralny-informacyjny`.
- **`białorusko-narodowy` vs `prozachodni`** — Belsat and Radyjo Svaboda are funded by Western governments but write in Belarusian for a Belarusian audience. Default: BN. Switch to PZ only when the text is in English/German/French and addressed to Western audiences.
- **`antywojenny` vs `prozachodni`** — Russian opposition channels (Navalny, Dozhd) are both anti-war and pro-Western. Default: `antywojenny` because their primary frame is *opposition to Russian state*, not *advocacy for Western institutions*.
- **`antywojenny` vs `białorusko-narodowy`** — Belarusian opposition channels are both. Default: `białorusko-narodowy` when Belarusian identity is the primary frame; `antywojenny` when the 2022 war / Russian mobilisation is the primary frame.

### 3.3 Out-of-scope

- Videos about pre-2014 events / Soviet history without contemporary framing → `neutralny-informacyjny`.
- Apolitical content that slipped through the Politics topic auto-classifier → `neutralny-informacyjny`.
- Non-Russian-Slavic / non-Eastern-European politics (e.g. US elections, Middle East) → still apply categories by analogy if a clear stance is visible; otherwise `neutralny-informacyjny`.

---

## 4. Inter-coder agreement protocol

- **Human coder:** dr Ilya Sulzhytski, hand-codes 60 items from the stratified 200-video sample.
- **LLM coders:** Claude Sonnet 4.6 + GPT-4o.
- For each item × LLM, run **≥2 prompt formulations × 2 temperatures (0.0, 0.5)** to measure prompt sensitivity.
- Report:
  - Cohen's κ (human × each LLM, overall and per-class)
  - Krippendorff's α across all 3 coders (human + 2 LLMs)
  - Per-class precision / recall / F1 (LLM vs human)
  - Cross-LLM disagreement rate (% items where Claude ≠ GPT among LLM-internal agreement on prompt × temperature)

---

## 5. Known limitations of this codebook

1. **Class imbalance.** `prokremlowski` is expected to be small (< 15%) due to corpus sampling bias. κ on this class will have wide CI.
2. **Stance vs topic conflation.** Most failures will be on the `prokremlowski` vs `neutralny-informacyjny` boundary — exactly the place where moderation policy matters most.
3. **No multi-label.** v0.1 forces a single label. v0.2 may add a secondary frame field (optional) for hybrid cases — open question.
4. **No temporal context.** A video about Maidan-2014 published in 2024 is coded by 2024-era framing, not 2014-era. This is deliberate but may bias historical content.
5. **Anchor-language bias.** The anchor queries that defined the retrieval are all Russian; videos in DE/EN that don't match Russian anchors are under-represented.

---

## 6. Changelog

- **v0.1 (2026-05-27)** — initial draft, 5 categories, drawn from `outputs/v2_feed_ready.csv.gz` real examples after `regen_feed_ready.py` rebuild from MariaDB.
