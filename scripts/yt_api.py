"""Shared YouTube Data API v3 helper — batched, checkpointed, key-from-env.

Used by fetch_video_api.py (pool/feed enrichment) and fetch_metadata_bulk.py
(the 261K missing-metadata backfill). Design constraints:

  * API key ONLY from the YT_API_KEY env var — never on disk, never in args.
  * `videos.list` with 50 ids/request = 1 quota unit per request.
  * Checkpoint JSONL: one line per REQUESTED id ({"yt_id", "found", ...fields}),
    so a rerun skips everything already fetched — safe to interrupt anytime.
  * Ids not returned by the API are recorded as found=false (deleted/private/
    terminated) — that absence is itself the churn-attribution signal.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

API_URL = "https://www.googleapis.com/youtube/v3/videos"
BATCH = 50


def require_key() -> str:
    key = os.environ.get("YT_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "YT_API_KEY is not set. Get a key (console.cloud.google.com → "
            "YouTube Data API v3) and run:\n"
            "    YT_API_KEY=... <this command>\n"
            "Nothing was fetched; rerun is safe (checkpointed).")
    return key


def load_checkpoint(path: Path) -> dict[str, dict]:
    done: dict[str, dict] = {}
    if path.exists():
        for line in path.open(encoding="utf-8"):
            if line.strip():
                rec = json.loads(line)
                done[rec["yt_id"]] = rec
    return done


def parse_item(item: dict) -> dict:
    sn = item.get("snippet", {})
    st = item.get("status", {})
    stats = item.get("statistics", {})
    return {
        "found": True,
        "channel_id": sn.get("channelId"),
        "channel_title": sn.get("channelTitle"),
        "published_at_api": sn.get("publishedAt"),
        "title_api": sn.get("title"),
        "default_audio_lang_api": sn.get("defaultAudioLanguage"),
        "privacy_status": st.get("privacyStatus"),
        "upload_status": st.get("uploadStatus"),
        "view_count": stats.get("viewCount"),
        "like_count": stats.get("likeCount"),
        "comment_count": stats.get("commentCount"),
    }


def fetch_videos(ids: list[str], key: str, checkpoint: Path,
                 parts: str = "snippet,status,statistics",
                 sleep: float = 0.1, quota_budget: int | None = None) -> dict[str, dict]:
    """Fetch all ids (resuming from checkpoint); returns {yt_id: record}."""
    done = load_checkpoint(checkpoint)
    todo = [i for i in ids if i not in done]
    n_req = (len(todo) + BATCH - 1) // BATCH
    print(f"      {len(done)} already in checkpoint, {len(todo)} to fetch "
          f"({n_req} requests = {n_req} quota units)")
    if quota_budget is not None and n_req > quota_budget:
        todo = todo[:quota_budget * BATCH]
        print(f"      quota budget {quota_budget}: limiting this run to {len(todo)} ids")

    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    fetched_at = time.strftime("%Y-%m-%d")
    with checkpoint.open("a", encoding="utf-8") as out:
        for b in range(0, len(todo), BATCH):
            chunk = todo[b:b + BATCH]
            r = requests.get(API_URL, params={
                "part": parts, "id": ",".join(chunk),
                "maxResults": BATCH, "key": key}, timeout=30)
            if r.status_code == 403 and "quota" in r.text.lower():
                print(f"      ✗ quota exhausted after {b} ids this run — "
                      "checkpoint saved, rerun tomorrow")
                break
            r.raise_for_status()
            returned = {it["id"]: it for it in r.json().get("items", [])}
            for vid in chunk:
                rec = {"yt_id": vid, "fetched_at": fetched_at}
                rec.update(parse_item(returned[vid]) if vid in returned
                           else {"found": False})
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                done[vid] = rec
            if (b // BATCH) % 20 == 0:
                print(f"      … {b + len(chunk)}/{len(todo)}", file=sys.stderr)
            time.sleep(sleep)
    return done
