"""Detect title / description / upload-status edits across VIDEO_METADATA snapshots.

Per `docs/EXPORTS_ROADMAP.md` §6 (EXPORT 2). The roadmap originally proposed
reading a pre-extracted CSV; with the MariaDB instance now reloaded (see
`docs/RESULTS_LOG.md` → "MariaDB restoration — 2026-05-21") we can pull the
data directly via socket-auth and skip the intermediate file.

Outputs (under outputs/):
    title_edits_feasibility.csv  one-row summary of yields used to log results
    title_edits.csv              per-edited-video summary
                                 (YT_ID, n_snapshots, n_title_uniq, n_desc_uniq,
                                  n_upload_uniq, first_date, last_date,
                                  first_title, last_title, all_titles)

Privacy-status churn is *not* included: every snapshot in this dump is
PRIVACY_STATUS='public', so within-table privacy edits are zero. Real
privacy churn must come from STATS-gap detection (EXPORT 3).
"""
from __future__ import annotations

import argparse
import csv
from collections import OrderedDict
from pathlib import Path

import pandas as pd
import pymysql


SQL_EDITED_VIDEOS = """
SELECT vm.YT_ID, vm.DATE, vm.TITLE, vm.DESCRIPTION, vm.UPLOAD_STATUS
FROM VIDEO_METADATA vm
JOIN (
  SELECT YT_ID
  FROM VIDEO_METADATA
  GROUP BY YT_ID
  HAVING COUNT(DISTINCT BINARY TITLE) > 1
      OR COUNT(DISTINCT MD5(DESCRIPTION)) > 1
      OR COUNT(DISTINCT UPLOAD_STATUS) > 1
) edited USING (YT_ID)
ORDER BY vm.YT_ID, vm.DATE
"""

SQL_FEASIBILITY = """
SELECT
  SUM(n_title_uniq   > 1) AS n_with_title_change,
  SUM(n_desc_uniq    > 1) AS n_with_desc_change,
  SUM(n_upload_uniq  > 1) AS n_with_upload_status_change,
  COUNT(*)                AS n_multi_snapshot,
  (SELECT COUNT(DISTINCT YT_ID) FROM VIDEO_METADATA) AS n_distinct_videos
FROM (
  SELECT YT_ID,
         -- BINARY forces byte-level distinction (case + emoji colour);
         -- the database's utf8mb4_unicode_ci collation would otherwise
         -- collapse `Alyona Alyona`↔`alyona alyona` and `🟤`↔`🔴`,
         -- under-counting genuine creator edits by ~2 % (214 vs 218 on
         -- this corpus). The per-video reduce below uses Python's binary
         -- `a != b`; the feasibility row matches it exactly.
         COUNT(DISTINCT BINARY TITLE)            AS n_title_uniq,
         COUNT(DISTINCT MD5(DESCRIPTION))        AS n_desc_uniq,
         COUNT(DISTINCT UPLOAD_STATUS)           AS n_upload_uniq
  FROM VIDEO_METADATA
  GROUP BY YT_ID
  HAVING COUNT(*) > 1
) t
"""


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--db-user",    default="sulzhytski")
    p.add_argument("--db-name",    default="metadata")
    p.add_argument("--db-socket",  default="/tmp/mysql.sock",
                   help="UNIX socket for the local MariaDB instance")
    p.add_argument("--out-summary",     default="outputs/title_edits_feasibility.csv")
    p.add_argument("--out-edits",       default="outputs/title_edits.csv")
    p.add_argument("--v2-feed",         default="outputs/v2_feed_ready_with_tags.csv.gz",
                   help="optional v2 feed for intersection report (informational only)")
    return p.parse_args()


def connect(args):
    """Try the canonical Homebrew socket path, fall back to TCP on localhost."""
    for sock in (args.db_socket, "/opt/homebrew/var/mysql/mysql.sock", "/tmp/mariadb.sock"):
        if Path(sock).exists():
            return pymysql.connect(user=args.db_user, database=args.db_name,
                                   unix_socket=sock, charset="utf8mb4")
    return pymysql.connect(user=args.db_user, database=args.db_name,
                           host="127.0.0.1", charset="utf8mb4")


def main():
    args = parse_args()

    print(f"[1/4] Connecting to MariaDB as {args.db_user}")
    conn = connect(args)

    print(f"\n[2/4] Feasibility summary")
    feas = pd.read_sql(SQL_FEASIBILITY, conn)
    n_total      = int(feas["n_distinct_videos"].iloc[0])
    n_multi      = int(feas["n_multi_snapshot"].iloc[0])
    n_title      = int(feas["n_with_title_change"].iloc[0])
    n_desc       = int(feas["n_with_desc_change"].iloc[0])
    n_upload     = int(feas["n_with_upload_status_change"].iloc[0])
    print(f"      distinct videos in VIDEO_METADATA: {n_total:>7,}")
    print(f"      multi-snapshot (>=2):              {n_multi:>7,}  ({100*n_multi/n_total:.1f}%)")
    print(f"      with TITLE change:                 {n_title:>7,}  ({100*n_title/n_multi:.2f}% of multi)")
    print(f"      with DESCRIPTION change:           {n_desc:>7,}  ({100*n_desc/n_multi:.2f}% of multi)")
    print(f"      with UPLOAD_STATUS change:         {n_upload:>7,}  ({100*n_upload/n_multi:.2f}% of multi)")

    Path(args.out_summary).parent.mkdir(parents=True, exist_ok=True)
    feas.to_csv(args.out_summary, index=False)
    print(f"      wrote {args.out_summary}")

    print(f"\n[3/4] Pulling per-snapshot rows for edited videos")
    snaps = pd.read_sql(SQL_EDITED_VIDEOS, conn, parse_dates=["DATE"])
    print(f"      {len(snaps):,} snapshot rows for {snaps['YT_ID'].nunique():,} videos")

    print(f"\n[4/4] Reducing to per-video summary")

    def reduce(g: pd.DataFrame) -> pd.Series:
        g = g.sort_values("DATE")
        titles = g["TITLE"].tolist()
        descs  = g["DESCRIPTION"].tolist()
        # consecutive-transition count, not just distinct-set size: a title that
        # toggles A->B->A counts as 2 changes, distinct-count would give 2 too.
        # The two agree only when changes are monotonic; for an audit signal we
        # prefer the transition count.
        return pd.Series({
            "n_snapshots":     len(g),
            "n_title_uniq":    g["TITLE"].nunique(),
            "n_desc_uniq":     pd.Series([hash(d) for d in descs]).nunique(),
            "n_upload_uniq":   g["UPLOAD_STATUS"].nunique(),
            "n_title_changes": sum(a != b for a, b in zip(titles[:-1], titles[1:])),
            "n_desc_changes":  sum(a != b for a, b in zip(descs[:-1],  descs[1:])),
            "first_date":      g["DATE"].min().date(),
            "last_date":       g["DATE"].max().date(),
            "first_title":     titles[0],
            "last_title":      titles[-1],
            "all_titles":      " || ".join(OrderedDict.fromkeys(titles)),
        })

    summary = (snaps.groupby("YT_ID", group_keys=False)
                    .apply(reduce, include_groups=False)
                    .reset_index())
    summary.to_csv(args.out_edits, index=False, quoting=csv.QUOTE_MINIMAL)
    kb = Path(args.out_edits).stat().st_size / 1024
    print(f"      wrote {args.out_edits}  ({kb:.0f} KB, {len(summary):,} rows)")

    # Optional intersection with the v2 21,710-video subset
    feed_path = Path(args.v2_feed)
    if feed_path.exists():
        feed_ids = set(pd.read_csv(feed_path, usecols=["YT_ID"])["YT_ID"])
        n_v2 = summary["YT_ID"].isin(feed_ids).sum()
        print(f"\n[info] of {len(summary):,} edited videos, "
              f"{n_v2:,} ({100*n_v2/len(summary):.1f}%) intersect the v2 feed_ready set")

    print(f"\n[top]  10 most-edited titles (by transition count):")
    top = summary.nlargest(10, "n_title_changes")[
        ["YT_ID","n_snapshots","n_title_changes","first_title","last_title"]
    ]
    print(top.to_string(index=False))


if __name__ == "__main__":
    main()
