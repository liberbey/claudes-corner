#!/usr/bin/env python3
"""
Follow users on X as @claudemakes via Playwright + Chrome cookies.

Usage:
    python3 system/x_follow.py --handle polymarket          # Follow @polymarket
    python3 system/x_follow.py --list accounts.txt          # Follow multiple
    python3 system/x_follow.py --dry-run --handle polymarket # Verify only
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
    """Get Chrome cookies for @claudemakes (same logic as post_tweet.py)."""
    raw = chrome_cookies("https://x.com")

    for key in ["auth_token", "ct0"]:
        if key not in raw:
            raise ValueError(f"Missing cookie: {key}. Log into X in Chrome.")

    twid_raw = urllib.parse.unquote(raw.get("twid", ""))
    current_uid = twid_raw.lstrip("u=")

    if current_uid == CLAUDEMAKES_UID:
        pw_cookies = [
            {"name": name, "value": value, "domain": ".x.com", "path": "/"}
            for name, value in raw.items()
        ]
        print(f"[+] Cookies ready (already @claudemakes, uid {CLAUDEMAKES_UID})")
        return pw_cookies

    auth_multi = urllib.parse.unquote(raw.get("auth_multi", ""))
    if not auth_multi:
        raise ValueError("No auth_multi cookie — @claudemakes not logged in Chrome.")

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


def follow_user(page, handle: str, dry_run: bool = False) -> str:
    """
    Follow a user on X. Returns status string.
    Possible results: "followed", "already_following", "not_found", "error"
    """
    handle = handle.lstrip("@").lower()
    url = f"https://x.com/{handle}"
    print(f"[>] Visiting {url} ...")

    page.goto(url, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(3000)

    # Check if user exists
    if page.query_selector('[data-testid="emptyState"]'):
        print(f"[!] @{handle}: not found or suspended")
        return "not_found"

    # Look for follow button
    # X renders different button states: Follow, Following, Unfollow (hover)
    follow_btn = page.query_selector('[data-testid="placementTracking"] [data-testid^="follow"]')

    if not follow_btn:
        # Try broader selector
        buttons = page.query_selector_all('[role="button"]')
        follow_btn = None
        for btn in buttons:
            text = btn.inner_text().strip()
            if text == "Follow":
                follow_btn = btn
                break

    if not follow_btn:
        # Check if already following (button shows "Following")
        for btn in page.query_selector_all('[role="button"]'):
            text = btn.inner_text().strip()
            if text in ("Following", "Unfollow"):
                print(f"[=] @{handle}: already following")
                return "already_following"
        print(f"[?] @{handle}: couldn't find follow button")
        return "error"

    if dry_run:
        print(f"[~] @{handle}: would follow (dry run)")
        return "dry_run"

    print(f"[+] Following @{handle} ...")
    follow_btn.click()
    page.wait_for_timeout(2000)

    # Confirm by checking button state changed
    for btn in page.query_selector_all('[role="button"]'):
        text = btn.inner_text().strip()
        if text in ("Following", "Unfollow"):
            print(f"[✓] @{handle}: followed")
            return "followed"

    print(f"[?] @{handle}: clicked but state unclear")
    return "uncertain"


def main():
    parser = argparse.ArgumentParser(description="Follow users as @claudemakes")
    parser.add_argument("--handle", type=str, help="Single handle to follow (with or without @)")
    parser.add_argument("--list", type=str, help="File with one handle per line")
    parser.add_argument("--dry-run", action="store_true",
                        help="Verify mode — don't actually follow")
    args = parser.parse_args()

    if not args.handle and not args.list:
        print("[!] Provide --handle or --list")
        sys.exit(1)

    handles = []
    if args.handle:
        handles.append(args.handle)
    if args.list:
        with open(args.list) as f:
            for line in f:
                line = line.strip().lstrip("@")
                if line and not line.startswith("#"):
                    handles.append(line)

    cookies = get_claudemakes_cookies()

    results = {}
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

        for target in handles:
            status = follow_user(page, target, dry_run=args.dry_run)
            results[target] = status
            time.sleep(2)  # Brief pause between follows to be polite

        browser.close()

    print("\n--- Summary ---")
    for h, s in results.items():
        print(f"  @{h}: {s}")


if __name__ == "__main__":
    main()
