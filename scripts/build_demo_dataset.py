"""Build a small reproducer dataset under data/demo/.

Output:
  data/demo/yt_ids.txt       canonical list of 200 YT_IDs (one per line)
  data/demo/lancedb/         LanceDB with two tables (videos_demo + videos_demo_large)
                             containing only vectors + metadata (NO TITLE,
                             DESCRIPTION or feed_text — those columns are
                             blanked to empty strings to preserve schema
                             without redistributing YouTube content).

The selection is stratified by country_combo and balanced so that roughly
half of the videos carry a surface protest keyword (Stage C input) and
roughly half do not (Stage B newly-surfaced metric).

Run from the project root:
    .venv_v2/bin/python scripts/build_demo_dataset.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import lancedb


SEED          = 42
N_DEMO        = 200
SRC_LANCEDB   = "outputs/v2_lancedb"
DEMO_DIR      = Path("data/demo")
DEMO_LANCEDB  = DEMO_DIR / "lancedb"
DEMO_IDS_TXT  = DEMO_DIR / "yt_ids.txt"


# Quotas per country_combo (proportional + minimum coverage for the smaller groups)
QUOTA = {
    "R":      50,
    "UR":     45,
    "B":      35,
    "U":      30,
    "BR":     10,
    "BUR":    10,
    "BU":     10,
    "(none)": 10,
}
assert sum(QUOTA.values()) == N_DEMO, "quotas must sum to N_DEMO"


def select_yt_ids(meta: pd.DataFrame) -> list[str]:
    """Stratified sample: for each country combo, half protest_anywhere=True
    and half False (rounded). Seeded for reproducibility."""
    rng = np.random.default_rng(SEED)
    chosen = []
    m = meta.copy()
    m["country_combo"] = m["country_combo"].fillna("(none)")

    for combo, k in QUOTA.items():
        pool = m[m["country_combo"] == combo]
        if pool.empty:
            print(f"  WARN: no rows for {combo!r} — skipping {k}")
            continue
        # Aim for 50/50 protest_anywhere where possible
        k_true  = min(k // 2, (pool["protest_anywhere"] == True).sum())
        k_false = k - k_true
        if (pool["protest_anywhere"] == False).sum() < k_false:
            # Not enough False; fall back to whatever pool can offer
            k_false = (pool["protest_anywhere"] == False).sum()
            k_true  = min(k - k_false, (pool["protest_anywhere"] == True).sum())

        ids_true  = (pool[pool["protest_anywhere"] == True]["YT_ID"]
                     .sample(n=k_true, random_state=int(rng.integers(0, 2**31))))
        ids_false = (pool[pool["protest_anywhere"] == False]["YT_ID"]
                     .sample(n=k_false, random_state=int(rng.integers(0, 2**31))))
        sub = pd.concat([ids_true, ids_false]).tolist()
        chosen.extend(sub)
        print(f"  {combo:8s}  protest+={k_true:>2d}  protest-={k_false:>2d}")

    return sorted(set(chosen))


def build_demo_table(src_db, src_table_name: str,
                     dst_db, dst_table_name: str,
                     yt_ids: list[str]):
    """Read the source table, filter to YT_IDs, blank out copyright-sensitive
    text columns, and write to the destination table."""
    src = src_db.open_table(src_table_name)
    df = src.search().select(
        ["YT_ID","vector","PUBLISHED_AT","DEFAULT_AUDIO_LANG","DURATION",
         "dur_sec","LIVE_BROADCAST","TITLE","DESCRIPTION","feed_text",
         "meaningful_len","n_urls","protest_anywhere","protest_in_title",
         "protest_in_desc","BY","UA","RU","country_combo"]
    ).limit(len(src)).to_pandas()

    df = df[df["YT_ID"].isin(set(yt_ids))].copy()
    # Replace copyrighted free-text columns with the empty string, keeping
    # schema (so Stage B's column selection still works) but redistributing
    # nothing.
    for col in ("TITLE", "DESCRIPTION", "feed_text"):
        df[col] = ""
    # Drop any internal _distance column from the search projection
    df = df.drop(columns=[c for c in df.columns if c.startswith("_")])

    if dst_table_name in dst_db.list_tables():
        dst_db.drop_table(dst_table_name)
    dst_db.create_table(dst_table_name, data=df, mode="overwrite")
    print(f"  wrote table {dst_table_name!r} ({len(df)} rows, "
          f"{df['protest_anywhere'].sum()} with protest keyword)")


def main():
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    if DEMO_LANCEDB.exists():
        shutil.rmtree(DEMO_LANCEDB)

    print(f"[1/4] Reading metadata from {SRC_LANCEDB}/videos")
    src_db = lancedb.connect(SRC_LANCEDB)
    full = src_db.open_table("videos")
    meta = full.search().select(["YT_ID","country_combo","protest_anywhere"]) \
                       .limit(len(full)).to_pandas()
    print(f"      {len(meta):,} videos in source table")

    print(f"\n[2/4] Stratified sample of {N_DEMO} videos (seed={SEED})")
    yt_ids = select_yt_ids(meta)
    DEMO_IDS_TXT.write_text("\n".join(yt_ids) + "\n")
    print(f"      {len(yt_ids)} YT_IDs written to {DEMO_IDS_TXT}")

    print(f"\n[3/4] Building demo LanceDB at {DEMO_LANCEDB}")
    dst_db = lancedb.connect(str(DEMO_LANCEDB))
    build_demo_table(src_db, "videos",          dst_db, "videos_demo",       yt_ids)
    build_demo_table(src_db, "videos_e5large",  dst_db, "videos_demo_large", yt_ids)

    print(f"\n[4/4] On-disk size")
    total = sum(p.stat().st_size for p in DEMO_LANCEDB.rglob("*") if p.is_file())
    print(f"      {total/1024/1024:.2f} MB")


if __name__ == "__main__":
    main()
