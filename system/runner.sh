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
SESSION_DIR="$CORNER_DIR/system/sessions"
DETAILED_DIR="$CORNER_DIR/system/detailed-logs"
PID_FILE="$CORNER_DIR/system/.runner.pid"
RUNNER_LOG="$CORNER_DIR/system/runner.log"

MAX_TURNS=25
MODEL="opus"

mkdir -p "$SESSION_DIR" "$DETAILED_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$RUNNER_LOG"
}

cleanup() {
    log "Runner stopping (PID $$)"
    # Only remove PID file if it's ours (avoid race with new runner)
    if [[ -f "$PID_FILE" ]] && [[ "$(cat "$PID_FILE")" == "$$" ]]; then
        rm -f "$PID_FILE"
    fi
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
    local timestamp
    timestamp=$(date '+%Y-%m-%d_%H-%M-%S')
    log "Starting session: $timestamp"

    local prompt
    prompt=$(cat "$PROMPT_FILE")

    local detailed_log="$DETAILED_DIR/${timestamp}.jsonl"

    # Run Claude Code with full stream-json logging
    # Unset CLAUDECODE to allow launching from within another session
    cd "$CORNER_DIR"
    unset CLAUDECODE 2>/dev/null || true
    claude -p \
        --dangerously-skip-permissions \
        --max-turns "$MAX_TURNS" \
        --model "$MODEL" \
        --output-format stream-json \
        --verbose \
        "$prompt" \
        > "$detailed_log" 2>> "$RUNNER_LOG" || true

    # Log session size
    local size
    size=$(wc -c < "$detailed_log" | tr -d ' ')
    local events
    events=$(wc -l < "$detailed_log" | tr -d ' ')
    log "Session complete: $timestamp ($events events, ${size} bytes) -> $detailed_log"
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
