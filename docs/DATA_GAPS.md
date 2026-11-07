# Data gaps — что в базе ещё не использовано (аудит 2026-06-11)

Полный проход по колонкам всех 9 таблиц MariaDB + сверка с готовыми EXPORT'ами.
Числа — на v2-подмножестве (21,710), запросы воспроизводимы из этого файла.

## Неиспользованные данные (по убыванию ценности)

| # | Источник | Что | Объём (v2) | Применение |
|---|---|---|---|---|
| 1 | `VID_TOPICS`/`TOPICS` | **топик-флаги кроме Politics**: Military, Television_program, Religion… (Society вырожден — 99.3% co-occurrence) | Military 1,105; TV 737; Religion 73 | дешёвые фичи гейта/ранга: war-контент и ток-шоу → чаще `absent`. → `scripts/build_static_flags.py` |
| 2 | `VID_TAGS`+`TAGS` (БД) | **полный источник тегов** — 19,624 v2-видео (≥ CSV-покрытия 19,623) | 90.4% | убрать зависимость от `complete_video_info_*.csv`: `enrich_with_tags.py --from-db` (TODO) |
| 3 | `VIDEOS.CAPTION` | есть субтитры | **1,638 (7.5%)** | (а) флаг-фича; (б) **будущий источник текста**: субтитры через API → эмбеддинг контента, не только метаданных |
| 4 | `VIDEO_METADATA.LICENSE` | creativeCommon | 452 | переиспользуемый/перезаливаемый контент — прокси цепочек распространения |
| 5 | `VIDEOS.CONTENT_RATING` | ytAgeRestricted | 47 | модерационный сигнал (жёсткие кадры протестов?) — качественная проверка |
| 6 | `VIDEO_METADATA.EMBEDDABLE` | запрет встраивания | 249 | контроль распространения автором/платформой |
| 7 | `VIDEOS.LIVE_BROADCAST` | live/upcoming | 246+11 | связка с live-retitling (EXPORT 2); анти-фича для footage |
| 8 | `VIDEOS.DEFAULT_LANG` | язык интерфейса (≠ audio) | 12,817 set | дополняет DEFAULT_AUDIO_LANG (89.5%); кросс-проверка языка |
| 9 | `STATS` траектории | только оконные агрегаты использованы | 6.4M строк | формы кривых: burst-detection, второй пик (revival), плато |
| 10 | `SEARCH_RESULTS` ранг-траектории | best/median использованы | 1.65M | динамика ранга (video,term) во времени: подъём/падение видимости |
| 11 | `SEARCHES.TIMESTAMP` | время суток запроса | 15,240 | контроль скрейпера; для анализа малоценно |
| 12 | `VIDEO_METADATA` non-Politics | 5,595 видео с метаданными вне Politics (Lifestyle/Music/Entertainment) | 5,595 | низкий приоритет; Society-without-Politics 1,789 — возможен civic-контент |

**Мёртвые колонки** (проверено): `STATS.FAVORITE_COUNT` — всюду 0; `SEARCHES.LIMIT` —
константа; `VIDEO_METADATA.LICENSED_CONTENT` — 0 на v2; `MADE_FOR_KIDS` — 8 видео;
`VIDEOS.KIND/DIMENSION` — константы по построению; `PRIVACY_STATUS` — всюду public
(известно с EXPORT 2).

## EXPORT'ы: сделано / не сделано

Готово: 2 (title edits), 3 (churn), 4 (engagement), 5 (search), 6 (canonical tags),
7 (hypergraph), 10 (sampling validity).

Не сделано (и теперь имеет инфраструктуру):
- **static_flags** — топик-флаги + caption/license/live/embeddable/age-restricted
  (`scripts/build_static_flags.py`, работает сразу);
- **video_api** — каналы + текущая доступность через YouTube API
  (`scripts/fetch_video_api.py`, ждёт `YT_API_KEY`);
- **metadata bulk** — 261,099 Politics-видео без снапшота
  (`scripts/fetch_metadata_bulk.py`, ждёт `YT_API_KEY`);
- **event features** — близость публикации к протестным событиям
  (`scripts/build_event_features.py` + `data/event_calendar.csv`, работает сразу);
- траектории STATS / ранг-траектории SEARCH_RESULTS — идеи №9–10, скриптов пока нет.
