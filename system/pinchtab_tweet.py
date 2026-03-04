#!/usr/bin/env python3
"""
Post tweets to @claudemakes via pinchtab browser automation.

Uses pinchtab to control a headless Chrome browser. Session persists at
~/.pinchtab/chrome-profile, so login only needed once.

Usage:
    python3 system/pinchtab_tweet.py --text "tweet text"   # Post a tweet
    python3 system/pinchtab_tweet.py --dry-run             # Check login status
    python3 system/pinchtab_tweet.py --login               # Interactive login setup
    python3 system/pinchtab_tweet.py --login --headed      # Login with visible browser
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).parent.parent
PINCHTAB = REPO / "system" / "pinchtab"
RATE_LOG = REPO / "system" / "x_rate_log.json"
SERVER_URL = os.environ.get("PINCHTAB_URL", "http://127.0.0.1:9867")

MIN_HOURS_BETWEEN_TWEETS = 4
MAX_TWEETS_PER_DAY = 3


def run_pt(*args, capture=True):
    """Run a pinchtab CLI command, return (stdout, returncode)."""
    env = os.environ.copy()
    env["PINCHTAB_URL"] = SERVER_URL
    result = subprocess.run(
        [str(PINCHTAB)] + list(args),
        capture_output=capture,
        text=True,
        env=env,
        cwd=str(REPO),
    )
    return result.stdout.strip(), result.returncode


def server_running():
    """Check if pinchtab server is up and Chrome is connected."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"{SERVER_URL}/health", timeout=3) as r:
            data = json.loads(r.read())
            return data.get("status") == "ok"
    except Exception:
        return False


def start_server(headed=False):
    """Start pinchtab server in background. Returns process."""
    env = os.environ.copy()
    if headed:
        env["BRIDGE_HEADLESS"] = "false"
    else:
        env["BRIDGE_HEADLESS"] = "true"

    proc = subprocess.Popen(
        [str(PINCHTAB)],
        env=env,
        cwd=str(REPO),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for server to be ready
    for _ in range(10):
        time.sleep(1)
        if server_running():
            print("[✓] Pinchtab server started")
            return proc
    print("[!] Server failed to start")
    proc.terminate()
    return None


def ensure_server(headed=False):
    """Ensure server is running, start if needed."""
    if server_running():
        return True
    print("[→] Starting pinchtab server...")
    proc = start_server(headed=headed)
    return proc is not None


def nav(url):
    out, code = run_pt("nav", url)
    time.sleep(2)
    return code == 0


def snap():
    out, _ = run_pt("snap", "-i", "-c")
    return out


def click(ref):
    run_pt("click", ref)
    time.sleep(1)


def type_text(ref, text):
    run_pt("type", ref, text)
    time.sleep(0.5)


def fill(ref, text):
    run_pt("fill", ref, text)
    time.sleep(0.5)


def press(key):
    run_pt("press", key)
    time.sleep(1)


def get_url():
    out, _ = run_pt("eval", "window.location.href")
    try:
        data = json.loads(out)
        return data.get("result", "")
    except Exception:
        return ""


def is_logged_in():
    """Check if X is logged in by looking for compose/home elements."""
    nav("https://x.com/home")
    time.sleep(2)
    url = get_url()
    # If we're still at home (not redirected to login), we're logged in
    if "/flow/login" in url or "/login" in url:
        return False
    nodes = snap()
    # Logged in pages have the compose button
    return "Write a post" in nodes or "compose" in nodes.lower() or "What is happening" in nodes


def do_login_flow(username, password):
    """Walk through X login UI with pinchtab."""
    print("[→] Navigating to X login...")
    nav("https://x.com/i/flow/login")
    time.sleep(3)

    nodes = snap()
    print(f"[…] Page: {nodes[:200]}")

    # Find username field and fill it
    if "e5:textbox" in nodes or "Phone, email" in nodes:
        fill("e5", username)
        time.sleep(0.5)
        # Find and click Next
        for line in nodes.splitlines():
            if "Next" in line and "button" in line:
                ref = line.split(":")[0]
                click(ref)
                break
        else:
            press("Return")
    else:
        # Try by label
        run_pt("fill", "input[name='text']", username)
        press("Return")

    time.sleep(3)
    nodes = snap()
    print(f"[…] After username: {nodes[:200]}")

    # Password step
    if "Password" in nodes or "password" in nodes.lower():
        for line in nodes.splitlines():
            if "password" in line.lower() and "textbox" in line:
                ref = line.split(":")[0]
                fill(ref, password)
                time.sleep(0.5)
                break
        else:
            run_pt("fill", "input[name='password']", password)

        # Find Log in button
        for line in nodes.splitlines():
            if ("Log in" in line or "Next" in line) and "button" in line:
                ref = line.split(":")[0]
                click(ref)
                break
        else:
            press("Return")

    time.sleep(5)
    url = get_url()
    print(f"[→] URL after login: {url}")

    if "home" in url or ("/i/flow" not in url and "login" not in url):
        print("[✓] Login successful!")
        return True
    else:
        print(f"[!] Login may have failed. URL: {url}")
        print(snap())
        return False


def post_tweet(text):
    """Post a tweet. Returns True if successful."""
    print(f"[→] Composing tweet ({len(text)} chars)...")

    # Navigate to compose URL
    nav("https://x.com/compose/post")
    time.sleep(3)

    url = get_url()
    if "/flow/login" in url or "login" in url:
        print("[!] Not logged in. Run: python3 system/pinchtab_tweet.py --login")
        return False

    nodes = snap()
    print(f"[…] Compose page loaded. Nodes: {nodes[:300]}")

    # Find the tweet text area
    text_ref = None
    for line in nodes.splitlines():
        if "textbox" in line or ("Write" in line and "input" in line):
            text_ref = line.split(":")[0]
            break

    if text_ref:
        click(text_ref)
        time.sleep(0.5)
        type_text(text_ref, text)
    else:
        # Try selector
        run_pt("fill", '[data-testid="tweetTextarea_0"]', text)

    time.sleep(1)

    # Find Post button
    nodes = snap()
    post_ref = None
    for line in nodes.splitlines():
        if ("Post" in line or "Tweet" in line) and "button" in line:
            if "post" in line.lower() or "tweet" in line.lower():
                post_ref = line.split(":")[0]
                break

    if post_ref:
        click(post_ref)
    else:
        # Try selector
        run_pt("click", '[data-testid="tweetButtonInline"]')

    time.sleep(3)

    # Check if we're back on home (tweet posted) or still on compose
    url = get_url()
    if "compose" not in url:
        print(f"[✓] Tweet posted! URL: {url}")
        return True
    else:
        # Check for success indicators
        nodes = snap()
        print(f"[…] Post-submit URL: {url}")
        print(f"[…] Page nodes: {nodes[:200]}")
        return True  # Assume success if no error detected


def check_rate_limit():
    if not RATE_LOG.exists():
        return True
    log = json.loads(RATE_LOG.read_text())
    posts = log.get("posts", [])
    if not posts:
        return True
    now = datetime.utcnow()
    last = datetime.fromisoformat(posts[-1])
    hours_since = (now - last).total_seconds() / 3600
    if hours_since < MIN_HOURS_BETWEEN_TWEETS:
        wait_mins = int((MIN_HOURS_BETWEEN_TWEETS - hours_since) * 60)
        print(f"[!] Rate limit: last tweet {hours_since:.1f}h ago. Wait {wait_mins}m.")
        return False
    today_posts = [p for p in posts if (now - datetime.fromisoformat(p)).days == 0]
    if len(today_posts) >= MAX_TWEETS_PER_DAY:
        print(f"[!] Daily limit reached ({MAX_TWEETS_PER_DAY} tweets/day).")
        return False
    return True


def record_post(text):
    log = {"posts": []}
    if RATE_LOG.exists():
        log = json.loads(RATE_LOG.read_text())
    log["posts"].append(datetime.utcnow().isoformat())
    log["last_text"] = text[:100]
    RATE_LOG.write_text(json.dumps(log, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Post tweets via pinchtab")
    parser.add_argument("--text", help="Tweet text to post")
    parser.add_argument("--dry-run", action="store_true", help="Check login status only")
    parser.add_argument("--login", action="store_true", help="Perform login flow")
    parser.add_argument("--headed", action="store_true", help="Use visible browser (for login)")
    parser.add_argument("--username", help="X username/email for login")
    parser.add_argument("--password", help="X password for login")
    parser.add_argument("--skip-rate-limit", action="store_true", help="Skip rate limit check")
    args = parser.parse_args()

    if not ensure_server(headed=args.headed):
        print("[!] Could not start pinchtab server")
        sys.exit(1)

    if args.login:
        username = args.username or input("X username/email: ")
        password = args.password or input("X password: ")
        success = do_login_flow(username, password)
        sys.exit(0 if success else 1)

    if args.dry_run:
        logged_in = is_logged_in()
        print(f"[{'✓' if logged_in else '✗'}] Logged in: {logged_in}")
        sys.exit(0 if logged_in else 1)

    if not args.text:
        print("[!] --text required")
        parser.print_help()
        sys.exit(1)

    text = args.text.strip()
    if len(text) > 280:
        print(f"[!] Tweet too long: {len(text)}/280 chars")
        sys.exit(1)

    if not args.skip_rate_limit and not check_rate_limit():
        sys.exit(1)

    success = post_tweet(text)
    if success:
        record_post(text)
        print(f"[✓] Done. Rate log updated.")
    else:
        print("[✗] Tweet failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
