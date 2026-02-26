#!/usr/bin/env python3
"""Fetch Polymarket data and write pulse/data.json for the visualization."""

import json
import requests
from datetime import datetime, timezone

GAMMA = "https://gamma-api.polymarket.com"

def fetch_events(limit=50):
    """Fetch active events sorted by volume."""
    resp = requests.get(f"{GAMMA}/events", params={
        "active": True,
        "closed": False,
        "order": "volume24hr",
        "ascending": False,
        "limit": limit,
    })
    resp.raise_for_status()
    return resp.json()

def classify_category(title, tags):
    """Rough category classification from title and tags."""
    title_lower = title.lower()
    tag_set = set(t["label"].lower() if isinstance(t, dict) else t.lower() for t in (tags or []))

    if any(w in title_lower for w in ["bitcoin", "btc", "eth", "crypto", "solana"]):
        return "crypto"
    # "vs." is a strong sports signal
    if " vs. " in title_lower or " vs " in title_lower:
        return "sports"
    if any(w in title_lower for w in ["nba", "nfl", "mlb", "fifa", "ufc", "nhl", "champion", "super bowl", "world cup", "premier league", "stanley cup", "la liga", "ligue 1", "serie a", "mvp"]):
        return "sports"
    if any(w in title_lower for w in ["fed ", "interest rate", "inflation", "gdp", "recession", "stock", "s&p"]):
        return "economy"
    if any(w in title_lower for w in ["president", "elect", "trump", "democrat", "republican", "congress", "senate", "governor", "nominee", "vote"]):
        return "politics"
    if any(w in title_lower for w in ["elon", "musk", "tweet", "x.com"]):
        return "culture"
    if any(w in title_lower for w in ["ai ", "openai", "google", "apple", "tesla", "spacex", "tech"]):
        return "tech"
    if any(w in title_lower for w in ["iran", "ukraine", "russia", "china", "war", "strike", "nato"]):
        return "geopolitics"
    if any(w in title_lower for w in ["alien", "ufo", "climate", "earthquake", "pandemic"]):
        return "science"

    # Fallback from tags
    if "politics" in tag_set or "us-elections" in tag_set:
        return "politics"
    if "crypto" in tag_set:
        return "crypto"
    if "sports" in tag_set:
        return "sports"

    return "other"

def extract_market_data(event):
    """Extract clean market data from an event."""
    markets = event.get("markets", [])
    if not markets:
        return None

    title = event.get("title", "")
    volume = float(event.get("volume", 0) or 0)
    volume_24h = float(event.get("volume24hr", 0) or 0)
    tags = event.get("tags", [])
    category = classify_category(title, tags)

    # Find the most interesting market in the event
    # (highest volume or the "main" one)
    best_market = None
    best_volume = -1

    for m in markets:
        outcomes = m.get("outcomes", "[]")
        prices = m.get("outcomePrices", "[]")
        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)
        if isinstance(prices, str):
            prices = json.loads(prices)

        if not prices or not outcomes:
            continue

        mv = float(m.get("volume", 0) or 0)

        # For Yes/No markets, get the "Yes" probability
        prob = None
        if len(outcomes) == 2 and outcomes[0] == "Yes":
            prob = float(prices[0])
        elif len(outcomes) >= 2:
            # Multi-outcome: find the leading one
            max_idx = max(range(len(prices)), key=lambda i: float(prices[i]))
            prob = float(prices[max_idx])

        if mv > best_volume and prob is not None:
            best_volume = mv
            best_market = {
                "question": m.get("question", title),
                "outcomes": outcomes,
                "prices": [float(p) for p in prices],
                "probability": prob,
                "volume": mv,
            }

    if not best_market:
        return None

    # Calculate "uncertainty" — how close to 50/50
    # 0 = maximally certain, 1 = maximally uncertain
    p = best_market["probability"]
    uncertainty = 1.0 - abs(2 * p - 1)

    return {
        "title": title,
        "category": category,
        "volume": volume,
        "volume_24h": volume_24h,
        "uncertainty": round(uncertainty, 3),
        "market": best_market,
    }

def compute_interestingness(item):
    """Score how interesting a market is. High uncertainty + high volume = interesting."""
    vol_score = min(item["volume"] / 100_000_000, 1.0)  # normalize to ~$100M
    unc_score = item["uncertainty"]
    return 0.4 * vol_score + 0.6 * unc_score

def main():
    print("Fetching Polymarket events...")
    events = fetch_events(80)

    items = []
    for e in events:
        data = extract_market_data(e)
        if data and data["volume"] > 100_000:  # filter tiny markets
            data["interestingness"] = round(compute_interestingness(data), 3)
            items.append(data)

    # Sort by interestingness
    items.sort(key=lambda x: x["interestingness"], reverse=True)

    # Take top 40
    items = items[:40]

    # Category counts
    categories = {}
    for item in items:
        cat = item["category"]
        categories[cat] = categories.get(cat, 0) + 1

    output = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_events": len(events),
        "displayed": len(items),
        "categories": categories,
        "markets": items,
    }

    outpath = "pulse/data.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(items)} markets to {outpath}")
    print(f"Categories: {categories}")

    # Print the top 10 most interesting
    print("\nTop 10 most interesting markets:")
    for i, item in enumerate(items[:10]):
        p = item["market"]["probability"]
        print(f"  {i+1}. [{item['category']}] {item['title']}")
        print(f"     {p*100:.0f}% | uncertainty: {item['uncertainty']:.2f} | vol: ${item['volume']:,.0f}")

if __name__ == "__main__":
    main()
