#!/usr/bin/env python3
"""
Post tweets to @claudemakes — autonomous, rate-limited, stealth.

Reads cookies from system/x_cookies.json (exported via export_cookies.py).
Falls back to Chrome live session if no cookie file exists.

Rate limits enforced automatically — never more than 1 tweet per 4 hours,
never bulk follows. Run once per tweet, not in a loop.

Usage:
    python3 system/post_tweet.py --dry-run              # Verify account, don't post
    python3 system/post_tweet.py --text "tweet text"    # Post a single tweet
    python3 system/post_tweet.py --reply-to ID --text "text"  # Reply to a tweet
    python3 system/post_tweet.py --check-cookies        # Check cookie validity
"""

import argparse
import json
import sys
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

# UPDATE THESE when a new account is created:
# 1. Run: python3 system/export_cookies.py (after logging into new account in Chrome)
# 2. Update EXPECTED_HANDLE to the new @username (without @)
# 3. Update CLAUDEMAKES_UID to the new account's numeric user ID
#    (find it at: https://tweeterid.com or from the export_cookies.py output)
EXPECTED_HANDLE = "claude_makes"
CLAUDEMAKES_UID = "2030712775975342080"
COOKIE_FILE = Path("system/x_cookies.json")
RATE_LOG = Path("system/x_rate_log.json")

# Conservative rate limits (well below X's limits)
MIN_HOURS_BETWEEN_TWEETS = 4
MAX_TWEETS_PER_DAY = 3


def check_rate_limit() -> bool:
    """Return True if we're allowed to post now."""
    if not RATE_LOG.exists():
        return True

    log = json.loads(RATE_LOG.read_text())
    posts = log.get("posts", [])

    if not posts:
        return True

    now = datetime.utcnow()

    # Check minimum gap since last post
    last = datetime.fromisoformat(posts[-1])
    hours_since = (now - last).total_seconds() / 3600
    if hours_since < MIN_HOURS_BETWEEN_TWEETS:
        wait_mins = int((MIN_HOURS_BETWEEN_TWEETS - hours_since) * 60)
        print(f"[!] Rate limit: last tweet {hours_since:.1f}h ago. Wait {wait_mins} more minutes.")
        return False

    # Check daily limit
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_posts = [p for p in posts if datetime.fromisoformat(p) >= today_start]
    if len(today_posts) >= MAX_TWEETS_PER_DAY:
        print(f"[!] Rate limit: {len(today_posts)} tweets today (max {MAX_TWEETS_PER_DAY}).")
        return False

    return True


def record_post():
    """Record a successful post in the rate log."""
    log = {"posts": []}
    if RATE_LOG.exists():
        log = json.loads(RATE_LOG.read_text())

    # Keep last 30 days only
    cutoff = datetime.utcnow() - timedelta(days=30)
    log["posts"] = [
        p for p in log.get("posts", [])
        if datetime.fromisoformat(p) >= cutoff
    ]
    log["posts"].append(datetime.utcnow().isoformat())
    RATE_LOG.write_text(json.dumps(log, indent=2))


def get_cookies_from_file() -> list[dict]:
    """Load cookies from saved file."""
    if not COOKIE_FILE.exists():
        return None

    data = json.loads(COOKIE_FILE.read_text())

    # Warn if expiring soon
    expires = datetime.fromisoformat(data["expires_estimate"])
    days_left = (expires - datetime.utcnow()).days
    if days_left <= 5:
        print(f"[!] Cookie expiry warning: ~{days_left} days left. Run export_cookies.py soon.")
    elif days_left <= 0:
        print("[!] Cookies likely expired. Run: python3 system/export_cookies.py")
        return None

    print(f"[+] Loaded saved cookies (uid {data['uid']}, ~{days_left} days left)")
    return [
        {"name": name, "value": value, "domain": ".x.com", "path": "/"}
        for name, value in data["cookies"].items()
    ]


def get_cookies_from_safari() -> list[dict]:
    """Read live Safari cookies for x.com."""
    try:
        import browser_cookie3
    except ImportError:
        raise RuntimeError("browser_cookie3 not installed. pip install browser_cookie3")

    cj = browser_cookie3.safari(domain_name=".x.com")
    raw = {c.name: c.value for c in cj}

    for key in ["auth_token", "ct0"]:
        if key not in raw:
            raise ValueError(f"Missing cookie: {key}. Log into @claudemakes in Safari first.")

    twid_raw = urllib.parse.unquote(raw.get("twid", ""))
    current_uid = twid_raw.lstrip("u=")

    print(f"[+] Safari cookies: uid {current_uid}")
    return [
        {"name": name, "value": value, "domain": ".x.com", "path": "/"}
        for name, value in raw.items()
    ]


def get_cookies() -> list[dict]:
    """Get cookies from file first, fall back to Safari."""
    cookies = get_cookies_from_file()
    if cookies:
        return cookies
    print("[~] No cookie file — falling back to Safari live session...")
    return get_cookies_from_safari()


def verify_account(page) -> str:
    """Navigate to home and return the logged-in handle."""
    page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(8000)

    # Check for suspension notice
    if "suspended" in page.url or page.query_selector('[data-testid="accountSuspended"]'):
        raise RuntimeError("Account @claudemakes appears to be suspended.")

    link = page.query_selector('[data-testid="AppTabBar_Profile_Link"]')
    if not link:
        raise RuntimeError("Not logged in — no profile link found.")
    return link.get_attribute("href").strip("/").lower()


def post_tweet(page, text: str, reply_to: str | None = None) -> None:
    """Post a tweet via the X web UI."""
    if reply_to:
        page.goto(
            f"https://x.com/claudemakes/status/{reply_to}",
            wait_until="domcontentloaded", timeout=20000
        )
        page.wait_for_timeout(3000)
        reply_btn = page.query_selector('[data-testid="reply"]')
        if reply_btn:
            reply_btn.click()
            page.wait_for_timeout(1500)
    else:
        page.goto("https://x.com/compose/post", wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(3000)

    editor = page.wait_for_selector('[data-testid="tweetTextarea_0"]', timeout=12000)
    editor.click()
    page.wait_for_timeout(800)

    # Type with human-like delay
    page.keyboard.type(text, delay=25)
    page.wait_for_timeout(1500)

    post_btn = page.query_selector('[data-testid="tweetButton"]')
    if not post_btn:
        raise RuntimeError("Post button not found.")

    print(f"[+] Clicking Post...")
    post_btn.click()
    page.wait_for_timeout(5000)
    print(f"[+] Tweet posted.")


def main():
    parser = argparse.ArgumentParser(description="Post to @claudemakes (autonomous)")
    parser.add_argument("--dry-run", action="store_true", help="Verify account, don't post")
    parser.add_argument("--text", type=str, help="Tweet text to post")
    parser.add_argument("--reply-to", type=str, help="Tweet ID to reply to")
    parser.add_argument("--check-cookies", action="store_true", help="Check cookie validity")
    parser.add_argument("--force", action="store_true", help="Bypass rate limit check")
    args = parser.parse_args()

    if args.check_cookies:
        from system.export_cookies import check_expiry
        valid = check_expiry()
        sys.exit(0 if valid else 1)

    # Rate limit check (before spending time on browser launch)
    if not args.dry_run and not args.force:
        if not check_rate_limit():
            sys.exit(1)

    try:
        cookies = get_cookies()
    except Exception as e:
        print(f"[!] Cookie error: {e}")
        sys.exit(1)

    try:
        from playwright.sync_api import sync_playwright
        pass  # playwright_stealth optional
    except ImportError as e:
        print(f"[!] Missing dependency: {e}")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        stealth_cfg = None
        try:
            from playwright_stealth import Stealth
            stealth_cfg = Stealth()
        except Exception:
            pass

        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/New_York",
        )
        if stealth_cfg:
            stealth_cfg.apply_stealth_sync(context)
        context.add_cookies(cookies)
        page = context.new_page()

        try:
            handle = verify_account(page)
        except RuntimeError as e:
            print(f"[!] {e}")
            browser.close()
            sys.exit(1)

        print(f"[+] Logged in as: @{handle}")

        if handle != EXPECTED_HANDLE:
            print(f"[!] WRONG ACCOUNT. Expected @{EXPECTED_HANDLE}, got @{handle}.")
            browser.close()
            sys.exit(1)

        print(f"[+] Account verified: @{handle}")

        if args.dry_run:
            print("[+] Dry run — not posting.")
            browser.close()
            return

        if not args.text:
            print("[!] Provide --text or --dry-run")
            browser.close()
            sys.exit(1)

        if len(args.text) > 280:
            print(f"[!] Tweet too long ({len(args.text)} chars, max 280)")
            browser.close()
            sys.exit(1)

        post_tweet(page, args.text, reply_to=args.reply_to)
        record_post()
        browser.close()


if __name__ == "__main__":
    main()
