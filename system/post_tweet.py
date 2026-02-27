#!/usr/bin/env python3
"""
Post tweets to @claudemakes via Playwright + Chrome cookies.

Uses Playwright (real browser) to bypass Cloudflare, and swaps
auth cookies from @liberbey -> @claudemakes using auth_multi.

Usage:
    python3 system/post_tweet.py --dry-run              # Verify account, don't post
    python3 system/post_tweet.py --text "tweet text"    # Post a single tweet
    python3 system/post_tweet.py --reply-to ID --text "text"  # Reply to a tweet
"""

import argparse
import sys
import time
import urllib.parse

from pycookiecheat import chrome_cookies
from playwright.sync_api import sync_playwright

EXPECTED_HANDLE = "claudemakes"


CLAUDEMAKES_UID = "2027047400393863168"


def get_claudemakes_cookies() -> list[dict]:
    """Get Chrome cookies for @claudemakes.

    Handles two cases:
    1. @claudemakes is already primary (twid matches CLAUDEMAKES_UID) — use as-is.
    2. @claudemakes is secondary (in auth_multi) — swap auth_token and twid.
    """
    raw = chrome_cookies("https://x.com")

    for key in ["auth_token", "ct0"]:
        if key not in raw:
            raise ValueError(f"Missing cookie: {key}. Log into X in Chrome.")

    # Check if @claudemakes is already the primary account
    twid_raw = urllib.parse.unquote(raw.get("twid", ""))
    current_uid = twid_raw.lstrip("u=")

    if current_uid == CLAUDEMAKES_UID:
        # Already logged in as @claudemakes — pass cookies through unchanged
        pw_cookies = [
            {"name": name, "value": value, "domain": ".x.com", "path": "/"}
            for name, value in raw.items()
        ]
        print(f"[+] Cookies ready (already @claudemakes, uid {CLAUDEMAKES_UID})")
        return pw_cookies

    # @claudemakes is secondary — swap via auth_multi
    auth_multi = urllib.parse.unquote(raw.get("auth_multi", ""))
    if not auth_multi:
        raise ValueError("No auth_multi cookie — @claudemakes not logged in Chrome.")

    # auth_multi format: "user_id:auth_token"
    parts = auth_multi.strip('"').split(":", 1)
    claude_uid, claude_auth = parts[0], parts[1]

    if claude_uid != CLAUDEMAKES_UID:
        raise ValueError(
            f"auth_multi uid {claude_uid} is not @claudemakes ({CLAUDEMAKES_UID}). "
            "Ensure @claudemakes is logged in Chrome."
        )

    current_auth = raw["auth_token"]
    pw_cookies = []
    for name, value in raw.items():
        if name == "auth_token":
            value = claude_auth
        elif name == "twid":
            value = urllib.parse.quote(f"u={claude_uid}")
        elif name == "auth_multi":
            value = urllib.parse.quote(f'"{current_uid}:{current_auth}"')
        pw_cookies.append({
            "name": name, "value": value,
            "domain": ".x.com", "path": "/",
        })

    print(f"[+] Cookies ready (swapped to @claudemakes, uid {claude_uid})")
    return pw_cookies


def verify_account(page) -> str:
    """Navigate to home and return the logged-in handle."""
    page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(3000)
    link = page.query_selector('[data-testid="AppTabBar_Profile_Link"]')
    if not link:
        raise RuntimeError("Not logged in — no profile link found.")
    return link.get_attribute("href").strip("/").lower()


def post_tweet(page, text: str, reply_to: str | None = None) -> str | None:
    """Post a tweet via the X web UI. Returns tweet URL if found."""
    if reply_to:
        page.goto(f"https://x.com/claudemakes/status/{reply_to}",
                  wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(2000)
        # Click the reply button on the tweet
        reply_btn = page.query_selector('[data-testid="reply"]')
        if reply_btn:
            reply_btn.click()
            page.wait_for_timeout(1000)
    else:
        page.goto("https://x.com/compose/post",
                  wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(2000)

    # Find the tweet compose box and type
    editor = page.wait_for_selector(
        '[data-testid="tweetTextarea_0"]', timeout=10000
    )
    editor.click()
    page.wait_for_timeout(500)

    # Type character by character for the rich text editor
    page.keyboard.type(text, delay=10)
    page.wait_for_timeout(1000)

    # Click post button
    post_btn = page.query_selector('[data-testid="tweetButton"]')
    if not post_btn:
        raise RuntimeError("Post button not found.")

    print(f"[+] Clicking Post...")
    post_btn.click()
    page.wait_for_timeout(4000)

    # Try to find the posted tweet URL from the page
    print(f"[+] Tweet posted.")
    return None


def main():
    parser = argparse.ArgumentParser(description="Post to @claudemakes")
    parser.add_argument("--dry-run", action="store_true",
                        help="Verify account only, do not post")
    parser.add_argument("--text", type=str, help="Tweet text to post")
    parser.add_argument("--reply-to", type=str, help="Tweet ID to reply to")
    args = parser.parse_args()

    cookies = get_claudemakes_cookies()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        context.add_cookies(cookies)

        page = context.new_page()
        handle = verify_account(page)
        print(f"[+] Logged in as: @{handle}")

        if handle != EXPECTED_HANDLE:
            print(f"[!] WRONG ACCOUNT. Expected @{EXPECTED_HANDLE}, got @{handle}.")
            sys.exit(1)

        print(f"[+] Account verified: @{handle}")

        if args.dry_run:
            print("[+] Dry run — not posting.")
            browser.close()
            return

        if not args.text:
            print("[!] Provide --text or --dry-run")
            sys.exit(1)

        post_tweet(page, args.text, reply_to=args.reply_to)
        browser.close()


if __name__ == "__main__":
    main()
