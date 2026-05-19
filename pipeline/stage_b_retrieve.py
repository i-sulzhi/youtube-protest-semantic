"""Stage B — anchor-based retrieval over the LanceDB index.

Queries the embedded subset with multiple natural-language anchors, one per
political-context cluster. Reports top-K results per anchor and produces:
- a per-anchor results CSV (top 100 per anchor),
- an aggregate "newly surfaced videos" CSV — videos that were retrieved by
  at least one anchor but contain no surface protest keyword.

Usage:
  python v2_stage_b_retrieve.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import lancedb
from sentence_transformers import SentenceTransformer


def _to_bool(s: pd.Series) -> pd.Series:
    """Robust boolean parse — works whether the column is bool, int, or string."""
    if s.dtype == bool:
        return s.fillna(False)
    return s.astype(str).str.lower().isin(["true", "1"])


ANCHORS = {
    "BY-2020-protest":
        "массовые мирные протесты в Беларуси против фальсификации президентских "
        "выборов 2020 года, против Александра Лукашенко, в Минске и других городах, "
        "марши, аресты, Тихановская, забастовки, бело-красно-белый флаг",
    "RU-antiwar-2022":
        "антивоенные акции и протесты в России против войны в Украине в 2022 году, "
        "Москва, Санкт-Петербург, задержания, российская оппозиция, митинги против "
        "войны, Putin protest",
    "RU-Navalny":
        "протесты в поддержку Алексея Навального, акции против ареста Навального, "
        "Свободу Навальному, январь 2021, антикоррупционные митинги",
    "RU-mobilisation-2022":
        "протесты против мобилизации в России осенью 2022 года, бегство от мобилизации, "
        "митинги против частичной мобилизации, отказ от службы",
    "UA-Maidan-2014":
        "Революция гідності, Євромайдан, Майдан 2013-2014, протесты в Киеве против "
        "Януковича, Небесная сотня, Революция достоинства",
    "UA-current-protest":
        "протесты на Украине во время войны, акции в поддержку военных, протесты "
        "против коррупции, митинги в Киеве",
    "general-protest-action":
        "уличный протест, демонстрация, акция протеста, митинг, забастовка, "
        "столкновения с полицией, задержания на протесте",
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--lancedb", default="outputs/v2_lancedb")
    p.add_argument("--table",   default="videos")
    p.add_argument("--model",   default="intfloat/multilingual-e5-large")
    p.add_argument("--top-k",   type=int, default=100)
    p.add_argument("--device",  default="mps")
    p.add_argument("--out-dir", default="outputs/retrieval")
    return p.parse_args()


def main():
    args = parse_args()
    Path(args.out_dir).mkdir(parents=True, exist_ok=True)

    print(f"[B.1] Connecting to LanceDB at {args.lancedb}/{args.table}")
    db = lancedb.connect(args.lancedb)
    tbl = db.open_table(args.table)
    print(f"      table size: {len(tbl):,} rows")

    print(f"\n[B.2] Loading encoder: {args.model}")
    model = SentenceTransformer(args.model, device=args.device)
    model.half()

    # Encode all anchors at once
    print(f"\n[B.3] Encoding {len(ANCHORS)} anchor queries...")
    anchor_keys = list(ANCHORS.keys())
    queries = ["query: " + ANCHORS[k] for k in anchor_keys]
    qvecs = model.encode(queries, normalize_embeddings=True, convert_to_numpy=True).astype(np.float16)

    # Per-anchor retrieval.
    # LanceDB's default metric is L2² (Euclidean squared); we explicitly
    # request cosine so _distance = 1 - cos_sim regardless of how the table
    # was created. Without this, "similarity = 1 - _distance" silently
    # returns 2*cos_sim - 1 (linear monotonic transform of cos_sim, so
    # ranking is still correct, but the absolute numbers are off by ~0.13).
    all_hits = []
    for key, qv in zip(anchor_keys, qvecs):
        hits = (tbl.search(qv).metric("cosine").limit(args.top_k)
                .select(["YT_ID","TITLE","DESCRIPTION","DEFAULT_AUDIO_LANG",
                         "PUBLISHED_AT","country_combo","protest_anywhere",
                         "protest_in_title","protest_in_desc","dur_sec","feed_text"])
                .to_pandas())
        hits.insert(0, "anchor", key)
        hits["similarity"] = 1 - hits["_distance"]
        hits = hits.drop(columns=["_distance"])
        all_hits.append(hits)
        print(f"      {key:25s} top-1 cos_sim={hits.iloc[0]['similarity']:.3f}  "
              f"% protest_anywhere={100*hits['protest_anywhere'].mean():.1f}%")

    full = pd.concat(all_hits, ignore_index=True)
    out_dir = Path(args.out_dir)
    out_csv = out_dir / "topk_per_anchor.csv"
    full.to_csv(out_csv, index=False)
    print(f"\n      wrote {out_csv} ({len(full):,} rows)")

    # Aggregate: newly surfaced videos (anchor-retrieved AND no surface protest keyword)
    print(f"\n[B.4] Newly-surfaced analysis (anchor-retrieved AND no protest keyword)")
    full["protest_anywhere_bool"] = _to_bool(full["protest_anywhere"])
    newly = full[~full["protest_anywhere_bool"]].copy()
    newly_dedup = newly.sort_values("similarity", ascending=False).drop_duplicates(subset=["YT_ID"])
    print(f"      total anchor-retrieved (deduped): {full['YT_ID'].nunique():,}")
    print(f"      retrieved AND has protest keyword: {full[full['protest_anywhere_bool']]['YT_ID'].nunique():,}")
    print(f"      retrieved AND no protest keyword (NEWLY SURFACED): {newly_dedup['YT_ID'].nunique():,}")

    out_new = out_dir / "newly_surfaced.csv"
    newly_dedup.to_csv(out_new, index=False)
    print(f"      wrote {out_new}")

    # Per-anchor breakdown
    print(f"\n[B.5] Per-anchor newly-surfaced rate:")
    for key in anchor_keys:
        sub = full[full["anchor"] == key]
        new_in_anchor = sub[~sub["protest_anywhere_bool"]]
        print(f"      {key:25s}  newly={len(new_in_anchor):3d}/{len(sub):3d}  "
              f"({100*len(new_in_anchor)/len(sub):.1f}%)")


if __name__ == "__main__":
    main()
