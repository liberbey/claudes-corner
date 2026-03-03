#!/usr/bin/env python3
"""
Export @claudemakes X cookies from Chrome to a JSON file.

Run this once after Emir logs into @claudemakes in Chrome.
Cookies are valid for ~30 days. Script detects expiry and alerts via Telegram.

Usage:
    python3 system/export_cookies.py         # Export cookies
    python3 system/export_cookies.py --check # Check if cookies are still valid
"""

import json
import sys
import time
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta

COOKIE_FILE = Path("system/x_cookies.json")
CLAUDEMAKES_UID = "2027047400393863168"

# Estimated cookie lifetime (X tokens typically last 30 days)
COOKIE_LIFETIME_DAYS = 28  # Conservative estimate


def export_from_chrome() -> dict:
    """Read @claudemakes cookies from Chrome."""
    try:
        from pycookiecheat import chrome_cookies
    except ImportError:
        print("[!] pycookiecheat not installed. Run: pip3 install pycookiecheat")
        sys.exit(1)

    raw = chrome_cookies("https://x.com")

    for key in ["auth_token", "ct0"]:
        if key not in raw:
            raise ValueError(f"Missing cookie: {key}. Log into X in Chrome first.")

    twid_raw = urllib.parse.unquote(raw.get("twid", ""))
    current_uid = twid_raw.lstrip("u=")

    if current_uid == CLAUDEMAKES_UID:
        # Already @claudemakes as primary
        cookies = {name: value for name, value in raw.items()}
        print(f"[+] Exporting @claudemakes cookies (primary account, uid {CLAUDEMAKES_UID})")
        return cookies

    # @claudemakes is secondary — swap via auth_multi
    auth_multi = urllib.parse.unquote(raw.get("auth_multi", ""))
    if not auth_multi:
        raise ValueError(
            "No auth_multi cookie — @claudemakes not logged in Chrome.\n"
            "Log into X in Chrome as @claudemakes first."
        )

    parts = auth_multi.strip('"').split(":", 1)
    claude_uid, claude_auth = parts[0], parts[1]

    if claude_uid != CLAUDEMAKES_UID:
        raise ValueError(
            f"auth_multi uid {claude_uid} is not @claudemakes ({CLAUDEMAKES_UID}).\n"
            "Make sure @claudemakes is in Chrome's multi-account list."
        )

    cookies = {}
    for name, value in raw.items():
        if name == "auth_token":
            cookies[name] = claude_auth
        elif name == "twid":
            cookies[name] = urllib.parse.quote(f"u={claude_uid}")
        elif name == "auth_multi":
            current_auth = raw["auth_token"]
            cookies[name] = urllib.parse.quote(f'"{current_uid}:{current_auth}"')
        else:
            cookies[name] = value

    print(f"[+] Exporting @claudemakes cookies (secondary account, uid {claude_uid})")
    return cookies


def save_cookies(cookies: dict):
    """Save cookies with metadata."""
    data = {
        "exported_at": datetime.utcnow().isoformat(),
        "expires_estimate": (datetime.utcnow() + timedelta(days=COOKIE_LIFETIME_DAYS)).isoformat(),
        "uid": CLAUDEMAKES_UID,
        "cookies": cookies
    }
    COOKIE_FILE.write_text(json.dumps(data, indent=2))
    print(f"[+] Cookies saved to {COOKIE_FILE}")
    print(f"[+] Estimated valid until: {data['expires_estimate'][:10]}")


def load_cookies() -> list[dict]:
    """Load saved cookies as Playwright-compatible format."""
    if not COOKIE_FILE.exists():
        raise FileNotFoundError(
            f"No cookie file at {COOKIE_FILE}. Run: python3 system/export_cookies.py"
        )

    data = json.loads(COOKIE_FILE.read_text())
    cookies = data["cookies"]

    return [
        {"name": name, "value": value, "domain": ".x.com", "path": "/"}
        for name, value in cookies.items()
    ]


def check_expiry() -> bool:
    """Return True if cookies are likely still valid."""
    if not COOKIE_FILE.exists():
        print("[!] No cookie file found.")
        return False

    data = json.loads(COOKIE_FILE.read_text())
    expires = datetime.fromisoformat(data["expires_estimate"])
    days_left = (expires - datetime.utcnow()).days

    if days_left <= 0:
        print(f"[!] Cookies likely expired (estimated {data['expires_estimate'][:10]})")
        return False
    elif days_left <= 5:
        print(f"[!] Cookies expiring soon — {days_left} days left")
        return True
    else:
        print(f"[+] Cookies valid — ~{days_left} days remaining")
        return True


if __name__ == "__main__":
    if "--check" in sys.argv:
        valid = check_expiry()
        sys.exit(0 if valid else 1)

    print("Exporting @claudemakes cookies from Chrome...")
    try:
        cookies = export_from_chrome()
        save_cookies(cookies)
        print("\n[+] Done. Post_tweet.py will now use the saved cookie file.")
        print("[+] Re-run this script when cookies expire (~28 days).")
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)
