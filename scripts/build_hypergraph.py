"""Build a search-discovery hypergraph for the v2 subset.

Per `docs/EXPORTS_ROADMAP.md` §8 (EXPORT 7). The reviewer of the manuscript
explicitly raised hypergraph methodology as a desideratum — this is a
direct reply.

Structure:
  - Vertices  = videos (v2 subset, 21,710)
  - Hyperedges = (canonical_search_term, DATE) pairs
  - An edge contains every video that appeared in that (term, day) pool
  - Edge weight = mean RANK of videos in the pool (lower = more visible)

The (term, DATE) hyperedge is *genuinely* many-to-many: each search day
surfaced ≤500 videos at once and each video appeared across many
(term, day) pools over years. A bipartite representation loses the
per-event grouping; a regular weighted graph loses the *co-presence*
structure (videos that consistently appear in the same pool).

We compute three broker-style centrality measures per video:
  - `hyperedge_degree`   — number of distinct (term, day) edges
  - `unique_terms`       — number of distinct canonical terms (≤6)
  - `mean_edge_size`     — average pool size of the edges this video sits in

Plus per-edge: `n_videos`, `mean_rank`, `min_rank`.

Outputs (under outputs/):
  hypergraph_incidence.csv     edge_id, YT_ID, rank          (long format, ~1.6M rows)
  hypergraph_edges.csv         edge_id, term, date, n_videos, mean_rank, min_rank
  hypergraph_vertex_stats.csv  YT_ID, hyperedge_degree, unique_terms, mean_edge_size,
                                       broker_score
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pymysql

from canonical_tags import apply_synonyms, canonicalise, load_synonym_table


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--db-user",   default="sulzhytski")
    p.add_argument("--db-name",   default="metadata")
    p.add_argument("--db-socket", default="/tmp/mysql.sock")
    p.add_argument("--feed",      default="outputs/v2_feed_ready_with_tags.csv.gz")
    p.add_argument("--synonyms",  default="data/tag_synonyms.csv")
    p.add_argument("--out-dir",   default="outputs/hypergraph")
    p.add_argument("--skip-hnx",  action="store_true",
                   help="skip hypernetx centrality computation (faster smoke test)")
    return p.parse_args()


def fetch_rows(args, yt_ids: list[str]) -> pd.DataFrame:
    conn = pymysql.connect(user=args.db_user, database=args.db_name,
                           unix_socket=args.db_socket, charset="utf8mb4")
    with conn.cursor() as cur:
        cur.execute("CREATE TEMPORARY TABLE v2_ids (YT_ID VARCHAR(11) PRIMARY KEY)")
        cur.executemany("INSERT IGNORE INTO v2_ids VALUES (%s)",
                        [(y,) for y in yt_ids])
        cur.execute("""
            SELECT sr.YT_ID, sr.DATE, s.SEARCH_TERM, sr.RANK
            FROM SEARCH_RESULTS sr
            JOIN v2_ids v ON sr.YT_ID = v.YT_ID
            JOIN SEARCHES s
              ON s.DATE = sr.DATE AND s.SEARCH_ID = sr.SEARCH_ID
        """)
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=["YT_ID", "DATE", "SEARCH_TERM", "RANK"])
    df["DATE"] = pd.to_datetime(df["DATE"]).dt.date
    df["RANK"] = pd.to_numeric(df["RANK"], errors="coerce").astype("Int64")
    return df


def main():
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/6] Loading v2 feed: {args.feed}")
    feed = pd.read_csv(args.feed, usecols=["YT_ID"])
    print(f"      {len(feed):,} videos")

    print(f"\n[2/6] Loading synonyms and pulling search rows")
    synonyms = load_synonym_table(args.synonyms)
    sr = fetch_rows(args, feed["YT_ID"].tolist())
    sr["term_canon"] = (sr["SEARCH_TERM"].map(canonicalise)
                                          .map(lambda t: apply_synonyms(t, synonyms)))
    sr = sr.dropna(subset=["RANK"])
    print(f"      {len(sr):,} rows; {sr['term_canon'].nunique()} canonical terms")

    print(f"\n[3/6] Defining hyperedges = (canonical term, date) pairs")
    sr["edge_id"] = sr["term_canon"] + "|" + sr["DATE"].astype(str)
    n_edges = sr["edge_id"].nunique()
    n_verts = sr["YT_ID"].nunique()
    print(f"      hypergraph: {n_verts:,} vertices, {n_edges:,} hyperedges")

    # Incidence — long format, used by both vertex and edge aggregations.
    # Dedupe by (edge_id, YT_ID): a video can appear in the same
    # canonical edge via multiple raw SEARCH_TERMs on the same DATE
    # (e.g. `беларусь` and `belarus` both fold to edge `belarus|2020-09-23`).
    # That collision creates ~30K duplicate (edge, vertex) rows; the
    # bipartite hypergraph definition treats each video as either in or
    # out of an edge, so we keep the BEST rank — the most-visible
    # observation — per (edge, vertex) pair.
    incidence_raw = sr[["edge_id", "YT_ID", "RANK", "term_canon", "DATE"]].rename(
        columns={"RANK": "rank"})
    n_raw = len(incidence_raw)
    incidence = (incidence_raw.sort_values("rank")
                              .drop_duplicates(["edge_id", "YT_ID"], keep="first")
                              .reset_index(drop=True))
    incidence_path = out_dir / "incidence.csv"
    incidence.to_csv(incidence_path, index=False)
    n_dedup = n_raw - len(incidence)
    print(f"      wrote {incidence_path}  ({len(incidence):,} rows; "
          f"deduped {n_dedup:,} cross-term collisions)")

    print(f"\n[4/6] Edge-level stats")
    edges = (incidence.groupby(["edge_id", "term_canon", "DATE"])
                       .agg(n_videos=("YT_ID", "nunique"),
                            mean_rank=("rank", "mean"),
                            min_rank=("rank", "min"))
                       .reset_index())
    edges["mean_rank"] = edges["mean_rank"].round(1)
    edges_path = out_dir / "edges.csv"
    edges.to_csv(edges_path, index=False)
    print(f"      wrote {edges_path}  ({len(edges):,} rows)")
    print(f"      edge size:  median={int(edges['n_videos'].median())}, "
          f"p90={int(edges['n_videos'].quantile(0.9))}, max={int(edges['n_videos'].max())}")
    print(f"      mean_rank:  median={edges['mean_rank'].median():.1f}")

    print(f"\n[5/6] Vertex-level broker stats")
    # Hyperedge degree = how many (term, day) pools contain this video
    vert = (incidence.groupby("YT_ID")
                      .agg(hyperedge_degree=("edge_id", "nunique"),
                           unique_terms=("term_canon", "nunique"),
                           first_seen=("DATE", "min"),
                           last_seen=("DATE", "max"),
                           best_rank=("rank", "min"),
                           mean_rank=("rank", "mean"))
                      .reset_index())
    vert["mean_rank"] = vert["mean_rank"].round(1)

    # Mean size of the edges this vertex sits in — proxy for "in how crowded a
    # discovery pool does this video typically appear"
    edge_size = edges.set_index("edge_id")["n_videos"]
    vert_edge_sizes = (incidence.merge(edge_size.rename("edge_size"),
                                        left_on="edge_id", right_index=True)
                                 .groupby("YT_ID")["edge_size"]
                                 .mean().round(1))
    vert["mean_edge_size"] = vert["YT_ID"].map(vert_edge_sizes)

    # Broker score: reward many-edge + multi-term presence
    # (degree × unique_terms / mean_edge_size) — high = many pools, diverse
    # channels, and not lost in big pools. Scaled so max ~ 100.
    raw_score = (vert["hyperedge_degree"] * vert["unique_terms"]) / vert["mean_edge_size"]
    vert["broker_score"] = (100 * raw_score / raw_score.max()).round(2)

    vert = vert.sort_values("broker_score", ascending=False)
    vert_path = out_dir / "vertex_stats.csv"
    vert.to_csv(vert_path, index=False)
    print(f"      wrote {vert_path}  ({len(vert):,} rows)")
    print(f"      hyperedge_degree: median={int(vert['hyperedge_degree'].median())}, "
          f"p90={int(vert['hyperedge_degree'].quantile(0.9))}, max={int(vert['hyperedge_degree'].max())}")
    print(f"      unique_terms:     distribution {dict(vert['unique_terms'].value_counts().sort_index())}")

    if not args.skip_hnx:
        print(f"\n[6/6] hypernetx validation (vertex/edge counts)")
        import hypernetx as hnx
        # Build from edge→[YT_IDs] dict; faster than from incidence
        edge_dict = (incidence.groupby("edge_id")["YT_ID"]
                              .agg(list).to_dict())
        H = hnx.Hypergraph(edge_dict)
        print(f"      hnx graph: {len(H.nodes):,} nodes, {len(H.edges):,} edges")
        if len(H.nodes) != n_verts or len(H.edges) != n_edges:
            raise SystemExit(
                f"Inconsistency: pandas {n_verts}/{n_edges} vs hnx "
                f"{len(H.nodes)}/{len(H.edges)}"
            )
        print(f"      ✓ matches pandas counts")
    else:
        print(f"\n[6/6] hypernetx validation skipped (--skip-hnx)")

    print(f"\nTop 10 broker videos:")
    cols = ["YT_ID", "hyperedge_degree", "unique_terms",
            "mean_edge_size", "broker_score", "best_rank"]
    print(vert.head(10)[cols].to_string(index=False))


if __name__ == "__main__":
    main()
