# Demo dataset (200 videos)

This directory holds a small, reproducible slice of the v2 corpus that
makes the pipeline runnable end-to-end without access to the full
*YouTube* metadata fetch. It exists so that a reader can verify the
pipeline on their own machine in under a minute.

## What is included

- **`yt_ids.txt`** — 200 canonical YouTube video IDs, one per line,
  stratified by country combination (Belarus, Russia, Ukraine, and the
  cross combinations) and balanced so that approximately half the
  videos contain a surface protest keyword.
- **`lancedb/`** — a small LanceDB store with two tables,
  `videos_demo` (`e5-small`, 384-dim) and `videos_demo_large`
  (`e5-large`, 1024-dim). Each row holds the video's embedding vector
  and aggregate metadata (language, country combo, publication date,
  protest-keyword flags). About 1.1 MB on disk.

## What is **not** included

The `TITLE`, `DESCRIPTION` and `feed_text` columns are present in the
schema but blanked to the empty string. The repository does not
redistribute *YouTube* video text under either creator copyright or
the *YouTube* API Services Terms of Service. To inspect the
underlying titles and descriptions:

1. Take the 200 IDs from `yt_ids.txt`.
2. Fetch their `snippet` parts via the *YouTube* Data API v3
   (`videos.list?part=snippet&id=...`). The IDs are public; the API
   call returns the same title and description any user sees in the
   *YouTube* UI.

## How to use the demo

From the project root, with `.venv` activated:

```bash
# Stage B — anchor retrieval (top-30 per anchor on demo)
python pipeline/stage_b_retrieve.py \
    --lancedb data/demo/lancedb --table videos_demo \
    --model intfloat/multilingual-e5-small \
    --top-k 30 --out-dir outputs/demo_retrieval

python pipeline/stage_b_retrieve.py \
    --lancedb data/demo/lancedb --table videos_demo_large \
    --model intfloat/multilingual-e5-large \
    --top-k 30 --out-dir outputs/demo_retrieval_large

# Stage C — polysemy (k=4 instead of k=8 for the smaller sample)
python pipeline/stage_c_polysemy.py \
    --lancedb data/demo/lancedb --table videos_demo \
    --n-clusters 4 --out-dir outputs/demo_polysemy

# Stage D — ensemble fusion
python pipeline/stage_d_ensemble.py \
    --small-csv outputs/demo_retrieval/topk_per_anchor.csv \
    --large-csv outputs/demo_retrieval_large/topk_per_anchor.csv \
    --top-k 30 --out-dir outputs/demo_ensemble
```

End-to-end runtime: roughly 30 seconds, dominated by the one-off
download of the encoder weights from Hugging Face.

## What the demo cannot show

- **Stage A.** The demo ships pre-computed vectors, so the embedding
  step is not exercised. To rerun Stage A end-to-end, the original
  text content is required.
- **Polysemy structure at scale.** With only ~100 protest-mentioning
  videos, KMeans clusters at k=4 (or k=8) are illustrative rather
  than substantive. The full corpus has 2,034 protest-mentioning
  videos, and that is the sample size for the cluster-purity numbers
  reported in `notebooks/pipeline.ipynb`.
- **Newly-surfaced precision.** The 200-video sample is too narrow
  for the +60% UNION-fusion recall gain to manifest. On the full
  corpus the gain is substantial; on the demo it is small because
  both encoders agree on most candidates within such a constrained
  set.

The demo verifies *that* the pipeline runs; the substantive findings
require the full 21,710-video corpus.

## Reproducibility of the demo selection

The demo was generated with:

```bash
python scripts/build_demo_dataset.py
```

Stratification quotas and the random seed (`SEED = 42`) are inlined in
the script. Re-running it against the same source LanceDB will produce
the same 200 `YT_ID` set.
