"""Block 5.1 — three ways the corpus "knows" protest (Task-5 analytics core).

From the gate-`direct` seeds, builds three candidate sets over the 21,710 feed
and measures their overlap/complementarity:

  (a) semantic   — the 4-way retrieval pool (what embeddings found);
  (b) hypergraph — videos sharing ≥k search-discovery pools (`(term, DATE)`
                   hyperedges, outputs/hypergraph/incidence.csv) with ≥1 seed;
  (c) channel    — videos by protest-heavy channels
                   (outputs/channel_expansion_candidates.csv, Block 1.3).

For each modality: size, overlap with the labelled pool, precision proxy
(share of its pool-overlap items the gate labels relevant), gold hits; then
pairwise Jaccard and unique contributions. The publishable claim shape:
"the modalities are complementary, not redundant".

Runs NOW. Inputs improve later (API channels → better (c); bigger pool → (a)).

Run from project root:
    .venv_v2/bin/python scripts/stage_f_modalities.py
"""
from __future__ import annotations

import argparse
import glob
import json
from itertools import combinations
from pathlib import Path

import pandas as pd


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--gated", default="outputs/stage_e/protest_index_gated.csv")
    p.add_argument("--index", default="outputs/stage_e/protest_index.csv")
    p.add_argument("--pred-glob",
                   default="outputs/stage_e/relevance_pred/claude_chunk*.jsonl")
    p.add_argument("--incidence", default="outputs/hypergraph/incidence.csv")
    p.add_argument("--channel-cands",
                   default="outputs/channel_expansion_candidates.csv")
    p.add_argument("--gold", default="mini_study/coding_layer2.csv")
    p.add_argument("--min-shared-edges", type=int, default=3,
                   help="hypergraph: min discovery pools shared with a seed")
    p.add_argument("--out-dir", default="outputs/stage_f")
    return p.parse_args()


def load_labels(pattern: str) -> pd.Series:
    rows = []
    for f in sorted(glob.glob(pattern)):
        for line in open(f, encoding="utf-8"):
            if line.strip():
                rows.append(json.loads(line))
    df = pd.DataFrame(rows).drop_duplicates("yt_id", keep="first")
    return df.set_index("yt_id")["protest_relevance"]


def main():
    a = parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    gated = pd.read_csv(a.gated)
    seeds = set(gated.loc[gated["relevance_llm"] == "direct", "YT_ID"])
    labels = load_labels(a.pred_glob)
    semantic = set(pd.read_csv(a.index, usecols=["YT_ID"])["YT_ID"])
    print(f"[1/4] Seeds: {len(seeds)} gate-direct; semantic pool {len(semantic)}")

    # --- hypergraph expansion ---------------------------------------------- #
    print(f"[2/4] Hypergraph expansion (incidence ≥{a.min_shared_edges} shared "
          "pools with a seed) …")
    inc = pd.read_csv(a.incidence, usecols=["edge_id", "YT_ID"])
    seed_edges = set(inc.loc[inc["YT_ID"].isin(seeds), "edge_id"])
    on_seed_edges = inc[inc["edge_id"].isin(seed_edges)]
    shared = on_seed_edges.groupby("YT_ID")["edge_id"].nunique()
    hyper = set(shared[shared >= a.min_shared_edges].index) - seeds
    print(f"      {len(seed_edges)} seed pools → {len(hyper):,} expansion videos")

    # threshold sweep: size + precision proxy at each k (the analysis knob)
    sweep_rows = []
    lbl = load_labels(a.pred_glob)
    for k in [2, 3, 5, 10, 20, 50]:
        sk = set(shared[shared >= k].index) - seeds
        in_pool_k = sk & set(lbl.index)
        rel = sum(lbl.get(v) in ("direct", "indirect") for v in in_pool_k)
        sweep_rows.append((k, len(sk), len(in_pool_k),
                           round(rel / len(in_pool_k), 3) if in_pool_k else None))
    print("      sweep k → size/precision-proxy: "
          + "; ".join(f"k={k}: {n:,} ({p})" for k, n, _, p in sweep_rows))

    # --- channel expansion --------------------------------------------------#
    if Path(a.channel_cands).exists():
        channel = set(pd.read_csv(a.channel_cands, usecols=["YT_ID"])["YT_ID"])
    else:
        channel = set()
        print(f"      ⚠ {a.channel_cands} missing — run channel_expand_pool.py "
              "first; channel modality empty this run")
    print(f"[3/4] Channel expansion: {len(channel)} videos")

    sets = {"semantic": semantic, "hypergraph": hyper, "channel": channel}
    gold = pd.read_csv(a.gold)
    gold_rel = set(gold.loc[gold["protest_relevance"] != "absent", "yt_id"])

    def describe(name, s):
        in_pool = s & set(labels.index)
        rel = sum(labels.get(v) in ("direct", "indirect") for v in in_pool)
        prec = rel / len(in_pool) if in_pool else float("nan")
        return {"modality": name, "size": len(s),
                "in_labelled_pool": len(in_pool),
                "pool_precision": round(prec, 3),
                "gold_relevant_hits": len(s & gold_rel)}

    desc = pd.DataFrame([describe(k, v) for k, v in sets.items()])
    print(desc.to_string(index=False))

    rows_j = []
    for (n1, s1), (n2, s2) in combinations(sets.items(), 2):
        inter = len(s1 & s2)
        union = len(s1 | s2) or 1
        rows_j.append((f"{n1} × {n2}", inter, round(inter / union, 3)))
    uniq = {n: len(s - set.union(*(v for k, v in sets.items() if k != n)))
            for n, s in sets.items() if s}

    # per-video membership table for downstream analysis
    allv = sorted(set.union(*sets.values()))
    mem = pd.DataFrame({"YT_ID": allv})
    for n, s in sets.items():
        mem[n] = mem["YT_ID"].isin(s)
    mem["llm_label"] = mem["YT_ID"].map(labels)
    mem.to_csv(out / "modality_sets.csv", index=False)

    L = ["# Stage F — three ways the corpus knows protest", "",
         f"Seeds: {len(seeds)} gate-direct videos. Hypergraph threshold: "
         f"≥{a.min_shared_edges} shared discovery pools.", "",
         "## Modalities", "",
         "| modality | size | in labelled pool | pool precision | gold relevant hits |",
         "|---|---:|---:|---:|---:|",
         *[f"| {r.modality} | {r.size:,} | {r.in_labelled_pool} | "
           f"{r.pool_precision} | {r.gold_relevant_hits} |"
           for r in desc.itertuples()], "",
         "`pool_precision` = share of the modality's labelled-pool overlap the "
         "gate calls relevant (a proxy — only the semantic pool is fully "
         "labelled; label a sample of the others before quoting).", "",
         "## Hypergraph threshold sweep (pick k by precision/size trade-off)", "",
         "| k (shared pools) | expansion size | in labelled pool | precision proxy |",
         "|---:|---:|---:|---:|",
         *[f"| {k} | {n:,} | {ip} | {p} |" for k, n, ip, p in sweep_rows], "",
         "## Overlap", "",
         "| pair | ∩ | Jaccard |", "|---|---:|---:|",
         *[f"| {p} | {i} | {j} |" for p, i, j in rows_j], "",
         "Unique contributions: " +
         ", ".join(f"{k} {v:,}" for k, v in uniq.items()), "",
         "Membership table: `modality_sets.csv`. Next steps: LLM-label a "
         "random sample of hypergraph/channel-only candidates to turn "
         "pool_precision into real precision; rerun with API channels.",
         ]
    (out / "modalities_report.md").write_text("\n".join(L), encoding="utf-8")
    print(f"[4/4] wrote {out/'modalities_report.md'} + modality_sets.csv")


if __name__ == "__main__":
    main()
