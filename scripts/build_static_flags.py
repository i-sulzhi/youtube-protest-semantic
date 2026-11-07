"""EXPORT static_flags — unexploited per-video static signals from MariaDB.

Closes DATA_GAPS.md items 1, 3–8 in one artefact: topic flags beyond Politics
(Military / TV-program / Religion — cheap relevance features; Society is
degenerate at 99.3% co-occurrence and skipped), caption availability, license,
live-broadcast status, embeddability, age restriction, interface language.

Output: outputs/static_flags.csv — one row per feed video, ready to join into
stage_e_rank / stage_e_ltr / train_distilled_gate on YT_ID.

Run from project root (MariaDB up):
    .venv_v2/bin/python scripts/build_static_flags.py
"""
from __future__ import annotations

import argparse

import pandas as pd
import pymysql

TOPIC_FLAGS = {
    "topic_military": "https://en.wikipedia.org/wiki/Military",
    "topic_tv": "https://en.wikipedia.org/wiki/Television_program",
    "topic_entertainment": "https://en.wikipedia.org/wiki/Entertainment",
    "topic_film": "https://en.wikipedia.org/wiki/Film",
    "topic_humour": "https://en.wikipedia.org/wiki/Humour",
    "topic_religion": "https://en.wikipedia.org/wiki/Religion",
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--feed", default="outputs/v2_feed_ready.csv.gz")
    p.add_argument("--out", default="outputs/static_flags.csv")
    return p.parse_args()


def main():
    a = parse_args()
    ids = pd.read_csv(a.feed, usecols=["YT_ID"])["YT_ID"]
    print(f"[1/4] Feed scope: {len(ids):,} videos")

    conn = pymysql.connect(user="sulzhytski", unix_socket="/tmp/mysql.sock",
                           database="metadata", charset="utf8mb4")
    try:
        with conn.cursor() as c:
            c.execute("CREATE TEMPORARY TABLE scope (YT_ID varchar(11) PRIMARY KEY)")
            c.executemany("INSERT INTO scope VALUES (%s)", ids.tolist())
        conn.commit()

        print("[2/4] VIDEOS + latest VIDEO_METADATA flags …")
        vid = pd.read_sql("""
            SELECT v.YT_ID,
                   v.CAPTION = 'true'                         AS has_captions,
                   v.DEFINITION = 'hd'                        AS is_hd,
                   v.LIVE_BROADCAST                           AS live_broadcast,
                   v.CONTENT_RATING LIKE '%%ytAgeRestricted%%' AS age_restricted,
                   NULLIF(v.DEFAULT_LANG, '')                 AS default_lang
            FROM VIDEOS v JOIN scope USING (YT_ID)""", conn)
        meta = pd.read_sql("""
            SELECT vm.YT_ID,
                   vm.EMBEDDABLE                AS embeddable,
                   vm.LICENSE = 'creativeCommon' AS license_cc
            FROM VIDEO_METADATA vm JOIN scope USING (YT_ID)
            WHERE vm.DATE = (SELECT MAX(vm2.DATE) FROM VIDEO_METADATA vm2
                             WHERE vm2.YT_ID = vm.YT_ID)""", conn)

        print("[3/4] Topic flags …")
        topics = pd.read_sql("""
            SELECT vt.YT_ID, t.TOPIC
            FROM VID_TOPICS vt JOIN TOPICS t ON t.id = vt.TOPIC_ID
            JOIN scope ON scope.YT_ID = vt.YT_ID""", conn)
    finally:
        conn.close()

    df = vid.merge(meta, on="YT_ID", how="left")
    tset = topics.groupby("YT_ID")["TOPIC"].apply(set)
    df["n_topics"] = df["YT_ID"].map(tset.str.len()).fillna(0).astype(int)
    for col, url in TOPIC_FLAGS.items():
        flagged = set(topics.loc[topics["TOPIC"] == url, "YT_ID"])
        df[col] = df["YT_ID"].isin(flagged)

    print("[4/4] Writing …")
    df.to_csv(a.out, index=False)
    n = len(df)
    print(f"      wrote {a.out}: {n:,} rows × {len(df.columns)} cols")
    summary = {c: int(df[c].sum()) for c in
               ["has_captions", "age_restricted", "license_cc"] + list(TOPIC_FLAGS)}
    summary["live"] = int((df["live_broadcast"] == "live").sum())
    summary["not_embeddable"] = int((df["embeddable"] == 0).sum())
    print("      " + ", ".join(f"{k}={v}" for k, v in summary.items()))


if __name__ == "__main__":
    main()
