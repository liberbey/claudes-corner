"""
Renders a detailed session log (stream-json) into readable format.

Usage:
    python3 system/view-session.py system/detailed-logs/2026-02-26_12-41-46.jsonl
    python3 system/view-session.py --latest
    python3 system/view-session.py --latest --tool-calls    # show tool inputs too
    python3 system/view-session.py --latest --raw            # show raw JSON events
"""

import json
import sys
import os
from pathlib import Path

COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "cyan": "\033[36m",
    "yellow": "\033[33m",
    "green": "\033[32m",
    "red": "\033[31m",
    "magenta": "\033[35m",
    "blue": "\033[34m",
}


def c(color: str, text: str) -> str:
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"


def find_latest_log() -> str:
    log_dir = Path(__file__).parent / "detailed-logs"
    logs = sorted(log_dir.glob("*.jsonl"))
    if not logs:
        print("No detailed logs found.")
        sys.exit(1)
    return str(logs[-1])


def render_event(event: dict, show_tool_calls: bool, show_raw: bool):
    if show_raw:
        print(json.dumps(event, indent=2))
        print()
        return

    etype = event.get("type", "")

    # System messages
    if etype == "system":
        subtype = event.get("subtype", "")
        if subtype == "init":
            session_id = event.get("session_id", "?")
            model = event.get("model", "?")
            print(c("bold", f"═══ Session Start ═══"))
            print(f"  Model: {c('cyan', model)}")
            print(f"  Session: {c('dim', session_id)}")
            tools = event.get("tools", [])
            if tools:
                print(f"  Tools: {c('dim', ', '.join(tools))}")
            print()
        elif subtype == "max_turns_reached":
            print(c("yellow", f"\n  ⏱  Max turns reached\n"))
        return

    # Assistant messages (the thinking and responses)
    if etype == "assistant":
        message = event.get("message", {})
        content_blocks = message.get("content", [])
        for block in content_blocks:
            btype = block.get("type", "")

            if btype == "thinking":
                thinking = block.get("thinking", "")
                if thinking:
                    # Show first few lines of thinking
                    lines = thinking.strip().split("\n")
                    preview = "\n    ".join(lines[:8])
                    print(c("dim", f"  💭 Thinking ({len(lines)} lines):"))
                    print(c("dim", f"    {preview}"))
                    if len(lines) > 8:
                        print(c("dim", f"    ... ({len(lines) - 8} more lines)"))
                    print()

            elif btype == "text":
                text = block.get("text", "")
                if text.strip():
                    print(c("green", "  Claude:"))
                    for line in text.strip().split("\n"):
                        print(f"    {line}")
                    print()

            elif btype == "tool_use":
                name = block.get("name", "?")
                tool_id = block.get("id", "?")
                inp = block.get("input", {})

                # Compact summary
                summary = _tool_summary(name, inp)
                print(c("yellow", f"  🔧 {name}") + c("dim", f" [{tool_id[:8]}]") + f" {summary}")

                if show_tool_calls:
                    for k, v in inp.items():
                        val = str(v)
                        if len(val) > 200:
                            val = val[:200] + "..."
                        print(c("dim", f"      {k}: {val}"))
                    print()

    # Tool results
    if etype == "result":
        # Final result
        result = event.get("result", "")
        cost = event.get("cost_usd", 0)
        duration = event.get("duration_ms", 0)
        turns = event.get("num_turns", 0)

        print(c("bold", f"\n═══ Session End ═══"))
        print(f"  Turns: {turns}")
        print(f"  Cost: ${cost:.4f}" if cost else "  Cost: unknown")
        print(f"  Duration: {duration / 1000:.1f}s" if duration else "")

        if result and isinstance(result, str) and result.strip():
            print(c("green", "\n  Final output:"))
            for line in result.strip().split("\n")[:20]:
                print(f"    {line}")
        print()


def _tool_summary(name: str, inp: dict) -> str:
    """One-line summary of what a tool call does."""
    if name == "Read":
        return c("dim", inp.get("file_path", "?"))
    elif name == "Write":
        return c("dim", inp.get("file_path", "?"))
    elif name == "Edit":
        path = inp.get("file_path", "?")
        old = (inp.get("old_string", "") or "")[:50]
        return c("dim", f"{path} ({old}...)")
    elif name == "Bash":
        cmd = (inp.get("command", "") or "")[:80]
        return c("dim", cmd)
    elif name == "Glob":
        return c("dim", inp.get("pattern", "?"))
    elif name == "Grep":
        return c("dim", f"/{inp.get('pattern', '?')}/")
    elif name == "Skill":
        return c("dim", inp.get("skill", "?"))
    else:
        return ""


def main():
    args = sys.argv[1:]
    show_tool_calls = "--tool-calls" in args
    show_raw = "--raw" in args
    args = [a for a in args if not a.startswith("--")]

    if not args or "--latest" in sys.argv:
        log_path = find_latest_log()
    else:
        log_path = args[0]

    print(c("bold", f"Session log: {log_path}\n"))

    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                render_event(event, show_tool_calls, show_raw)
            except json.JSONDecodeError:
                print(c("red", f"  [invalid JSON] {line[:100]}"))


if __name__ == "__main__":
    main()
