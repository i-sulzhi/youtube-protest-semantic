"""Stage A — embed the 21,710-video text-ready subset and write to LanceDB.

Inputs:  outputs/v2_feed_ready.csv.gz   (produced by EDA_v2_text_ready.ipynb)
Output:  outputs/v2_lancedb/            (LanceDB table 'videos' with 1024-dim vectors)

Encoder: intfloat/multilingual-e5-large (560M params, 1024-dim, multilingual, fp16).
e5 input convention: prefix passages with "passage: " and queries with "query: ".

Approach:
- Load the feed-ready CSV
- Truncate feed_text to 2000 chars (keeps 99% of content; bounds 512-token window)
- Encode in batches on MPS, fp16
- Persist to LanceDB with all metadata for filtering at retrieval time
"""
from __future__ import annotations

import os, sys, time, gzip, argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import lancedb
import pyarrow as pa
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--feed-csv",  default="outputs/v2_feed_ready.csv.gz")
    p.add_argument("--lancedb",   default="outputs/v2_lancedb")
    p.add_argument("--table",     default="videos")
    p.add_argument("--model",     default="intfloat/multilingual-e5-large")
    p.add_argument("--batch",     type=int, default=16)
    p.add_argument("--max-chars", type=int, default=2000)
    p.add_argument("--limit",     type=int, default=None,
                   help="if set, embed only the first N rows (for smoke testing)")
    p.add_argument("--device",    default="mps")
    p.add_argument("--use-tags",  action="store_true",
                   help="if set, include the 'tags' column in feed_e5 "
                        "(requires --feed-csv pointing to an enriched feed)")
    return p.parse_args()


def load_feed(path: str, max_chars: int, use_tags: bool) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])
    # we wrote feed_text in the EDA notebook; truncate here
    df["feed_text"] = df["feed_text"].fillna("").str[:max_chars]

    if use_tags and "tags" in df.columns:
        # When tags are available, give them their own slice of the input
        # budget (e5 truncates beyond ~512 tokens ≈ 2000 chars in Cyrillic).
        # Shrink the description portion to 1500 chars and append up to
        # 500 chars of tags. Tags carry author-curated semantic labels and
        # are often denser signal than the boilerplate tail of descriptions.
        df["feed_text"] = df["feed_text"].str[:1500]
        df["tags"]      = df["tags"].fillna("").str[:500]
        df["feed_e5"]   = "passage: " + df["feed_text"] + " . теги: " + df["tags"]
        print(f"      feed_e5 includes tags: median total length "
              f"{int((df['feed_text'].str.len() + df['tags'].str.len()).median())} chars")
    else:
        # e5 expects "passage: " prefix for indexed text
        df["feed_e5"] = "passage: " + df["feed_text"]
        if "tags" not in df.columns:
            df["tags"] = ""

    return df


def main():
    args = parse_args()

    print(f"[A.1] Loading feed: {args.feed_csv}  (use_tags={args.use_tags})")
    df = load_feed(args.feed_csv, args.max_chars, args.use_tags)
    if args.limit:
        df = df.head(args.limit).copy()
    print(f"      rows: {len(df):,}")
    print(f"      text length quantiles after truncation:")
    L = df["feed_text"].str.len()
    print(f"        median {int(L.median())},  p90 {int(L.quantile(.9))},  max {int(L.max())}")

    print(f"\n[A.2] Loading encoder: {args.model}")
    t0 = time.time()
    model = SentenceTransformer(args.model, device=args.device)
    # cast to fp16 for speed/memory on MPS
    model.half()
    dim = model.get_sentence_embedding_dimension()
    print(f"      device={args.device}  dim={dim}  load_time={time.time()-t0:.1f}s")

    print(f"\n[A.3] Encoding {len(df):,} passages (batch={args.batch})...")
    t0 = time.time()
    vectors = model.encode(
        df["feed_e5"].tolist(),
        batch_size=args.batch,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,    # cosine = dot product after normalisation
    )
    elapsed = time.time() - t0
    print(f"      done in {elapsed:.1f}s  ({len(df) / elapsed:.1f} vec/s)")
    print(f"      vectors shape: {vectors.shape}  dtype={vectors.dtype}")

    # Convert to fp16 for storage
    vectors = vectors.astype(np.float16)

    print(f"\n[A.4] Writing to LanceDB at {args.lancedb}/{args.table}")
    Path(args.lancedb).mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(args.lancedb)

    # Build the row dicts in the order LanceDB expects
    out = pd.DataFrame({
        "YT_ID":              df["YT_ID"].values,
        "vector":             [v for v in vectors],   # one np.array per row
        "PUBLISHED_AT":       df["PUBLISHED_AT"].values,
        "DEFAULT_AUDIO_LANG": df.get("DEFAULT_AUDIO_LANG", pd.Series([""] * len(df))).fillna("").values,
        "DURATION":           df.get("DURATION", pd.Series([""] * len(df))).fillna("").values,
        "dur_sec":            pd.to_numeric(df.get("dur_sec", pd.Series([0]*len(df))), errors="coerce").fillna(0).astype(int).values,
        "LIVE_BROADCAST":     df.get("LIVE_BROADCAST", pd.Series([""] * len(df))).fillna("").values,
        "TITLE":              df["TITLE"].fillna("").values,
        "DESCRIPTION":        df["DESCRIPTION"].fillna("").values,
        "feed_text":          df["feed_text"].values,
        "meaningful_len":     pd.to_numeric(df.get("meaningful_len", pd.Series([0]*len(df))), errors="coerce").fillna(0).astype(int).values,
        "n_urls":             pd.to_numeric(df.get("n_urls", pd.Series([0]*len(df))), errors="coerce").fillna(0).astype(int).values,
        "protest_anywhere":   (df.get("protest_anywhere", pd.Series([False]*len(df))).astype(str).str.lower() == "true").values,
        "protest_in_title":   (df.get("protest_in_title", pd.Series([False]*len(df))).astype(str).str.lower() == "true").values,
        "protest_in_desc":    (df.get("protest_in_desc",  pd.Series([False]*len(df))).astype(str).str.lower() == "true").values,
        "BY":                 (df.get("BY", pd.Series([False]*len(df))).astype(str).str.lower() == "true").values,
        "UA":                 (df.get("UA", pd.Series([False]*len(df))).astype(str).str.lower() == "true").values,
        "RU":                 (df.get("RU", pd.Series([False]*len(df))).astype(str).str.lower() == "true").values,
        "country_combo":      df.get("country_combo", pd.Series(["(none)"] * len(df))).fillna("(none)").values,
        "tags":               df.get("tags", pd.Series([""] * len(df))).fillna("").values,
    })

    if args.table in db.table_names():
        print(f"      table '{args.table}' exists — overwriting")
        db.drop_table(args.table)

    tbl = db.create_table(args.table, data=out, mode="overwrite")
    print(f"      wrote {len(tbl):,} rows")

    print(f"\n[A.5] Storage size:")
    total = sum(p.stat().st_size for p in Path(args.lancedb).rglob("*") if p.is_file())
    print(f"      {total / 1024 / 1024:.1f} MB on disk")

    print("\nDone.")


if __name__ == "__main__":
    main()
