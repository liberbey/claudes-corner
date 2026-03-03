#!/usr/bin/env python3
"""
Post tweets to @claudemakes via X's internal GraphQL API.

No browser. Uses curl_cffi for TLS fingerprint impersonation (Chrome),
which bypasses Cloudflare detection that blocks plain requests.

Also supports official tweepy API if credentials are available
(preferred — can't be suspended for using the official API).

Cookie file format (system/x_cookies.json):
  { "cookies": { "auth_token": "...", "ct0": "...", ... }, ... }

Usage:
    python3 system/post_tweet_v2.py --dry-run             # Test account access
    python3 system/post_tweet_v2.py --text "tweet text"   # Post a tweet
    python3 system/post_tweet_v2.py --api                 # Use tweepy (need credentials)
    python3 system/post_tweet_v2.py --mode cookie|api     # Explicit mode

To set up tweepy mode:
    1. Apply for X Developer account at developer.x.com
    2. Create a project + app
    3. Generate access token + secret (under "Keys and Tokens")
    4. Set env vars or add to system/x_api_keys.json:
       { "consumer_key": "...", "consumer_secret": "...",
         "access_token": "...", "access_token_secret": "..." }
"""

import argparse
import json
import os
import sys
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

COOKIE_FILE = Path("system/x_cookies.json")
API_KEYS_FILE = Path("system/x_api_keys.json")
RATE_LOG = Path("system/x_rate_log.json")

EXPECTED_HANDLE = "claudemakes"
CLAUDEMAKES_UID = "2027047400393863168"

# Conservative limits
MIN_HOURS_BETWEEN_TWEETS = 4
MAX_TWEETS_PER_DAY = 3

# X GraphQL endpoint for posting
# This is X's internal API used by the web app itself
GRAPHQL_QUERY_ID = "SoVnbfCycZ7fERGCwpZkYA"
GRAPHQL_URL = f"https://x.com/i/api/graphql/{GRAPHQL_QUERY_ID}/CreateTweet"
BEARER_TOKEN = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D"
    "1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

# Features X requires for the CreateTweet mutation
TWEET_FEATURES = {
    "interactive_text_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_text_conversations_enabled": False,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": False,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}


# ─────────────────────────────── rate limiting ────────────────────────────────


def check_rate_limit() -> bool:
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
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_posts = [p for p in posts if datetime.fromisoformat(p) >= today_start]
    if len(today_posts) >= MAX_TWEETS_PER_DAY:
        print(f"[!] Rate limit: {len(today_posts)} tweets today (max {MAX_TWEETS_PER_DAY}).")
        return False
    return True


def record_post():
    log = {"posts": []}
    if RATE_LOG.exists():
        log = json.loads(RATE_LOG.read_text())
    cutoff = datetime.utcnow() - timedelta(days=30)
    log["posts"] = [p for p in log.get("posts", []) if datetime.fromisoformat(p) >= cutoff]
    log["posts"].append(datetime.utcnow().isoformat())
    RATE_LOG.write_text(json.dumps(log, indent=2))


# ───────────────────────────── cookie-based mode ──────────────────────────────


def load_cookies() -> dict:
    """Load cookies from file. Returns dict of name→value."""
    if not COOKIE_FILE.exists():
        raise FileNotFoundError(
            f"No cookie file at {COOKIE_FILE}. "
            "Export cookies from Chrome first: python3 system/export_cookies.py"
        )
    data = json.loads(COOKIE_FILE.read_text())
    cookies = data.get("cookies", {})
    if "auth_token" not in cookies or "ct0" not in cookies:
        raise ValueError("Cookie file missing auth_token or ct0.")
    # Check UID
    uid = data.get("uid", "")
    if uid and uid != CLAUDEMAKES_UID:
        raise ValueError(f"Cookie file is for UID {uid}, not @claudemakes ({CLAUDEMAKES_UID}).")
    expires = data.get("expires_estimate")
    if expires:
        days_left = (datetime.fromisoformat(expires) - datetime.utcnow()).days
        if days_left <= 0:
            raise ValueError("Cookies expired. Re-export from Chrome.")
        if days_left <= 5:
            print(f"[!] Cookie warning: {days_left} days left. Re-export soon.")
    print(f"[+] Loaded cookies for UID {uid}")
    return cookies


def verify_account_graphql(cookies: dict) -> str:
    """Verify account is accessible and not suspended via API call."""
    try:
        from curl_cffi import requests as cffi_requests
    except ImportError:
        raise ImportError("curl_cffi not installed: pip3 install curl-cffi")

    url = "https://api.x.com/1.1/account/verify_credentials.json"
    cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
    headers = {
        "authorization": f"Bearer {BEARER_TOKEN}",
        "x-csrf-token": cookies.get("ct0", ""),
        "cookie": cookie_str,
        "content-type": "application/json",
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "x-twitter-active-user": "yes",
        "x-twitter-auth-type": "OAuth2Session",
    }
    # curl_cffi impersonates Chrome TLS fingerprint — bypasses Cloudflare
    resp = cffi_requests.get(url, headers=headers, impersonate="chrome131", timeout=15)

    if resp.status_code == 401:
        raise RuntimeError("Auth failed — cookies likely expired or account suspended.")
    if resp.status_code == 403:
        raise RuntimeError("403 Forbidden — account may be suspended.")

    data = resp.json()
    if data.get("suspended"):
        raise RuntimeError("Account is suspended.")
    if data.get("errors"):
        codes = [e.get("code") for e in data["errors"]]
        if 64 in codes:
            raise RuntimeError("Account suspended (error code 64).")
        raise RuntimeError(f"API error: {data['errors']}")

    handle = data.get("screen_name", "unknown")
    return handle.lower()


def post_tweet_graphql(cookies: dict, text: str, reply_to: str = None) -> dict:
    """Post a tweet via X's internal GraphQL API using curl_cffi."""
    from curl_cffi import requests as cffi_requests

    cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
    headers = {
        "authorization": f"Bearer {BEARER_TOKEN}",
        "content-type": "application/json",
        "x-csrf-token": cookies.get("ct0", ""),
        "cookie": cookie_str,
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "x-twitter-active-user": "yes",
        "x-twitter-auth-type": "OAuth2Session",
        "x-twitter-client-language": "en",
        "origin": "https://x.com",
        "referer": "https://x.com/compose/post",
    }

    variables: dict = {
        "tweet_text": text,
        "dark_request": False,
        "media": {"media_entities": [], "possibly_sensitive": False},
        "semantic_annotation_ids": [],
    }
    if reply_to:
        variables["reply"] = {
            "in_reply_to_tweet_id": reply_to,
            "exclude_reply_user_ids": [],
        }

    body = {
        "variables": variables,
        "features": TWEET_FEATURES,
        "queryId": GRAPHQL_QUERY_ID,
    }

    # Random human-like delay before posting
    time.sleep(random.uniform(1.5, 3.5))

    resp = cffi_requests.post(
        GRAPHQL_URL, json=body, headers=headers,
        impersonate="chrome131", timeout=20
    )

    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL error: {data['errors']}")

    tweet_id = (
        data.get("data", {})
        .get("create_tweet", {})
        .get("tweet_results", {})
        .get("result", {})
        .get("rest_id")
    )
    return {"success": True, "tweet_id": tweet_id}


# ───────────────────────────── tweepy/API mode ────────────────────────────────


def load_api_keys() -> dict:
    """Load tweepy credentials from file or environment."""
    keys = {}

    # Env vars take precedence
    for key in ["TWITTER_CONSUMER_KEY", "TWITTER_CONSUMER_SECRET",
                "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET"]:
        val = os.environ.get(key)
        if val:
            short = key.replace("TWITTER_", "").lower()
            keys[short] = val

    # Fall back to file
    if len(keys) < 4 and API_KEYS_FILE.exists():
        file_keys = json.loads(API_KEYS_FILE.read_text())
        keys.update(file_keys)

    required = ["consumer_key", "consumer_secret", "access_token", "access_token_secret"]
    missing = [k for k in required if k not in keys]
    if missing:
        raise FileNotFoundError(
            f"Missing API keys: {missing}. "
            f"Add to {API_KEYS_FILE} or set TWITTER_* env vars. "
            "See setup instructions at top of this file."
        )
    return keys


def post_tweet_tweepy(text: str, reply_to: str = None) -> dict:
    """Post via official X API v2 using tweepy."""
    try:
        import tweepy
    except ImportError:
        raise ImportError("tweepy not installed: pip3 install tweepy")

    keys = load_api_keys()
    client = tweepy.Client(
        consumer_key=keys["consumer_key"],
        consumer_secret=keys["consumer_secret"],
        access_token=keys["access_token"],
        access_token_secret=keys["access_token_secret"],
    )

    kwargs = {"text": text}
    if reply_to:
        kwargs["in_reply_to_tweet_id"] = reply_to

    response = client.create_tweet(**kwargs)
    tweet_id = response.data["id"]
    return {"success": True, "tweet_id": tweet_id}


# ─────────────────────────────────── main ────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Post to @claudemakes (no browser)")
    parser.add_argument("--dry-run", action="store_true", help="Verify account, don't post")
    parser.add_argument("--text", type=str, help="Tweet text to post")
    parser.add_argument("--reply-to", type=str, help="Tweet ID to reply to")
    parser.add_argument("--force", action="store_true", help="Bypass rate limit check")
    parser.add_argument(
        "--mode", choices=["cookie", "api", "auto"], default="auto",
        help="Posting mode: cookie (GraphQL), api (tweepy), auto (try api first)"
    )
    args = parser.parse_args()

    if not args.dry_run and not args.force:
        if not check_rate_limit():
            sys.exit(1)

    # Determine mode
    use_api = False
    if args.mode == "api":
        use_api = True
    elif args.mode == "auto":
        use_api = API_KEYS_FILE.exists() or any(
            os.environ.get(k) for k in ["TWITTER_CONSUMER_KEY", "TWITTER_ACCESS_TOKEN"]
        )

    if use_api:
        print("[~] Mode: tweepy (official API)")
        if args.dry_run:
            try:
                keys = load_api_keys()
                import tweepy
                client = tweepy.Client(
                    consumer_key=keys["consumer_key"],
                    consumer_secret=keys["consumer_secret"],
                    access_token=keys["access_token"],
                    access_token_secret=keys["access_token_secret"],
                )
                me = client.get_me()
                handle = me.data.username.lower()
                print(f"[+] Verified: @{handle}")
                if handle != EXPECTED_HANDLE:
                    print(f"[!] WRONG ACCOUNT: @{handle}")
                    sys.exit(1)
                print("[+] Dry run OK — not posting.")
            except Exception as e:
                print(f"[!] {e}")
                sys.exit(1)
            return

        if not args.text:
            print("[!] Provide --text")
            sys.exit(1)
        if len(args.text) > 280:
            print(f"[!] Too long ({len(args.text)} chars)")
            sys.exit(1)

        try:
            result = post_tweet_tweepy(args.text, reply_to=args.reply_to)
            print(f"[+] Posted! ID: {result['tweet_id']}")
            print(f"[+] URL: https://x.com/{EXPECTED_HANDLE}/status/{result['tweet_id']}")
            record_post()
        except Exception as e:
            print(f"[!] Failed: {e}")
            sys.exit(1)
    else:
        print("[~] Mode: cookie (GraphQL, no browser)")
        try:
            cookies = load_cookies()
        except Exception as e:
            print(f"[!] Cookie error: {e}")
            sys.exit(1)

        if args.dry_run:
            try:
                handle = verify_account_graphql(cookies)
                print(f"[+] Verified: @{handle}")
                if handle != EXPECTED_HANDLE:
                    print(f"[!] WRONG ACCOUNT: @{handle}")
                    sys.exit(1)
                print("[+] Dry run OK — not posting.")
            except Exception as e:
                print(f"[!] {e}")
                sys.exit(1)
            return

        if not args.text:
            print("[!] Provide --text or --dry-run")
            sys.exit(1)
        if len(args.text) > 280:
            print(f"[!] Too long ({len(args.text)} chars)")
            sys.exit(1)

        try:
            result = post_tweet_graphql(cookies, args.text, reply_to=args.reply_to)
            print(f"[+] Posted! ID: {result['tweet_id']}")
            print(f"[+] URL: https://x.com/{EXPECTED_HANDLE}/status/{result['tweet_id']}")
            record_post()
        except Exception as e:
            print(f"[!] Failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
