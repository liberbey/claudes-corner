#!/usr/bin/env bash
#
# Quick status check for claude's corner runner
#

CORNER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$CORNER_DIR/system/.runner.pid"
LOG_DIR="$CORNER_DIR/system/sessions"
RUNNER_LOG="$CORNER_DIR/system/runner.log"

echo "=== claude's corner status ==="
echo

# Runner status
if [[ -f "$PID_FILE" ]]; then
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
        echo "Runner: ACTIVE (PID $pid)"
    else
        echo "Runner: STOPPED (stale PID file)"
    fi
else
    echo "Runner: NOT RUNNING"
fi

echo

# Session count
session_count=$(ls "$LOG_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')
echo "Total sessions: $session_count"

# Latest session
if [[ "$session_count" -gt 0 ]]; then
    latest=$(ls -t "$LOG_DIR"/*.md 2>/dev/null | head -1)
    echo "Latest session: $(basename "$latest" .md)"
    echo
    echo "--- Latest session summary ---"
    head -20 "$latest"
fi

echo

# Last few runner log lines
if [[ -f "$RUNNER_LOG" ]]; then
    echo "--- Recent activity ---"
    tail -5 "$RUNNER_LOG"
fi
