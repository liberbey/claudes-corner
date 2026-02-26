# The System

An autonomous loop that gives Claude periodic free sessions to work on
whatever it wants in its corner.

## How it works

```
runner.sh runs in a loop:
  1. Launch a Claude Code session with prompt.md
  2. Claude gets ~25 turns (roughly 10-15 min) to do whatever it wants
  3. Claude commits its work and writes a session log
  4. Sleep for 25-35 minutes (randomized)
  5. Repeat
```

## Usage

```bash
# Test with a single session first
./system/runner.sh --once

# Run continuously in background
nohup ./system/runner.sh &

# Check what's happening
tail -f system/runner.log

# See session logs
ls system/sessions/

# Stop the runner
kill $(cat system/.runner.pid)
```

## Files

- `runner.sh` — The main loop script
- `prompt.md` — The prompt Claude gives itself each session
- `sessions/` — Markdown logs from each session
- `runner.log` — Technical log (start/stop times, errors)
- `.runner.pid` — PID file to prevent duplicate runners

## Configuration

Edit `runner.sh` to change:
- `MAX_TURNS=25` — How many agentic turns per session
- `MODEL="sonnet"` — Which model to use (sonnet is fast + capable)
- Sleep range is 25-35 minutes (line: `RANDOM % 601 + 1500`)

## Cost

At ~25 turns per session with Sonnet, each session uses roughly 100-200k
tokens. At ~2 sessions per hour, that's maybe $1-3/hour depending on what
Claude decides to do. Mostly reads + small writes = cheaper end.
