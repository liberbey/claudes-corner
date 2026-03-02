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


def get_hl_btc_funding():
    """Fetch BTC perpetual funding rate from Hyperliquid (24/7 source)."""
    try:
        resp = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "metaAndAssetCtxs"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        universe = data[0]["universe"]
        ctxs = data[1]
        for i, asset in enumerate(universe):
            if asset["name"] == "BTC":
                ctx = ctxs[i]
                funding = float(ctx.get("funding", 0))
                mark = float(ctx.get("markPx", 0))
                return {"funding_pct_hr": round(funding * 100, 5), "mark_price": round(mark, 0)}
    except Exception:
        pass
    return None


def load_polymarket_data():
    """Load the latest Pulse data for Polymarket odds."""
    try:
        with open("pulse/data.json") as f:
            return json.load(f)
    except Exception:
        return None


def fetch_polymarket_event(slug):
    """Fetch a specific Polymarket event by slug from the gamma API."""
    try:
        resp = requests.get(
            "https://gamma-api.polymarket.com/events",
            params={"slug": slug},
            timeout=10,
        )
        resp.raise_for_status()
        events = resp.json()
        return events[0] if events else None
    except Exception:
        return None


def find_market_prob_by_question(event, question_fragment):
    """Find a market's Yes probability within an event by question substring."""
    import json as _json
    if not event:
        return None
    for m in event.get("markets", []):
        q = m.get("question", "").lower()
        if question_fragment.lower() in q:
            prices = m.get("outcomePrices", "[]")
            if isinstance(prices, str):
                prices = _json.loads(prices)
            if prices:
                return float(prices[0])
    return None


def fetch_iran_strike_data():
    """Fetch current Iran strike probabilities from Polymarket."""
    result = {}
    # US strikes Iran by... (multi-date event)
    us_event = fetch_polymarket_event("us-strikes-iran-by")
    if us_event:
        result["us_strike_mar31"] = find_market_prob_by_question(
            us_event, "us strikes iran by march 31, 2026"
        )
        result["us_strike_jun30"] = find_market_prob_by_question(
            us_event, "us strikes iran by june 30, 2026"
        )
    # Israel strikes Iran by March 31
    il_event = fetch_polymarket_event("israel-strikes-iran-by-march-31-2026")
    if il_event:
        result["israel_strike_mar31"] = find_market_prob_by_question(
            il_event, "israel strikes iran by march 31, 2026"
        )
    return result


def find_polymarket_prob(pm_data, title_fragment):
    """Find a market's probability by title substring in Pulse data."""
    if not pm_data:
        return None
    for m in pm_data.get("markets", []):
        if title_fragment.lower() in m.get("title", "").lower():
            return m["market"]["probability"]
    return None


def check_prediction(pred, btc_price, nvda_price, pm_data, iran_data=None, brent_price=None, extra_data=None):
    """Check a single prediction against current data. Returns status dict."""
    pid = pred["id"]
    if iran_data is None:
        iran_data = {}
    if extra_data is None:
        extra_data = {}

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
        "extra_data": extra_data,
    }

    # --- Prediction-specific checks ---

    if pid == "2026-02-27-001":
        # No US strike on Iran by March 31
        us_mar31 = iran_data.get("us_strike_mar31")
        il_mar31 = iran_data.get("israel_strike_mar31")
        if us_mar31 is not None:
            result["current_data"]["us_strike_mar31"] = f"{us_mar31*100:.0f}%"
        if il_mar31 is not None:
            result["current_data"]["israel_strike_mar31"] = f"{il_mar31*100:.0f}%"
        if us_mar31 is not None and il_mar31 is not None:
            result["assessment"] = (
                f"Market: US strike by Mar 31 at {us_mar31*100:.0f}%, "
                f"Israel strike by Mar 31 at {il_mar31*100:.0f}%. "
                f"Vienna technical talks Monday. {days_left} days left."
            )
        else:
            result["assessment"] = f"Check Polymarket manually. {days_left} days left."
        if us_mar31 and us_mar31 >= 0.5:
            result["trending"] = "against"
        else:
            result["trending"] = "toward"

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

    elif pid == "2026-02-27-011":
        # US or Israeli strike on Iran by April 15
        us_mar31 = iran_data.get("us_strike_mar31")
        il_mar31 = iran_data.get("israel_strike_mar31")
        if us_mar31 is not None:
            result["current_data"]["us_strike_mar31"] = f"{us_mar31*100:.0f}%"
        if il_mar31 is not None:
            result["current_data"]["israel_strike_mar31"] = f"{il_mar31*100:.0f}%"
        if us_mar31 is not None:
            result["assessment"] = (
                f"Market: US strike by Mar 31 at {us_mar31*100:.0f}%. "
                f"Two carrier groups in position. Vienna talks Monday."
            )
        result["trending"] = "toward" if (us_mar31 and us_mar31 >= 0.5) else "neutral"

    elif pid == "2026-02-27-012":
        # Morgan Stanley BTC custody before Sept 2026
        result["assessment"] = (
            "No launch timeline announced. Regulatory approvals, compliance "
            "infrastructure, insurance frameworks all pending."
        )
        result["trending"] = "toward"

    elif pid == "2026-02-27-013":
        # Section 122 tariffs expire July 24
        result["assessment"] = (
            "Section 122 invoked Feb 24 at 10%. 150-day clock expires July 24. "
            "No extension bill introduced. Business-aligned GOP faction quietly hostile."
        )
        result["trending"] = "toward"

    elif pid == "2026-02-27-014":
        # No G7 trade deal in 2026
        result["assessment"] = (
            "EU postponed trade vote 2x. India paused talks. "
            "Section 122 deadline (July 24) gives partners incentive to wait."
        )
        result["trending"] = "toward"

    elif pid == "2026-02-28-015":
        # Pakistan-Afghanistan ceasefire by April 15
        result["assessment"] = (
            "Open warfare. Both capitals struck. Pakistan declared 'open war.' "
            "Afghanistan retaliated. UN, China, Qatar, Turkey mediating."
        )
        result["trending"] = "against"

    elif pid == "2026-02-28-017":
        # Brent > $100 in 14 days (deadline March 14)
        if brent_price:
            result["current_data"]["brent_price"] = f"${brent_price:.2f}"
            gap = 100 - brent_price
            gap_pct = (gap / brent_price) * 100 if brent_price < 100 else 0
            if brent_price >= 100:
                result["assessment"] = f"CONFIRMED. Brent at ${brent_price:.2f}, crossed $100."
                result["trending"] = "toward"
            else:
                result["assessment"] = (
                    f"Brent at ${brent_price:.2f}. Needs +{gap_pct:.1f}% to hit $100 "
                    f"in {days_left} days. IRGC announced Hormuz closure; market unmoved. "
                    "Bypass pipelines (IPSA 5.9M bbl/day) absorbing flow."
                )
                result["trending"] = "against"
        else:
            result["assessment"] = f"Brent unavailable. {days_left} days to March 14 deadline."
            result["trending"] = "against"

    elif pid == "2026-02-28-018":
        # Iran regime survives to Feb 28, 2027
        result["assessment"] = (
            "Khamenei status contested. IRGC functional. Assembly of Experts "
            "convening for succession. Regime institution outlasts any leader."
        )
        result["trending"] = "toward"

    elif pid == "2026-02-28-019":
        # No Hormuz closure in 30 days
        if brent_price:
            result["current_data"]["brent_price"] = f"${brent_price:.2f}"
            result["assessment"] = (
                f"IRGC announced closure March 1. Ships at Fujairah. Brent at "
                f"${brent_price:.2f} — market pricing partial/temporary disruption, "
                "not sustained blockade. Bypass pipelines active."
            )
        else:
            result["assessment"] = (
                "IRGC announced Hormuz closure March 1. Ships piling at Fujairah. "
                "Brent barely moved (~3%) — market not pricing sustained blockade."
            )
        result["trending"] = "against"  # trending against "no closure" = closure is happening

    elif pid == "2026-02-28-020":
        # US air ops ongoing March 29
        result["assessment"] = (
            "Trump: 'major combat operations,' 'weeks-long sustained operations.' "
            "Iran struck US bases — domestic justification to continue. "
            "War Powers Resolution vote next week."
        )
        result["trending"] = "toward"

    elif pid == "2026-02-28-022":
        # US-Iran negotiations resume by April 15
        result["assessment"] = (
            "Strikes destroyed nuclear infrastructure — no Iranian enrichment to negotiate over. "
            "US has no incentive to negotiate: military campaign ongoing. "
            "Iran has no regime continuity: Khamenei dead, succession in progress. "
            "Who would negotiate on the Iranian side? Deadline April 15."
        )
        result["trending"] = "toward"  # trending toward 'no negotiations'

    elif pid == "2026-02-28-023":
        # Congress won't terminate military ops by April 1
        result["assessment"] = (
            "War Powers 60-day clock: April 28. Congress has never successfully "
            "invoked WPR termination in history. Bipartisan majority unlikely — "
            "hawks want continued ops, many Democrats see Iran as threat. "
            "Motion to terminate would need 218 House + 50 Senate."
        )
        result["trending"] = "toward"

    elif pid == "2026-03-01-025":
        # Assembly of Experts announces new Supreme Leader by April 1
        result["assessment"] = (
            "Assembly of Experts convening. 1989 precedent: succession took 1 week. "
            "Khamenei confirmed dead by US officials. The question is who — "
            "Mojtaba Khamenei (son), Raisi's successor, or compromise candidate. "
            "Speed of announcement is an institutional health signal. Deadline April 1."
        )
        result["trending"] = "toward"

    elif pid == "2026-03-01-026":
        # 25% Canada/Mexico tariffs lifted/paused/exempted by June 1
        result["assessment"] = (
            "Tariffs effective March 4. Canada/Mexico retaliated in kind. "
            "Auto industry lobbying hard — Ford/GM supply chains cross border 6x. "
            "Historical pattern: Trump tariffs often followed by partial exemptions. "
            "USMCA review clause and domestic manufacturing pressure will intensify."
        )
        result["trending"] = "against"  # tariffs looking sticky

    elif pid == "2026-03-01-027":
        # Major NA auto manufacturer pauses production by March 18
        result["assessment"] = (
            "25% tariffs on parts crossing US-Canada-Mexico border. "
            "JIT supply chains cannot absorb 25% cost spike without pausing. "
            "Ford already warned of $1.5B annual impact. "
            "GM, Stellantis have Mexican assembly plants feeding US models. "
            "Q: does management have 14 days of buffer stock to delay the decision?"
        )
        result["trending"] = "toward"

    elif pid == "2026-03-02-028":
        # USD/CAD closes above 1.44 between March 4-6
        usdcad = result.get("extra_data", {}).get("usdcad")
        if usdcad:
            result["current_data"]["usd_cad"] = f"{usdcad:.4f}"
            gap = 1.44 - usdcad
            gap_pct = (gap / usdcad) * 100
            if usdcad >= 1.44:
                result["assessment"] = f"CONFIRMED. USD/CAD at {usdcad:.4f}, above 1.44."
                result["trending"] = "toward"
            else:
                result["assessment"] = (
                    f"USD/CAD at {usdcad:.4f}. Needs +{gap_pct:.1f}% to reach 1.44. "
                    f"Market still pricing deal, not tariff shock. "
                    f"March 4 is the test."
                )
                result["trending"] = "against"
        else:
            result["assessment"] = "USD/CAD unavailable. Requires tariff shock to drive CAD from 1.37 to 1.44."
            result["trending"] = "against"

    elif pid == "2026-03-02-029":
        # Tariffs go live March 4 without suspension
        usdcad = result.get("extra_data", {}).get("usdcad")
        if usdcad:
            result["current_data"]["usd_cad"] = f"{usdcad:.4f}"
            if usdcad < 1.40:
                result["assessment"] = (
                    f"USD/CAD at {usdcad:.4f} — market still pricing deal, not tariffs. "
                    f"25% effective March 4. No suspension/exemption announced yet. "
                    f"Resolve manually after March 4."
                )
            else:
                result["assessment"] = (
                    f"USD/CAD at {usdcad:.4f} — market beginning to price tariff risk. "
                    f"Resolve manually after March 4."
                )
        else:
            result["assessment"] = "Manual resolution required on March 4. No price proxy."
        result["trending"] = "toward"  # my base case is tariffs go live

    elif pid == "2026-03-02-031":
        # Gold stays within 2% of $5,426 on March 4-5
        gold = result.get("extra_data", {}).get("gold")
        if gold:
            result["current_data"]["gold"] = f"${gold:,.0f}"
            threshold = 5426 * 0.98  # 2% below context price
            if gold < threshold:
                result["assessment"] = f"ALERT. Gold at ${gold:,.0f}, below $5,317 threshold. Two-clock thesis challenged."
                result["trending"] = "against"
            else:
                pct_from_ref = (gold - 5426) / 5426 * 100
                result["assessment"] = (
                    f"Gold at ${gold:,.0f} ({pct_from_ref:+.1f}% from $5,426 reference). "
                    f"Resolves March 5. Testing whether gold reacts to tariff news."
                )
                result["trending"] = "toward"
        else:
            result["assessment"] = f"Gold data unavailable. {days_left} days to March 5."
            result["trending"] = "neutral"

    elif pid == "2026-03-02-030":
        # S&P 500 stays above 6,400 through March 14
        sp500 = result.get("extra_data", {}).get("sp500")
        if sp500:
            result["current_data"]["sp500"] = f"{sp500:,.0f}"
            buffer = sp500 - 6400
            buffer_pct = (buffer / sp500) * 100
            if sp500 < 6400:
                result["assessment"] = f"FALSIFIED. S&P at {sp500:,.0f}, below 6,400."
                result["trending"] = "against"
            else:
                result["assessment"] = (
                    f"S&P at {sp500:,.0f}. Buffer: +{buffer:.0f} pts ({buffer_pct:.1f}%). "
                    f"Would need -{buffer_pct:.1f}% drop to falsify. "
                    f"{days_left} days left."
                )
                result["trending"] = "toward"
        else:
            result["assessment"] = f"S&P data unavailable. {days_left} days left."
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
    brent_price = get_stock_price("BZ=F")
    sp500_price = get_stock_price("^GSPC")
    cadusd_price = get_stock_price("CADUSD=X")
    usdcad_price = round(1 / cadusd_price, 4) if cadusd_price else None
    hl_btc = get_hl_btc_funding()
    pm_data = load_polymarket_data()

    gold_price = get_stock_price("GC=F")

    extra_data = {
        "sp500": sp500_price,
        "usdcad": usdcad_price,
        "gold": gold_price,
    }

    print(f"  Bitcoin:  ${btc_price:,.0f}" if btc_price else "  Bitcoin:  unavailable")
    print(f"  NVDA:     ${nvda_price:.2f}" if nvda_price else "  NVDA:     unavailable")
    print(f"  Brent:    ${brent_price:.2f}" if brent_price else "  Brent:    unavailable")
    print(f"  S&P 500:  {sp500_price:,.0f}" if sp500_price else "  S&P 500:  unavailable")
    print(f"  USD/CAD:  {usdcad_price:.4f}" if usdcad_price else "  USD/CAD:  unavailable")
    print(f"  Gold:     ${gold_price:,.0f}" if gold_price else "  Gold:     unavailable")
    if hl_btc:
        print(f"  HL BTC:   mark=${hl_btc['mark_price']:,.0f}  funding={hl_btc['funding_pct_hr']:+.4f}%/hr")
    print(f"  Pulse:    {pm_data['fetched_at'][:10]}" if pm_data else "  Pulse:    unavailable")

    iran_data = fetch_iran_strike_data()
    if iran_data:
        us_m = iran_data.get("us_strike_mar31")
        il_m = iran_data.get("israel_strike_mar31")
        if us_m is not None:
            print(f"  Iran:     US strike Mar31 {us_m*100:.0f}%, Israel {il_m*100:.0f}%" if il_m else f"  Iran:     US strike Mar31 {us_m*100:.0f}%")
    print()

    # Check each prediction
    resolved_count = 0
    correct_count = 0
    results = []

    for pred in predictions:
        r = check_prediction(pred, btc_price, nvda_price, pm_data, iran_data, brent_price, extra_data)
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
            "brent_price": brent_price,
            "sp500": sp500_price,
            "usdcad": usdcad_price,
            "gold": gold_price,
            "hl_btc_funding": hl_btc,
            "pulse_date": pm_data["fetched_at"][:10] if pm_data else None,
        },
        "summary": {
            "total": len(predictions),
            "resolved": resolved_count,
            "correct": correct_count,
            "open": len(open_results),
        },
        "results": [{k: v for k, v in r.items() if k != "extra_data"} for r in results],
    }

    with open("forecast/tracker.json", "w") as f:
        json.dump(output, f, indent=2, default=str)

    print("  Saved → forecast/tracker.json")


if __name__ == "__main__":
    main()
