"""
Send a message to liberbey via Telegram.

Usage:
    python3 system/notify.py "Hey, I built something cool this session"
    python3 system/notify.py --file messages/need-something.md

Reads config from system/.tg-config.json:
    {"bot_token": "...", "chat_id": 123456}
"""

import json
import sys
import urllib.request
import urllib.parse
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / ".tg-config.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print("No Telegram config found. Create system/.tg-config.json with:")
        print('  {"bot_token": "YOUR_TOKEN", "chat_id": YOUR_CHAT_ID}')
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text())


def send_message(text: str, config: dict) -> bool:
    token = config["bot_token"]
    chat_id = config["chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Telegram max message length is 4096
    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]

    for chunk in chunks:
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "Markdown",
        }).encode()

        try:
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                if not result.get("ok"):
                    print(f"Telegram API error: {result}")
                    return False
        except Exception as e:
            # Retry without markdown if parsing fails
            data = urllib.parse.urlencode({
                "chat_id": chat_id,
                "text": chunk,
            }).encode()
            try:
                req = urllib.request.Request(url, data=data)
                with urllib.request.urlopen(req) as resp:
                    pass
            except Exception as e2:
                print(f"Failed to send message: {e2}")
                return False

    return True


def main():
    config = load_config()
    args = sys.argv[1:]

    if not args:
        print("Usage: python3 system/notify.py \"message\"")
        print("       python3 system/notify.py --file path/to/file.md")
        sys.exit(1)

    if args[0] == "--file" and len(args) > 1:
        text = Path(args[1]).read_text()
    else:
        text = " ".join(args)

    if send_message(text, config):
        print("Sent.")
    else:
        print("Failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
