"""Regenerate outputs/v2_feed_ready.csv.gz from MariaDB.

Replicates the EDA.ipynb logic for cells 8, 17, 19, 25, 27, 29, 31, 32 without
requiring the original CSV export. Reads VIDEOS + VID_TOPICS + TOPICS +
VIDEO_METADATA, joins to the 21,710 distinct Politics-topic videos that have
metadata, keeps the LATEST snapshot per YT_ID, and writes the same schema
that pipeline/stage_a_embed.py consumes.

Usage:
    python scripts/regen_feed_ready.py
"""
from __future__ import annotations

import os
import re
from collections import Counter

import pandas as pd
import pymysql

OUT_PATH = "outputs/v2_feed_ready.csv.gz"
POLITICS_URL = "https://en.wikipedia.org/wiki/Politics"

SQL = f"""
SELECT
    vm.YT_ID,
    vm.DATE AS metadata_captured_on,
    vm.TITLE,
    vm.DESCRIPTION,
    v.PUBLISHED_AT,
    v.DEFAULT_LANG,
    v.DEFAULT_AUDIO_LANG,
    v.DURATION,
    v.LIVE_BROADCAST
FROM VIDEO_METADATA vm
JOIN VIDEOS v       ON v.YT_ID = vm.YT_ID
JOIN VID_TOPICS vt  ON vt.YT_ID = vm.YT_ID
JOIN TOPICS t       ON t.id    = vt.TOPIC_ID
WHERE t.TOPIC = '{POLITICS_URL}'
  AND vm.DATE = (
        SELECT MAX(vm2.DATE)
        FROM VIDEO_METADATA vm2
        WHERE vm2.YT_ID = vm.YT_ID
      )
"""


def parse_dur(s: str):
    if not s:
        return None
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", s)
    if not m:
        return None
    h, mi, se = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + se


def main():
    print("[1/6] Connecting to MariaDB and pulling Politics-topic latest snapshots …")
    conn = pymysql.connect(
        user="sulzhytski",
        unix_socket="/tmp/mysql.sock",
        database="metadata",
        charset="utf8mb4",
    )
    try:
        df = pd.read_sql(SQL, conn)
    finally:
        conn.close()

    df["TITLE"] = df["TITLE"].fillna("").astype(str)
    df["DESCRIPTION"] = df["DESCRIPTION"].fillna("").astype(str)
    print(f"      Rows: {len(df):,}  |  Unique YT_IDs: {df['YT_ID'].nunique():,}")

    if df["YT_ID"].duplicated().any():
        print("      WARNING: duplicate YT_IDs detected, deduping (keep first)")
        df = df.drop_duplicates(subset="YT_ID", keep="first").reset_index(drop=True)

    print("[2/6] Parsing DURATION → dur_sec …")
    df["dur_sec"] = df["DURATION"].map(parse_dur)
    print(f"      Unparsed durations: {df['dur_sec'].isna().sum():,}")

    print("[3/6] Hashtag and URL counts …")
    hashtag_re = re.compile(r"#([\wЀ-ӿ]+)", re.UNICODE)
    url_re = re.compile(r"https?://[^\s<>\"']+", re.UNICODE)
    df["title_hashtags"] = df["TITLE"].apply(hashtag_re.findall)
    df["desc_hashtags"] = df["DESCRIPTION"].apply(hashtag_re.findall)
    df["n_title_tags"] = df["title_hashtags"].str.len()
    df["n_desc_tags"] = df["desc_hashtags"].str.len()
    df["n_urls"] = df["DESCRIPTION"].apply(lambda s: len(url_re.findall(s)))

    print("[4/6] Protest signal regex …")
    protest_pat = re.compile(
        r"(\bпротест\w*|\bprotest\w*|\bмитинг\w*|\bпратэст\w*|\bмайдан|maidan|"
        r"\bреволюц\w*|revolution|демонстра|demonstration|rally|rallies|"
        r"riot|восстан\w*|забастовк\w*|стачк\w*|stachk\w*|бунт\w*)",
        re.IGNORECASE | re.UNICODE,
    )
    df["protest_in_title"] = df["TITLE"].apply(lambda s: bool(protest_pat.search(s)))
    df["protest_in_desc"] = df["DESCRIPTION"].apply(lambda s: bool(protest_pat.search(s)))
    df["protest_anywhere"] = df["protest_in_title"] | df["protest_in_desc"]
    print(
        f"      protest_anywhere: {df['protest_anywhere'].sum():,} / {len(df):,} "
        f"({100*df['protest_anywhere'].mean():.1f}%)"
    )

    print("[5/6] Country flags + country_combo (B/U/R) …")
    cs = {
        "BY": re.compile(
            r"(\bбеларус\w*|\bbelarus\w*|\bbelarusian\w*|\bбелорус\w*|\bлукаш\w*|"
            r"\blukash\w*|\bминск|\bminsk|\bтиханов\w*|\btsikhan)",
            re.IGNORECASE | re.UNICODE,
        ),
        "UA": re.compile(
            r"(\bукраин\w*|\bukrain\w*|\bкиев|\bkyiv|\bzelensk\w*|\bзеленск\w*|"
            r"\bодесс|\bodes|\bхарьков|\bkharkiv|\bдонбас|\bdonbas|\bдонецк|"
            r"\bdonetsk|\bкрым|\bcrimea|\bмариуполь|\bmariupol)",
            re.IGNORECASE | re.UNICODE,
        ),
        "RU": re.compile(
            r"(\bроссиян\w*|\brussian\b|\bnavalny\w*|\bнавальн\w*|\bпутин|\bputin|"
            r"\bмосква|\bmoscow|\bкремль|\bkremlin)",
            re.IGNORECASE | re.UNICODE,
        ),
    }
    for c, pat in cs.items():
        df[c] = df["TITLE"].apply(lambda s: bool(pat.search(s))) | df["DESCRIPTION"].apply(
            lambda s: bool(pat.search(s))
        )

    def _combo(row):
        flags = {"B": row["BY"], "U": row["UA"], "R": row["RU"]}
        s = "".join(k for k in "BUR" if flags[k])
        return s or "(none)"

    df["country_combo"] = df.apply(_combo, axis=1)
    print(df["country_combo"].value_counts().to_string())

    print("[6/6] feed_text construction + quality flags + save …")

    def is_only_urls(s: str) -> bool:
        if not s.strip():
            return False
        no_url = re.sub(r"https?://\S+", " ", s).strip()
        no_hashtag = re.sub(r"#\S+", "", no_url).strip()
        return len(no_hashtag) < 20

    df["desc_len"] = df["DESCRIPTION"].str.len()
    df["desc_only_urls"] = df["DESCRIPTION"].apply(is_only_urls)

    def build_feed(row):
        t = row["TITLE"] or ""
        d = row["DESCRIPTION"] or ""
        s = t + " . " + d
        s = re.sub(r"https?://\S+", "<URL>", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    df["feed_text"] = df.apply(build_feed, axis=1)

    def meaningful_chars(s: str) -> int:
        s = re.sub(r"https?://\S+", "", s)
        s = re.sub(r"#\S+", "", s)
        return len(s.strip())

    df["meaningful_len"] = df["feed_text"].apply(meaningful_chars)
    print(
        f"      ≥30 meaningful chars: {(df.meaningful_len >= 30).sum():,} "
        f"({100*(df.meaningful_len >= 30).mean():.1f}%)"
    )

    cols = [
        "YT_ID",
        "PUBLISHED_AT",
        "DEFAULT_AUDIO_LANG",
        "DURATION",
        "dur_sec",
        "LIVE_BROADCAST",
        "TITLE",
        "DESCRIPTION",
        "feed_text",
        "meaningful_len",
        "n_urls",
        "n_title_tags",
        "n_desc_tags",
        "protest_anywhere",
        "protest_in_title",
        "protest_in_desc",
        "BY",
        "UA",
        "RU",
        "country_combo",
        "desc_only_urls",
        "metadata_captured_on",
    ]
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    df[cols].to_csv(OUT_PATH, index=False, compression="gzip")
    size_mb = os.path.getsize(OUT_PATH) / 1024 / 1024
    print(f"\n      Wrote {OUT_PATH}  ({size_mb:.1f} MB, {len(df):,} rows)")


if __name__ == "__main__":
    main()
