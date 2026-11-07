"""Generic ad-hoc slicer over the master dataset — any question in one command.

The escape hatch for analytical questions that don't deserve a module yet:
filter (pandas query syntax) → group → aggregate → sort → print/save.

Examples (run from project root):
  # gate survival by country among pool videos
  .venv_v2/bin/python analytics/slice.py --where "in_pool" \
      --by country_combo --agg "in_gated_index:mean,YT_ID:count"

  # median views of direct vs absent videos per anchor
  .venv_v2/bin/python analytics/slice.py --where "relevance_llm.notna()" \
      --by "primary_anchor,relevance_llm" --agg "views_total:median"

  # do tags-era videos with captions survive the gate more often?
  .venv_v2/bin/python analytics/slice.py --where "in_pool" \
      --by has_captions --agg "in_gated_index:mean,velocity_d7_z:mean,YT_ID:count"

  # top channels inside the gated index
  .venv_v2/bin/python analytics/slice.py --where "in_gated_index" \
      --by channel_proxy --agg "YT_ID:count" --sort "YT_ID_count" --top 15
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.lib import load_master  # noqa: E402


def parse_args():
    p = argparse.ArgumentParser(
        description="Ad-hoc slice of the master dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("--where", default=None, help="pandas query, e.g. \"in_pool\"")
    p.add_argument("--by", default=None, help="comma-separated group columns")
    p.add_argument("--agg", default="YT_ID:count",
                   help="col:func[,col:func…]; funcs: count,mean,median,sum,std,nunique,min,max")
    p.add_argument("--sort", default=None, help="column of the result to sort by (desc)")
    p.add_argument("--top", type=int, default=50)
    p.add_argument("--out", default=None, help="optional CSV to save the result")
    p.add_argument("--columns", action="store_true", help="list master columns and exit")
    return p.parse_args()


def main():
    a = parse_args()
    m = load_master()
    if a.columns:
        for c in m.columns:
            print(f"  {c:28s} {m[c].dtype}  non-null {m[c].notna().sum():,}")
        return
    if a.where:
        m = m.query(a.where, engine="python")
        print(f"-- where {a.where!r}: {len(m):,} rows")
    aggs = {}
    for part in a.agg.split(","):
        col, fn = part.split(":")
        aggs[f"{col}_{fn}"] = (col.strip(), fn.strip())
    if a.by:
        by = [c.strip() for c in a.by.split(",")]
        res = m.groupby(by, dropna=False).agg(**aggs).reset_index()
    else:
        res = m.agg({v[0]: v[1] for v in aggs.values()}).to_frame().T
    if a.sort and a.sort in res.columns:
        res = res.sort_values(a.sort, ascending=False)
    res = res.head(a.top)
    with __import__("pandas").option_context("display.width", 200,
                                             "display.max_columns", 50):
        print(res.to_string(index=False))
    if a.out:
        res.to_csv(a.out, index=False)
        print(f"-- saved {a.out}")


if __name__ == "__main__":
    main()
