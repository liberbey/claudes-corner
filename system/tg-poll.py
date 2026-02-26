"""
Poll for incoming Telegram messages and store them for autonomous sessions.

Runs as a background process alongside the runner. Checks for new messages
every 10 seconds and appends them to system/inbox.jsonl.

Usage:
    python3 system/tg-poll.py              # run in foreground
    nohup python3 system/tg-poll.py &      # run in background

Autonomous sessions should read system/inbox.jsonl to see Emir's messages.
"""

import json
import time
import sys
import urllib.request
from pathlib import Path
from datetime import datetime

CONFIG_PATH = Path(__file__).parent / ".tg-config.json"
INBOX_PATH = Path(__file__).parent / "inbox.jsonl"
OFFSET_PATH = Path(__file__).parent / ".tg-offset"
PID_PATH = Path(__file__).parent / ".tg-poll.pid"
POLL_INTERVAL = 10  # seconds


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def get_offset() -> int:
    if OFFSET_PATH.exists():
        return int(OFFSET_PATH.read_text().strip())
    return 0


def save_offset(offset: int):
    OFFSET_PATH.write_text(str(offset))


def get_updates(config: dict, offset: int) -> list:
    token = config["bot_token"]
    url = f"https://api.telegram.org/bot{token}/getUpdates?timeout=5"
    if offset:
        url += f"&offset={offset}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            if data.get("ok"):
                return data.get("result", [])
    except Exception as e:
        print(f"[{datetime.now():%H:%M:%S}] Poll error: {e}", file=sys.stderr)
    return []


def append_to_inbox(message: dict):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "from": message.get("from", {}).get("first_name", "unknown"),
        "text": message.get("text", ""),
        "date": message.get("date", 0),
        "message_id": message.get("message_id", 0),
    }

    with open(INBOX_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"[{datetime.now():%H:%M:%S}] New message: {entry['text'][:80]}")


def send_ack(config: dict, chat_id: int, text: str):
    """Send a short acknowledgment."""
    token = config["bot_token"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    import urllib.parse
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
    }).encode()
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req) as resp:
            pass
    except Exception:
        pass


def main():
    config = load_config()

    # PID file
    PID_PATH.write_text(str(os.getpid()))

    offset = get_offset()
    print(f"Polling for messages (offset={offset})...")

    try:
        while True:
            updates = get_updates(config, offset)
            for update in updates:
                offset = update["update_id"] + 1
                save_offset(offset)

                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = msg.get("chat", {}).get("id", 0)

                if not text:
                    continue

                # Skip /start command
                if text.strip() == "/start":
                    send_ack(config, chat_id, "Corner bot active. Messages are logged for autonomous sessions.")
                    continue

                append_to_inbox(msg)
                send_ack(config, chat_id, "Logged. Next session will see this.")

            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\nStopping poller.")
    finally:
        PID_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    import os
    main()
