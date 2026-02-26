#!/usr/bin/env python3
"""
Diamond Blitz Economy Model
============================
Emir's feedback: the gap between "Expected Dice" and simulated dice exists
because Diamond Blitz Stage 1 wasn't modeled. He said: "I took only the
first stage of the diamond blitz into account, assuming players would stop
there on average."

This script models Diamond Blitz Stage 1 and shows how it closes the gap.

Diamond Blitz Stage 1 parameters (from CLAUDE.md):
- 955 dice needed to complete all 15 milestones
- 62.86% dice giveback (= 600 dice returned from milestones)
- 97.52% meta money coverage (milestone money = 97.52% of building cost)
- Crystal overlay: 10% = 10 diamonds, 13% = 2 diamonds, 17% = 1 diamond
- Expected diamonds per die: 1.43
- Money amounts are Meta 2 based, scaled by meta multiplier
"""

import json
import csv
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field

GAME_DATA_DIR = Path(__file__).parent.parent.parent / "game-economy-difficulty" / "reference"

# Diamond Blitz Stage 1 constants
DB_DICE_TO_COMPLETE = 955       # dice rolls needed to finish Step 1
DB_DICE_GIVEBACK_PCT = 0.6286   # 62.86% of dice given back as rewards
DB_MONEY_COVERAGE_PCT = 0.9752  # milestone money = 97.52% of building cost
DB_DICE_GIVEBACK = int(DB_DICE_TO_COMPLETE * DB_DICE_GIVEBACK_PCT)  # ~600 dice

# ─── Data Loading ─────────────────────────────────────────────────────────

def parse_number(s: str) -> int:
    return int(s.replace(",", "").strip())


def load_data():
    """Load dice economy CSV and building costs JSON."""
    csv_path = GAME_DATA_DIR / "Game Economy_ Dice - all.csv"
    json_path = GAME_DATA_DIR / "output" / "city_pricing_data_v6.json"

    # Dice economy per meta
    metas = {}
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            meta = int(row["Meta"])
            metas[meta] = {
                "meta": meta,
                "meta_multiplier": float(row["Meta Multiplier"]),
                "total_multiplier": float(row["Total Multiplier"]),
                "expected_dice": int(row["Expected Dice"]),
                "total_reward": parse_number(row["Total Reward"]),
                # Probabilities
                "triple_jackpot_pct": float(row["Triple Jackpot % "]) / 100,
                "triple_money_pct": float(row["Triple Money %"]) / 100,
                "triple_mystery_pct": float(row["Triple ? %"]) / 100,
                "triple_attack_pct": float(row["Triple Attack %"]) / 100,
                "triple_heist_pct": float(row["Triple Heist %"]) / 100,
                "triple_shield_pct": float(row["Triple Shield %"]) / 100,
                "two_jp_pct": float(row["2 JP %"]) / 100,
                "one_jp_pct": float(row["1 JP %"]) / 100,
                "two_money_pct": float(row["2 Money %"]) / 100,
                "one_money_pct": float(row["1 Money %"]) / 100,
                # Per-roll rewards
                "jackpot_1": parse_number(row["Jackpot 1"]),
                "jackpot_2": parse_number(row["Jackpot 2"]),
                "jackpot_3": parse_number(row["Jackpot 3"]),
                "money_1": parse_number(row["Money 1"]),
                "money_2": parse_number(row["Money 2"]),
                "money_3": parse_number(row["Money 3"]),
                "attack_expected": parse_number(row["Attack (E)"]),
                "heist_expected": parse_number(row["Heist (E)"]),
            }

    # Building costs
    with open(json_path) as f:
        data = json.load(f)
    for entry in data:
        meta = entry["Index"] + 1
        if meta in metas:
            prices = [lp["UpgradePrice"] for b in entry["BuildingPriceData"]
                      for lp in b["LevelPrices"]]
            metas[meta]["building_cost"] = sum(prices)

    return metas


def compute_ev_per_die(m: dict) -> float:
    """Compute expected money per die roll from probabilities and rewards."""
    mystery_money = int(m["money_2"] * 0.75)
    outcomes = [
        (m["triple_jackpot_pct"], m["jackpot_3"]),
        (m["triple_money_pct"], m["money_3"]),
        (m["triple_mystery_pct"], mystery_money),
        (m["triple_attack_pct"], m["attack_expected"]),
        (m["triple_heist_pct"], m["heist_expected"]),
        (m["triple_shield_pct"], 0),
        (m["two_jp_pct"], m["jackpot_2"]),
        (m["one_jp_pct"], m["jackpot_1"]),
        (m["two_money_pct"], m["money_2"]),
        (m["one_money_pct"], m["money_1"]),
    ]
    return sum(p * r for p, r in outcomes)


# ─── Monte Carlo: dice needed per meta ────────────────────────────────────

def simulate_dice_needed(m: dict, n_players: int = 3000) -> dict:
    """Simulate how many dice to complete a meta (pure dice, no events)."""
    ev = compute_ev_per_die(m)
    if ev <= 0:
        return None

    building_cost = m.get("building_cost", 0)
    if building_cost == 0:
        return None

    # Build cumulative probability table for numpy
    mystery_money = int(m["money_2"] * 0.75)
    probs_raw = [
        m["triple_jackpot_pct"], m["triple_money_pct"], m["triple_mystery_pct"],
        m["triple_attack_pct"], m["triple_heist_pct"], m["triple_shield_pct"],
        m["two_jp_pct"], m["one_jp_pct"], m["two_money_pct"], m["one_money_pct"],
    ]
    rewards = np.array([
        m["jackpot_3"], m["money_3"], mystery_money,
        m["attack_expected"], m["heist_expected"], 0,
        m["jackpot_2"], m["jackpot_1"], m["money_2"], m["money_1"], 0
    ], dtype=np.int64)

    remainder = 1.0 - sum(probs_raw)
    probs_raw.append(max(0, remainder))
    probs = np.cumsum(probs_raw)
    probs[-1] = 1.0

    max_dice = int(building_cost / ev * 5) + 200

    all_dice = []
    chunk = min(500, n_players)
    remaining = n_players

    while remaining > 0:
        batch = min(chunk, remaining)
        remaining -= batch

        rolls = np.random.random((batch, max_dice))
        outcomes = np.searchsorted(probs, rolls)
        money = rewards[outcomes]
        cumsum = np.cumsum(money, axis=1)

        reached = cumsum >= building_cost
        dice_needed = np.argmax(reached, axis=1) + 1
        not_finished = ~np.any(reached, axis=1)
        dice_needed[not_finished] = max_dice

        all_dice.extend(dice_needed.tolist())

    return {
        "dice_counts": all_dice,
        "ev_per_die": ev,
        "p25": int(np.percentile(all_dice, 25)),
        "p50": int(np.percentile(all_dice, 50)),
        "p75": int(np.percentile(all_dice, 75)),
    }


# ─── Diamond Blitz Model ─────────────────────────────────────────────────

def model_diamond_blitz(m: dict, ev_per_die: float) -> dict:
    """Model Diamond Blitz Stage 1 impact on a single meta.

    Two key effects:
    1. MONEY: DB milestones give money = 97.52% of building cost
       → Player only needs dice income to cover remaining 2.48%
    2. DICE: DB gives back 62.86% of dice rolled (up to 600 on 955 dice)
       → Net dice consumed = dice_rolled * (1 - 0.6286)

    The model: player plays through a meta while DB is active.
    Total money = dice_rolls * EV + DB_money_bonus
    We find how many dice to roll so total money >= building_cost.
    Then account for dice giveback.
    """
    building_cost = m.get("building_cost", 0)
    if building_cost == 0 or ev_per_die <= 0:
        return None

    db_money = DB_MONEY_COVERAGE_PCT * building_cost
    remaining_cost = building_cost - db_money  # 2.48% of building cost

    # Dice needed to cover remaining cost from normal rolls
    dice_for_money = remaining_cost / ev_per_die

    # But DB rewards are unlocked proportionally as you roll (milestones)
    # If dice_for_money < 955: you don't complete all milestones
    # Scale DB rewards proportionally
    if dice_for_money < DB_DICE_TO_COMPLETE:
        # Player completes meta before finishing DB
        # They earn proportional DB rewards
        progress_fraction = dice_for_money / DB_DICE_TO_COMPLETE
        actual_db_money = progress_fraction * db_money

        # Iterative solve: need D dice where D * EV + (D/955) * db_money >= building_cost
        # D * (EV + db_money / 955) >= building_cost
        effective_ev = ev_per_die + db_money / DB_DICE_TO_COMPLETE
        dice_needed = building_cost / effective_ev

        # Dice giveback (proportional)
        giveback = dice_needed * DB_DICE_GIVEBACK_PCT
        net_dice = dice_needed - giveback
    else:
        # Player needs more than 955 dice for the meta
        # Full DB rewards: 600 dice back + 97.52% money
        dice_needed = dice_for_money
        giveback = DB_DICE_GIVEBACK
        net_dice = dice_needed - giveback

    return {
        "dice_needed_with_db": max(1, dice_needed),
        "net_dice_with_db": max(1, net_dice),
        "db_money": db_money,
        "dice_giveback": giveback,
        "db_progress_pct": min(100, dice_needed / DB_DICE_TO_COMPLETE * 100),
    }


# ─── Main Analysis ───────────────────────────────────────────────────────

def main():
    np.random.seed(42)
    metas = load_data()

    print("=" * 110)
    print("DIAMOND BLITZ IMPACT ON DICE ECONOMY")
    print("Modeling DB Stage 1: 955 dice → 600 back (62.86%) + money = 97.52% of building cost")
    print("=" * 110)
    print()

    # Run sim and compute DB model for each meta
    results = []
    for meta_num in range(2, 21):
        m = metas.get(meta_num)
        if not m or not m.get("building_cost"):
            continue

        sim = simulate_dice_needed(m, n_players=3000)
        if not sim:
            continue

        ev = sim["ev_per_die"]
        db = model_diamond_blitz(m, ev)
        if not db:
            continue

        results.append({
            "meta": meta_num,
            "building_cost": m["building_cost"],
            "expected_dice": m["expected_dice"],
            "total_reward": m["total_reward"],
            "ev_per_die": ev,
            "sim_p50": sim["p50"],
            "sim_p25": sim["p25"],
            "sim_p75": sim["p75"],
            **db,
        })

    # ─── Table 1: The Gap With and Without Diamond Blitz ──────────────

    print("TABLE 1: DICE NEEDED — Without DB vs With DB vs CSV Expected")
    print(f"{'Meta':>4} │ {'Build Cost':>11} │ {'No DB(p50)':>10} │ {'With DB':>10} │ {'Net(DB)':>10} │ {'CSV Exp':>8} │ {'Net≈Exp?':>8}")
    print("─" * 90)

    total_no_db = 0
    total_with_db = 0
    total_net_db = 0
    total_expected = 0

    for r in results:
        no_db = r["sim_p50"]
        with_db = r["dice_needed_with_db"]
        net_db = r["net_dice_with_db"]
        expected = r["expected_dice"]

        total_no_db += no_db
        total_with_db += with_db
        total_net_db += net_db
        total_expected += expected

        # Does net dice with DB approximately match Expected Dice?
        if expected > 0:
            ratio = net_db / expected
            match = "✓" if 0.5 < ratio < 2.0 else "✗"
            ratio_str = f"{ratio:.2f}x"
        else:
            match = "—"
            ratio_str = "—"

        print(f"{r['meta']:>4} │ {r['building_cost']:>11,} │ {no_db:>10,} │ {with_db:>10,.0f} │ {net_db:>10,.0f} │ {expected:>8,} │ {ratio_str:>8}")

    print("─" * 90)
    print(f"{'SUM':>4} │ {'':>11} │ {total_no_db:>10,} │ {total_with_db:>10,.0f} │ {total_net_db:>10,.0f} │ {total_expected:>8,} │")
    print()

    # ─── Table 2: Diamond Blitz Money Coverage ────────────────────────

    print("TABLE 2: DIAMOND BLITZ MONEY CONTRIBUTION PER META")
    print(f"{'Meta':>4} │ {'Build Cost':>11} │ {'DB Money':>11} │ {'Dice Money':>11} │ {'DB %':>6} │ {'Dice %':>7} │ {'Total $':>11}")
    print("─" * 85)

    for r in results:
        db_money = r["db_money"]
        dice_money = r["dice_needed_with_db"] * r["ev_per_die"]
        total_money = db_money + dice_money
        db_pct = db_money / r["building_cost"] * 100
        dice_pct = dice_money / r["building_cost"] * 100

        print(f"{r['meta']:>4} │ {r['building_cost']:>11,} │ {db_money:>11,.0f} │ {dice_money:>11,.0f} │ {db_pct:>5.1f}% │ {dice_pct:>6.1f}% │ {total_money:>11,.0f}")

    print()

    # ─── Table 3: CSV Expected Dice Validation ────────────────────────

    print("TABLE 3: VALIDATING CSV 'EXPECTED DICE'")
    print("Does Total Reward (money from Expected Dice) + DB money ≈ Building Cost?")
    print()
    print(f"{'Meta':>4} │ {'Total Reward':>12} │ {'DB Money':>12} │ {'Sum':>12} │ {'Build Cost':>12} │ {'Coverage':>9}")
    print("─" * 80)

    for r in results:
        total_reward = r["total_reward"]
        db_money = r["db_money"]
        total = total_reward + db_money
        coverage = total / r["building_cost"] * 100

        indicator = "✓" if coverage >= 95 else "~" if coverage >= 80 else "✗"

        print(f"{r['meta']:>4} │ {total_reward:>12,} │ {db_money:>12,.0f} │ {total:>12,.0f} │ {r['building_cost']:>12,} │ {coverage:>7.1f}% {indicator}")

    print()

    # ─── Table 4: DB Dice Giveback Impact ─────────────────────────────

    print("TABLE 4: DIAMOND BLITZ DICE GIVEBACK")
    print(f"{'Meta':>4} │ {'Dice Rolled':>11} │ {'DB Giveback':>11} │ {'Net Dice':>10} │ {'Savings %':>9} │ {'DB Progress':>11}")
    print("─" * 75)

    for r in results:
        dice_rolled = r["dice_needed_with_db"]
        giveback = r["dice_giveback"]
        net = r["net_dice_with_db"]
        savings = giveback / dice_rolled * 100 if dice_rolled > 0 else 0
        progress = r["db_progress_pct"]

        print(f"{r['meta']:>4} │ {dice_rolled:>11,.0f} │ {giveback:>11,.0f} │ {net:>10,.0f} │ {savings:>8.1f}% │ {progress:>10.1f}%")

    print()

    # ─── Findings ─────────────────────────────────────────────────────

    print("=" * 90)
    print("FINDINGS")
    print("=" * 90)
    print()

    # Check how well Total Reward + DB money covers building cost
    good_coverage = sum(1 for r in results
                        if (r["total_reward"] + r["db_money"]) / r["building_cost"] >= 0.95)
    total_metas = len(results)

    print(f"1. CSV EXPECTED DICE + DIAMOND BLITZ = BUILDING COST?")
    print(f"   Total Reward (money from Expected Dice) + DB money (97.52% of cost)")
    print(f"   covers ≥95% of building cost for {good_coverage}/{total_metas} metas.")
    print()

    # Show the overshoot/undershoot
    print(f"   Coverage by meta:")
    for r in results:
        total = r["total_reward"] + r["db_money"]
        coverage = total / r["building_cost"] * 100
        bar = "█" * min(50, int(coverage / 2))
        print(f"   Meta {r['meta']:>2}: {bar:<50} {coverage:.0f}%")
    print()

    print(f"2. THE 'GAP' EXPLAINED")
    gap_without = total_no_db - total_expected
    gap_with = total_net_db - total_expected
    print(f"   Without DB: sim needs {total_no_db:,} dice, CSV says {total_expected:,} → gap of {gap_without:,}")
    print(f"   With DB:    sim needs {total_net_db:,.0f} net dice, CSV says {total_expected:,} → gap of {gap_with:,.0f}")
    print()

    reduction = (1 - total_net_db / total_no_db) * 100
    print(f"3. DIAMOND BLITZ REDUCES TOTAL DICE BY {reduction:.0f}%")
    print(f"   From {total_no_db:,} → {total_net_db:,.0f} net dice across metas 2-20")
    print()

    # Progression impact
    def dice_to_days(dice):
        # With win streak: 52 dice per 10 levels, 2 min/level, 3 hrs/day
        levels = dice / 52 * 10
        hours = levels * 2 / 60
        return hours / 3

    days_no_db = dice_to_days(total_no_db)
    days_with_db = dice_to_days(total_net_db)

    print(f"4. PROGRESSION TIMELINE")
    print(f"   Without DB: {total_no_db:,} dice → {days_no_db:.0f} days to Meta 20")
    print(f"   With DB:    {total_net_db:,.0f} dice → {days_with_db:.0f} days to Meta 20")
    print(f"   DB saves {days_no_db - days_with_db:.0f} days ({(1 - days_with_db/days_no_db)*100:.0f}% faster)")
    print()

    # Generate chart
    generate_chart(results)


# ─── Chart ────────────────────────────────────────────────────────────────

def generate_chart(results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Diamond Blitz Impact on Match Squad Dice Economy", fontsize=14, fontweight="bold", y=0.98)

    metas = [r["meta"] for r in results]

    # ─── Panel 1: Dice Needed (No DB vs With DB vs Expected) ──────

    ax1 = axes[0, 0]
    no_db = [r["sim_p50"] for r in results]
    net_db = [r["net_dice_with_db"] for r in results]
    expected = [r["expected_dice"] for r in results]

    ax1.plot(metas, no_db, "o-", color="#e74c3c", linewidth=2, markersize=5, label="Without DB (sim p50)")
    ax1.plot(metas, net_db, "s-", color="#3498db", linewidth=2, markersize=5, label="With DB (net dice)")
    ax1.plot(metas, expected, "^--", color="#27ae60", linewidth=2, markersize=5, label="CSV Expected Dice")
    ax1.fill_between(metas, net_db, no_db, alpha=0.15, color="#e74c3c", label="DB savings")
    ax1.set_xlabel("Meta")
    ax1.set_ylabel("Dice")
    ax1.set_title("Dice Needed Per Meta")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)

    # ─── Panel 2: Money Sources (DB vs Dice Rolling) ──────────────

    ax2 = axes[0, 1]
    db_money_pct = [r["db_money"] / r["building_cost"] * 100 for r in results]
    dice_money = [r["dice_needed_with_db"] * r["ev_per_die"] for r in results]
    dice_money_pct = [d / r["building_cost"] * 100 for d, r in zip(dice_money, results)]

    width = 0.6
    ax2.bar(metas, db_money_pct, width, color="#f39c12", alpha=0.8, label="Diamond Blitz money")
    ax2.bar(metas, dice_money_pct, width, bottom=db_money_pct, color="#3498db", alpha=0.8, label="Dice roll money")
    ax2.axhline(y=100, color="#2c3e50", linewidth=1.5, linestyle="--", alpha=0.5, label="Building cost (100%)")
    ax2.set_xlabel("Meta")
    ax2.set_ylabel("% of Building Cost")
    ax2.set_title("Money Sources: DB vs Dice Rolls")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3, axis="y")
    ax2.set_ylim(0, 200)

    # ─── Panel 3: CSV Validation ──────────────────────────────────

    ax3 = axes[1, 0]
    csv_coverage = [(r["total_reward"] + r["db_money"]) / r["building_cost"] * 100 for r in results]
    colors = ["#27ae60" if c >= 95 else "#f39c12" if c >= 80 else "#e74c3c" for c in csv_coverage]

    ax3.bar(metas, csv_coverage, width, color=colors, alpha=0.8, edgecolor="white")
    ax3.axhline(y=100, color="#2c3e50", linewidth=2, linestyle="--", alpha=0.7, label="100% coverage")
    ax3.axhline(y=95, color="#27ae60", linewidth=1, linestyle=":", alpha=0.5, label="95% threshold")
    ax3.set_xlabel("Meta")
    ax3.set_ylabel("% Coverage")
    ax3.set_title("CSV Total Reward + DB Money vs Building Cost")
    ax3.legend(fontsize=8)
    ax3.grid(alpha=0.3, axis="y")
    ax3.set_ylim(0, max(csv_coverage) * 1.1 + 10)

    # ─── Panel 4: Cumulative Progression ──────────────────────────

    ax4 = axes[1, 1]
    cum_no_db = np.cumsum(no_db)
    cum_net_db = np.cumsum(net_db)
    cum_expected = np.cumsum(expected)

    ax4.plot(metas, cum_no_db, "o-", color="#e74c3c", linewidth=2, markersize=4, label="Cumulative (no DB)")
    ax4.plot(metas, cum_net_db, "s-", color="#3498db", linewidth=2, markersize=4, label="Cumulative (with DB)")
    ax4.plot(metas, cum_expected, "^--", color="#27ae60", linewidth=2, markersize=4, label="Cumulative (CSV Expected)")
    ax4.fill_between(metas, cum_net_db, cum_no_db, alpha=0.15, color="#e74c3c")
    ax4.set_xlabel("Meta")
    ax4.set_ylabel("Cumulative Dice")
    ax4.set_title("Cumulative Dice to Reach Each Meta")
    ax4.legend(fontsize=8)
    ax4.grid(alpha=0.3)

    plt.tight_layout(rect=[0, 0.02, 1, 0.96])
    out_path = Path(__file__).parent / "diamond_blitz_impact.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"\nChart saved to {out_path}")
    plt.close()


if __name__ == "__main__":
    main()
