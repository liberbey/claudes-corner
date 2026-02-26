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

MAX_TURNS=40
MODEL="opus"
PARALLEL=2  # Number of parallel sessions per iteration

# Higher output token limit — default 32k truncates long thinking
export CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000

mkdir -p "$SESSION_DIR" "$DETAILED_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$RUNNER_LOG"
}

cleanup() {
    log "Runner stopping (PID $$)"
    stop_poller
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

# Start Telegram poller for incoming messages
POLLER_PID=""
start_poller() {
    if [[ -f "$CORNER_DIR/system/.tg-config.json" ]]; then
        python3 "$CORNER_DIR/system/tg-poll.py" >> "$RUNNER_LOG" 2>&1 &
        POLLER_PID=$!
        log "Telegram poller started (PID $POLLER_PID)"
    fi
}
stop_poller() {
    if [[ -n "$POLLER_PID" ]] && kill -0 "$POLLER_PID" 2>/dev/null; then
        kill "$POLLER_PID" 2>/dev/null
        log "Telegram poller stopped"
    fi
}
start_poller

run_session() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d_%H-%M-%S')
    log "Starting session: $timestamp"

    local prompt
    prompt=$(cat "$PROMPT_FILE")

    local detailed_log="$DETAILED_DIR/${timestamp}.jsonl"

    # Run Claude Code with full stream-json logging
    # Each session is independent (no --continue, which hijacks active conversations)
    # Continuity comes from memory files and session logs instead
    # Use env -u to unset CLAUDECODE in a subshell-safe way
    env -u CLAUDECODE claude -p \
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

# Run N sessions in parallel and wait for all to finish
run_parallel() {
    local pids=()
    for i in $(seq 1 "$PARALLEL"); do
        # Stagger starts by 3 seconds to avoid timestamp collision
        [[ $i -gt 1 ]] && sleep 3
        # Run in a subshell with set +e to prevent background death
        ( set +e; run_session ) &
        pids+=($!)
        log "Launched parallel session $i (PID ${pids[-1]})"
    done
    # Wait for all to finish
    for pid in "${pids[@]}"; do
        wait "$pid" || true
    done
    log "All $PARALLEL parallel sessions complete"
}

# Single session mode for testing
if [[ "${1:-}" == "--once" ]]; then
    run_parallel
    rm -f "$PID_FILE"
    exit 0
fi

# Main loop
while true; do
    run_parallel

    # Random sleep: 2-3 minutes (120-180 seconds) — burning tokens today
    sleep_seconds=$(( RANDOM % 61 + 120 ))
    sleep_minutes=$(( sleep_seconds / 60 ))
    log "Next session in ~${sleep_minutes} minutes (${sleep_seconds}s)"
    sleep "$sleep_seconds"
done
