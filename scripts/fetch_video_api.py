"""Block 1.1 — fetch channel identity + current availability via YouTube API.

The corpus has no channel/uploader field anywhere local (validated 2026-06-03);
the YouTube Data API is the only canonical source. This fetches, for a chosen
scope, `videos.list?part=snippet,status,statistics`:

  * channel_id / channel_title  → the real channel prior (Block 1.2):
        build_channel_features.py --api-csv outputs/video_api.csv
  * found=False (deleted/private/terminated NOW)
                                → churn disentanglement (Block 1.4):
        scripts/disentangle_churn.py
  * current view/like/comment counts → engagement drift vs the 2024 capture.

Quota: 1 unit / 50 ids → pool 1,099 ≈ 22 units; full feed 21,710 ≈ 435 units
(daily quota 10,000). Checkpointed + resumable; key ONLY from YT_API_KEY env.

WAITS FOR INPUT: the YT_API_KEY env var. `--dry-run` works without it.

Run from project root:
    .venv_v2/bin/python scripts/fetch_video_api.py --dry-run
    YT_API_KEY=... .venv_v2/bin/python scripts/fetch_video_api.py --scope pool
    YT_API_KEY=... .venv_v2/bin/python scripts/fetch_video_api.py --scope feed
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from yt_api import BATCH, fetch_videos, require_key  # noqa: E402

SCOPES = {
    "pool": ("outputs/stage_e/protest_index.csv", "YT_ID"),
    "gated": ("outputs/stage_e/protest_index_gated.csv", "YT_ID"),
    "feed": ("outputs/v2_feed_ready.csv.gz", "YT_ID"),
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--scope", choices=list(SCOPES), default="pool")
    p.add_argument("--ids-csv", help="custom id list (overrides --scope)")
    p.add_argument("--id-col", default="YT_ID")
    p.add_argument("--out", default="outputs/video_api.csv")
    p.add_argument("--checkpoint", default="outputs/video_api_checkpoint.jsonl")
    p.add_argument("--quota-budget", type=int, default=None,
                   help="max requests this run (resume later)")
    p.add_argument("--dry-run", action="store_true",
                   help="validate scope + print quota estimate, no key needed")
    return p.parse_args()


def main():
    a = parse_args()
    src, col = (a.ids_csv, a.id_col) if a.ids_csv else SCOPES[a.scope]
    ids = pd.read_csv(src, usecols=[col])[col].drop_duplicates().tolist()
    n_req = (len(ids) + BATCH - 1) // BATCH
    print(f"[1/3] Scope '{a.ids_csv or a.scope}': {len(ids):,} ids "
          f"→ ≤{n_req} requests = ≤{n_req} quota units (of 10,000/day)")
    if a.dry_run:
        print("      dry-run: OK, nothing fetched")
        return

    key = require_key()
    print("[2/3] Fetching (checkpointed — safe to interrupt) …")
    done = fetch_videos(ids, key, Path(a.checkpoint), quota_budget=a.quota_budget)

    have = [done[i] for i in ids if i in done]
    df = pd.DataFrame(have).rename(columns={"yt_id": "YT_ID"})
    df["available"] = df["found"]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False)
    n_gone = int((~df["available"]).sum())
    print(f"[3/3] wrote {a.out}: {len(df):,} rows; "
          f"{n_gone} unavailable now ({100*n_gone/max(len(df),1):.1f}%) — "
          f"the churn-attribution signal")
    print(f"      channels: {df['channel_id'].nunique()} distinct")
    if len(df) < len(ids):
        print(f"      ⚠ {len(ids)-len(df)} ids still unfetched (quota budget?) — "
              "rerun to resume")
    print("\nNext:  scripts/build_channel_features.py --api-csv " + a.out)
    print("       scripts/disentangle_churn.py")


if __name__ == "__main__":
    main()
