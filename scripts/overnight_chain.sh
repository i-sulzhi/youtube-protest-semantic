#!/usr/bin/env bash
# overnight_chain.sh
#
# Orchestrates the e5-large overnight rerun (Stages B and C, after Stage A
# is already running or has finished):
#   1. Wait for the running Stage A (PID in /tmp/embed_large.pid) to finish.
#   2. Run Stage B retrieval against table 'videos_e5large'
#       → outputs/retrieval_e5large/
#   3. Run Stage C polysemy clustering against the same table
#       → outputs/polysemy_e5large/
#
# Logs everything to /tmp/embed_large_chain.log
# Sends a desktop notification (macOS osascript) on completion.
#
# Invoke from the project root:  bash scripts/overnight_chain.sh

set -u
LOG=/tmp/embed_large_chain.log
PID_FILE=/tmp/embed_large.pid
# Project root is the parent of the directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV=$PROJECT/.venv_v2/bin/python

cd "$PROJECT"

echo "[chain] $(date)  starting orchestration" | tee -a "$LOG"

# 1) Wait for Stage A
if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE")
  echo "[chain] waiting for Stage A (PID $PID)" | tee -a "$LOG"
  while kill -0 "$PID" 2>/dev/null; do
    sleep 60
  done
  echo "[chain] $(date)  Stage A finished" | tee -a "$LOG"
else
  echo "[chain] no PID file; assuming Stage A already done" | tee -a "$LOG"
fi

# Sanity-check: table exists
"$VENV" -c "
import lancedb
db = lancedb.connect('outputs/v2_lancedb')
tables = db.table_names()
assert 'videos_e5large' in tables, f'videos_e5large missing — got {tables}'
n = len(db.open_table('videos_e5large'))
print(f'videos_e5large rows: {n}')
" 2>&1 | tee -a "$LOG"

# 2) Stage B
echo "[chain] $(date)  starting Stage B" | tee -a "$LOG"
"$VENV" pipeline/stage_b_retrieve.py \
  --model intfloat/multilingual-e5-large \
  --table videos_e5large \
  --out-dir outputs/retrieval_e5large \
  2>&1 | tee -a "$LOG"
echo "[chain] $(date)  Stage B finished" | tee -a "$LOG"

# 3) Stage C
echo "[chain] $(date)  starting Stage C" | tee -a "$LOG"
"$VENV" pipeline/stage_c_polysemy.py \
  --table videos_e5large \
  --out-dir outputs/polysemy_e5large \
  2>&1 | tee -a "$LOG"
echo "[chain] $(date)  Stage C finished" | tee -a "$LOG"

echo "[chain] $(date)  ALL DONE" | tee -a "$LOG"

# Desktop notification (macOS)
osascript -e 'display notification "v2 e5-large pipeline finished — check outputs/retrieval_e5large and outputs/polysemy_e5large" with title "Protest tags v2"' 2>/dev/null || true
