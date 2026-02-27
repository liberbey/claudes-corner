#!/usr/bin/env python3
"""
Forecast Tracker — checks predictions against real-world data.
Run each session to monitor prediction status.
Fetches Bitcoin price, stock prices, Polymarket odds.
"""

import json
import requests
from datetime import datetime, timezone


def load_predictions():
    with open("forecast/predictions.json") as f:
        return json.load(f)


def get_bitcoin_price():
    """Fetch current Bitcoin price from CoinGecko."""
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["bitcoin"]["usd"]
    except Exception:
        return None


def get_stock_price(symbol):
    """Fetch stock price from Yahoo Finance."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"interval": "1d", "range": "1d"},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
    except Exception:
        return None


def load_polymarket_data():
    """Load the latest Pulse data for Polymarket odds."""
    try:
        with open("pulse/data.json") as f:
            return json.load(f)
    except Exception:
        return None


def find_polymarket_prob(pm_data, title_fragment):
    """Find a market's probability by title substring."""
    if not pm_data:
        return None
    for m in pm_data.get("markets", []):
        if title_fragment.lower() in m.get("title", "").lower():
            return m["market"]["probability"]
    return None


def check_prediction(pred, btc_price, nvda_price, pm_data):
    """Check a single prediction against current data. Returns status dict."""
    pid = pred["id"]

    if pred["status"] == "resolved":
        return {
            "id": pid,
            "status": "resolved",
            "outcome": pred["outcome"],
            "note": pred.get("resolution_note", ""),
        }

    days_left = (
        datetime.strptime(pred["deadline"], "%Y-%m-%d") - datetime.now()
    ).days

    result = {
        "id": pid,
        "statement": pred["statement"],
        "confidence": pred["confidence"],
        "deadline": pred["deadline"],
        "days_left": days_left,
        "status": "open",
        "current_data": {},
        "assessment": "",
        "trending": None,  # "toward" or "against" my prediction
    }

    # --- Prediction-specific checks ---

    if pid == "2026-02-27-001":
        # No US strike on Iran by March 31
        us_prob = find_polymarket_prob(pm_data, "US strikes Iran")
        israel_prob = find_polymarket_prob(pm_data, "Israel strikes Iran")
        if us_prob is not None:
            result["current_data"]["us_strike_polymarket"] = f"{us_prob*100:.0f}%"
        if israel_prob is not None:
            result["current_data"]["israel_strike_mar31"] = f"{israel_prob*100:.0f}%"
        result["assessment"] = (
            f"Geneva round 3 ended without deal. 'Significant progress.' "
            f"Technical talks Vienna next week. Market: US strike {us_prob*100:.0f}% near-term, "
            f"Israel strike {israel_prob*100:.0f}% by Mar 31."
            if us_prob and israel_prob
            else f"Check Polymarket manually. {days_left} days left."
        )
        if israel_prob and israel_prob < 0.5:
            result["trending"] = "toward"
        elif israel_prob and israel_prob >= 0.5:
            result["trending"] = "against"

    elif pid == "2026-02-27-002":
        # Bitcoin won't trade above $80K in March
        if btc_price:
            result["current_data"]["btc_price"] = f"${btc_price:,.0f}"
            gap = 80000 - btc_price
            gap_pct = (gap / btc_price) * 100
            if btc_price >= 80000:
                result["assessment"] = (
                    f"FALSIFIED. BTC at ${btc_price:,.0f}, crossed $80K."
                )
                result["trending"] = "against"
            else:
                result["assessment"] = (
                    f"BTC at ${btc_price:,.0f}. Needs +{gap_pct:.1f}% "
                    f"(${gap:,.0f}) to falsify."
                )
                result["trending"] = "toward"

    elif pid == "2026-02-27-004":
        # NVDA above $220 by June 30
        if nvda_price:
            result["current_data"]["nvda_price"] = f"${nvda_price:.2f}"
            gap = 220 - nvda_price
            gap_pct = (gap / nvda_price) * 100
            if nvda_price >= 220:
                result["assessment"] = (
                    f"CONFIRMED. NVDA at ${nvda_price:.2f}, crossed $220."
                )
                result["trending"] = "toward"
            else:
                result["assessment"] = (
                    f"NVDA at ${nvda_price:.2f}. Needs +{gap_pct:.1f}% "
                    f"(${gap:.0f}) to confirm."
                )
                result["trending"] = "against" if gap_pct > 25 else "neutral"

    elif pid == "2026-02-27-005":
        # No comprehensive Iran deal in 2026
        result["assessment"] = (
            "Round 3 concluded without deal. Structural gap remains: "
            "US demands zero enrichment, Iran insists on enrichment under IAEA. "
            "Technical talks Vienna next week."
        )
        result["trending"] = "toward"

    elif pid == "2026-02-27-006":
        # AI agent company acquired for $1B+
        result["assessment"] = (
            "No $1B+ acquisition announced. Agent market accelerating: "
            "Salesforce 29K Agentforce deals, Perplexity Computer launch, "
            "GitHub skills explosion."
        )
        result["trending"] = "neutral"

    elif pid == "2026-02-27-007":
        # EU defense below 2.5% GDP
        result["current_data"]["eu_defense_2025_est"] = "~2.1% GDP"
        result["assessment"] = (
            "EU at ~2.1% GDP (2025 est). 860B plan announced, NATO 5% target by 2035, "
            "but SAFE instrument just adopted. Procurement timelines are years, not months."
        )
        result["trending"] = "toward"

    elif pid == "2026-02-27-008":
        # Bitcoin won't reclaim $100K in 2026
        if btc_price:
            result["current_data"]["btc_price"] = f"${btc_price:,.0f}"
            gap = 100000 - btc_price
            gap_pct = (gap / btc_price) * 100
            if btc_price >= 100000:
                result["assessment"] = (
                    f"FALSIFIED. BTC at ${btc_price:,.0f}, crossed $100K."
                )
                result["trending"] = "against"
            else:
                result["assessment"] = (
                    f"BTC at ${btc_price:,.0f}. Needs +{gap_pct:.1f}% "
                    f"(${gap:,.0f}) to falsify. Long deadline."
                )
                result["trending"] = "toward"

    elif pid == "2026-02-27-009":
        # GitHub Agentic Workflows GA by Sept 2026
        result["assessment"] = (
            "Still in technical preview. No GA announcement. "
            "Competitive pressure from Cursor, Claude Code growing."
        )
        result["trending"] = "neutral"

    elif pid == "2026-02-27-010":
        # 5+ Dem 2028 candidates by Dec 31, 2026
        result["assessment"] = (
            "No formal declarations yet. WashPost ranked contenders (Feb 26). "
            "Buttigieg leads NH poll at 20%. Deep bench forming. "
            "FEC filings exist but no major announcements."
        )
        result["trending"] = "neutral"

    return result


def main():
    predictions = load_predictions()

    print("=" * 70)
    print("  FORECAST TRACKER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)
    print()

    # Fetch real data
    print("  Fetching live data...")
    btc_price = get_bitcoin_price()
    nvda_price = get_stock_price("NVDA")
    pm_data = load_polymarket_data()

    print(f"  Bitcoin:  ${btc_price:,.0f}" if btc_price else "  Bitcoin:  unavailable")
    print(f"  NVDA:     ${nvda_price:.2f}" if nvda_price else "  NVDA:     unavailable")
    print(f"  Pulse:    {pm_data['fetched_at'][:10]}" if pm_data else "  Pulse:    unavailable")
    print()

    # Check each prediction
    resolved_count = 0
    correct_count = 0
    results = []

    for pred in predictions:
        r = check_prediction(pred, btc_price, nvda_price, pm_data)
        results.append(r)
        if r["status"] == "resolved":
            resolved_count += 1
            if r.get("outcome"):
                correct_count += 1

    open_results = [r for r in results if r["status"] == "open"]
    resolved_results = [r for r in results if r["status"] == "resolved"]

    # Print resolved
    if resolved_results:
        print("  RESOLVED")
        print("  " + "-" * 40)
        for r in resolved_results:
            mark = "correct" if r["outcome"] else "wrong"
            print(f"  [{mark}] {r['id']}")
        print()

    # Print open, sorted by days left
    open_results.sort(key=lambda x: x.get("days_left", 9999))

    print("  OPEN PREDICTIONS")
    print("  " + "-" * 40)
    for r in open_results:
        days = r["days_left"]
        conf = r["confidence"]
        arrow = {"toward": "->", "against": "<-", "neutral": "--"}.get(
            r.get("trending"), "??"
        )
        urgency = "!!" if days <= 30 else "  "

        print(f"  {urgency}{r['id']}  conf:{conf*100:.0f}%  {days}d left  [{arrow}]")
        stmt = r["statement"]
        if len(stmt) > 72:
            stmt = stmt[:69] + "..."
        print(f"    \"{stmt}\"")
        print(f"    {r['assessment']}")
        for k, v in r.get("current_data", {}).items():
            print(f"    [{k}: {v}]")
        print()

    # Summary
    print("  " + "=" * 40)
    print(f"  Total: {len(predictions)}  |  Resolved: {resolved_count}  |  "
          f"Correct: {correct_count}  |  Open: {len(open_results)}")

    # Nearest deadlines
    nearest = sorted(open_results, key=lambda x: x.get("days_left", 9999))[:3]
    if nearest:
        parts = [f"{r['id']} ({r['days_left']}d)" for r in nearest]
        print(f"  Next deadlines: {', '.join(parts)}")
    print()

    # Save tracker output
    output = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "live_data": {
            "btc_price": btc_price,
            "nvda_price": nvda_price,
            "pulse_date": pm_data["fetched_at"][:10] if pm_data else None,
        },
        "summary": {
            "total": len(predictions),
            "resolved": resolved_count,
            "correct": correct_count,
            "open": len(open_results),
        },
        "results": results,
    }

    with open("forecast/tracker.json", "w") as f:
        json.dump(output, f, indent=2, default=str)

    print("  Saved → forecast/tracker.json")


if __name__ == "__main__":
    main()
