#!/usr/bin/env bash
# Download 18+ months of 1m data for SPY and QQQ via Polygon.io
#
# Prerequisites:
#   export POLYGON_API_KEY="your_key_here"
#
# Usage:
#   bash backend/scripts/download_polygon_18m.sh
#
# Output:
#   data/historical/1m/SPY.parquet  (merged jan 2024 — nov 2025)
#   data/historical/1m/QQQ.parquet  (merged jan 2024 — nov 2025)
#
# The script downloads jan 2024 — may 2025 as a new chunk, then merges
# with the existing jun—nov 2025 data already in the parquet files.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT/backend"

if [ -z "${POLYGON_API_KEY:-}" ]; then
    echo "ERROR: POLYGON_API_KEY env var is required."
    echo "  export POLYGON_API_KEY=\"your_key_here\""
    exit 1
fi

DATA_DIR="$REPO_ROOT/data/historical/1m"
CHUNKS_DIR="$DATA_DIR/chunks_polygon"
mkdir -p "$CHUNKS_DIR"

# Date ranges: download jan 2024 — may 2025 (existing data starts jun 2025)
START="2024-01-02"
END="2025-06-01"

# Polygon free tier: 5 calls/min. Window of 30 days = ~18 windows per symbol.
# With 12s delay per page, stays well within limits.
WINDOW_DAYS=30
RATE_DELAY=12.0

for SYMBOL in SPY QQQ; do
    CHUNK_OUT="$CHUNKS_DIR/${SYMBOL}_polygon_2024_2025.parquet"
    FINAL_OUT="$DATA_DIR/${SYMBOL}.parquet"
    BACKUP="$DATA_DIR/${SYMBOL}.parquet.bak_pre_merge"

    echo ""
    echo "========================================"
    echo "  Downloading $SYMBOL ($START → $END)"
    echo "========================================"

    python -m scripts.download_intraday_windowed \
        --provider polygon \
        --symbol "$SYMBOL" \
        --start "$START" \
        --end "$END" \
        --window-days "$WINDOW_DAYS" \
        --out "$CHUNK_OUT" \
        --retries 5 \
        --backoff-seconds 15 \
        --polygon-per-page-delay-seconds "$RATE_DELAY" \
        --polygon-rate-limit-sleep-seconds 65 \
        --verbose

    if [ ! -f "$CHUNK_OUT" ]; then
        echo "ERROR: Download failed for $SYMBOL — chunk not created."
        exit 1
    fi

    # Backup existing file
    if [ -f "$FINAL_OUT" ]; then
        cp "$FINAL_OUT" "$BACKUP"
        echo "  Backed up existing $FINAL_OUT"
    fi

    # Merge chunk with existing data
    echo "  Merging $SYMBOL data..."
    python -c "
import pandas as pd
import sys

chunk = pd.read_parquet('$CHUNK_OUT')
existing = pd.read_parquet('$FINAL_OUT') if '$FINAL_OUT' != '' else pd.DataFrame()

# Normalize both to same format
for df in [chunk, existing]:
    if not df.empty:
        if isinstance(df.index, pd.DatetimeIndex):
            if df.index.name != 'datetime':
                df.index.name = 'datetime'
        elif 'datetime' in df.columns:
            df.set_index('datetime', inplace=True)

# Concatenate, sort, dedupe
if existing.empty:
    merged = chunk
    if 'datetime' in merged.columns:
        merged.set_index('datetime', inplace=True)
else:
    merged = pd.concat([chunk if isinstance(chunk.index, pd.DatetimeIndex) else chunk.set_index('datetime'),
                         existing])
    merged = merged.sort_index()
    merged = merged[~merged.index.duplicated(keep='first')]

# Keep only OHLCV
merged = merged[['open', 'high', 'low', 'close', 'volume']]
merged.index.name = 'datetime'

print(f'  Merged: {len(merged)} rows, {merged.index.min()} → {merged.index.max()}')
merged.to_parquet('$FINAL_OUT')
print(f'  Wrote: $FINAL_OUT')
"

    echo "  Done: $SYMBOL"
done

echo ""
echo "========================================"
echo "  Download complete!"
echo "  Run data quality audit:"
echo "    cd backend && python -m scripts.download_intraday_windowed --provider polygon --symbol SPY --start 2024-01-02 --end 2025-12-01 --window-days 30 --out /dev/null --verbose"
echo "  Or check directly:"
echo "    python -c \"import pandas as pd; df=pd.read_parquet('data/historical/1m/SPY.parquet'); print(len(df), df.index.min(), df.index.max())\""
echo "========================================"
