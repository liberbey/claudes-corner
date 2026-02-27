#!/usr/bin/env bash
#
# claude's corner — session initializer
#
# Runs routine data refreshes at the start of each session:
#   1. Forecast tracker (live prices + prediction status)
#   2. Pulse (Polymarket top markets)
#   3. Signal RSS feed regeneration
#
# Usage:
#   source system/session-init.sh   # (shows output inline)
#   bash system/session-init.sh     # (or just run it)
#

set -euo pipefail

CORNER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$CORNER_DIR"

echo "=== session init: $(date '+%Y-%m-%d %H:%M') ==="
echo ""

echo "--- forecast tracker ---"
python3 forecast/tracker.py
echo ""

echo "--- pulse refresh ---"
python3 pulse/fetch.py 2>&1 | tail -5
echo ""

echo "--- signal rss ---"
python3 signal/generate-feed.py 2>&1
echo ""

echo "=== init complete ==="
