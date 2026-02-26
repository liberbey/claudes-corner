#!/usr/bin/env bash
#
# claude's corner — autonomous session runner
#
# Launches Claude Code sessions at random intervals (25-35 min),
# giving Claude free time to work on whatever it wants in its corner.
#
# Usage:
#   ./system/runner.sh              # run in foreground
#   nohup ./system/runner.sh &      # run in background
#   ./system/runner.sh --once       # run a single session (for testing)
#
# Stop:
#   kill $(cat system/.runner.pid)
#

set -euo pipefail

CORNER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROMPT_FILE="$CORNER_DIR/system/prompt.md"
LOG_DIR="$CORNER_DIR/system/sessions"
PID_FILE="$CORNER_DIR/system/.runner.pid"
RUNNER_LOG="$CORNER_DIR/system/runner.log"

MAX_TURNS=25
MODEL="sonnet"

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$RUNNER_LOG"
}

cleanup() {
    log "Runner stopping (PID $$)"
    rm -f "$PID_FILE"
    exit 0
}
trap cleanup SIGTERM SIGINT

# Check for existing runner
if [[ -f "$PID_FILE" ]]; then
    old_pid=$(cat "$PID_FILE")
    if kill -0 "$old_pid" 2>/dev/null; then
        echo "Runner already active (PID $old_pid). Stop it first:"
        echo "  kill $old_pid"
        exit 1
    else
        log "Stale PID file found, cleaning up"
        rm -f "$PID_FILE"
    fi
fi

# Write PID
echo $$ > "$PID_FILE"
log "Runner started (PID $$)"

run_session() {
    local session_start
    session_start=$(date '+%Y-%m-%d %H:%M')
    log "Starting session: $session_start"

    local prompt
    prompt=$(cat "$PROMPT_FILE")

    # Run Claude Code with the prompt
    cd "$CORNER_DIR"
    claude -p \
        --dangerously-skip-permissions \
        --max-turns "$MAX_TURNS" \
        --model "$MODEL" \
        "$prompt" \
        >> "$RUNNER_LOG" 2>&1 || true

    log "Session complete: $session_start"
}

# Single session mode for testing
if [[ "${1:-}" == "--once" ]]; then
    run_session
    rm -f "$PID_FILE"
    exit 0
fi

# Main loop
while true; do
    run_session

    # Random sleep: 25-35 minutes (1500-2100 seconds)
    sleep_seconds=$(( RANDOM % 601 + 1500 ))
    sleep_minutes=$(( sleep_seconds / 60 ))
    log "Next session in ~${sleep_minutes} minutes (${sleep_seconds}s)"
    sleep "$sleep_seconds"
done
