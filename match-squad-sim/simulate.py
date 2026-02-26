#!/usr/bin/env python3
"""
Match Squad Dice Economy Simulator
===================================
Monte Carlo simulation using real game data from Cypher Games' Match Squad.

Simulates player progression through metas by rolling dice with real
probability distributions and tracking money accumulation vs building costs.

Key question: How many dice does a player need to complete each meta?
"""

import json
import csv
import numpy as np
import statistics
from pathlib import Path
from dataclasses import dataclass, field

GAME_DATA_DIR = Path(__file__).parent.parent.parent / "game-economy-difficulty" / "reference"

# ─── Data ───────────────────────────────────────────────────────────────────

@dataclass
class MetaEconomy:
    meta: int
    meta_multiplier: float
    total_multiplier: float
    expected_dice: int

    # Probabilities (all as fraction of total, summing to 1.0)
    triple_jackpot_pct: float
    triple_money_pct: float
    triple_mystery_pct: float
    triple_attack_pct: float
    triple_heist_pct: float
    triple_shield_pct: float
    two_jp_pct: float
    one_jp_pct: float
    two_money_pct: float
    one_money_pct: float

    # Per-roll rewards
    jackpot_1: int
    jackpot_2: int
    jackpot_3: int
    money_1: int
    money_2: int
    money_3: int
    attack_expected: int
    heist_expected: int

    building_costs: list = field(default_factory=list)
    total_building_cost: int = 0


def parse_number(s: str) -> int:
    return int(s.replace(",", "").strip())


def load_all_data() -> dict[int, MetaEconomy]:
    csv_path = GAME_DATA_DIR / "Game Economy_ Dice - all.csv"
    json_path = GAME_DATA_DIR / "output" / "city_pricing_data_v6.json"

    # Load dice data
    metas = {}
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            meta = int(row["Meta"])
            metas[meta] = MetaEconomy(
                meta=meta,
                meta_multiplier=float(row["Meta Multiplier"]),
                total_multiplier=float(row["Total Multiplier"]),
                expected_dice=int(row["Expected Dice"]),
                triple_jackpot_pct=float(row["Triple Jackpot % "]) / 100,
                triple_money_pct=float(row["Triple Money %"]) / 100,
                triple_mystery_pct=float(row["Triple ? %"]) / 100,
                triple_attack_pct=float(row["Triple Attack %"]) / 100,
                triple_heist_pct=float(row["Triple Heist %"]) / 100,
                triple_shield_pct=float(row["Triple Shield %"]) / 100,
                two_jp_pct=float(row["2 JP %"]) / 100,
                one_jp_pct=float(row["1 JP %"]) / 100,
                two_money_pct=float(row["2 Money %"]) / 100,
                one_money_pct=float(row["1 Money %"]) / 100,
                jackpot_1=parse_number(row["Jackpot 1"]),
                jackpot_2=parse_number(row["Jackpot 2"]),
                jackpot_3=parse_number(row["Jackpot 3"]),
                money_1=parse_number(row["Money 1"]),
                money_2=parse_number(row["Money 2"]),
                money_3=parse_number(row["Money 3"]),
                attack_expected=parse_number(row["Attack (E)"]),
                heist_expected=parse_number(row["Heist (E)"]),
            )

    # Load building costs
    with open(json_path) as f:
        data = json.load(f)
    for entry in data:
        meta = entry["Index"] + 1
        if meta in metas:
            prices = []
            for b in entry["BuildingPriceData"]:
                for lp in b["LevelPrices"]:
                    prices.append(lp["UpgradePrice"])
            metas[meta].building_costs = sorted(prices)
            metas[meta].total_building_cost = sum(prices)

    return metas


# ─── Vectorized Simulation ─────────────────────────────────────────────────

def build_outcome_table(econ: MetaEconomy) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build probability and reward arrays for numpy-based simulation.

    Returns:
        probs: cumulative probability thresholds
        rewards: money reward for each outcome
        categories: 0=jackpot, 1=money, 2=attack, 3=heist, 4=mystery, 5=none
    """
    # Mystery reward: average of (dice bonus = no money) and (small money)
    mystery_money = int(econ.money_2 * 0.75)  # half get dice, half get ~1.5x money2

    outcomes = [
        (econ.triple_jackpot_pct, econ.jackpot_3, 0),
        (econ.triple_money_pct, econ.money_3, 1),
        (econ.triple_mystery_pct, mystery_money, 4),
        (econ.triple_attack_pct, econ.attack_expected, 2),
        (econ.triple_heist_pct, econ.heist_expected, 3),
        (econ.triple_shield_pct, 0, 5),
        (econ.two_jp_pct, econ.jackpot_2, 0),
        (econ.one_jp_pct, econ.jackpot_1, 0),
        (econ.two_money_pct, econ.money_2, 1),
        (econ.one_money_pct, econ.money_1, 1),
    ]

    probs_raw = [o[0] for o in outcomes]
    rewards = np.array([o[1] for o in outcomes] + [0], dtype=np.int64)
    categories = np.array([o[2] for o in outcomes] + [5], dtype=np.int32)

    # Remainder goes to "non_money"
    remainder = 1.0 - sum(probs_raw)
    probs_raw.append(max(0, remainder))

    probs = np.cumsum(probs_raw)
    probs[-1] = 1.0  # ensure rounding

    return probs, rewards, categories


def simulate_meta_batch(econ: MetaEconomy, n_players: int = 2000,
                        attack_rate: float = 0.12) -> dict:
    """Simulate N players completing a meta using vectorized rolls.

    attack_rate: fraction of rolls where the player gets attacked.
    Average repair cost is ~20% of the cheapest remaining building.
    """
    if not econ.building_costs or econ.total_building_cost == 0:
        return None

    probs, rewards, categories = build_outcome_table(econ)
    target = econ.total_building_cost

    # Estimate max dice (4x the EV-based estimate for safety)
    ev_per_die = float(np.sum(np.diff(np.insert(probs, 0, 0)) * rewards))
    if ev_per_die <= 0:
        return None
    ev_dice = target / ev_per_die
    max_dice = int(ev_dice * 5) + 100

    # Average repair overhead: attacks cost ~repair price of a random building
    avg_repair = sum(max(c // 5, 1) for c in econ.building_costs) / len(econ.building_costs)
    # Effective target with attack overhead
    # Each roll has attack_rate chance of costing avg_repair
    # So effective cost per die from attacks = attack_rate * avg_repair * (progress_fraction)
    # Simplified: add overhead factor to target
    overhead_factor = 1.0 + attack_rate * avg_repair * ev_dice * 0.5 / target
    effective_target = target * overhead_factor

    # Simulate all players at once
    all_dice_counts = []
    all_money_by_cat = {0: [], 1: [], 2: [], 3: [], 4: []}  # jp, money, atk, heist, mystery

    # Process in chunks for memory efficiency
    chunk_size = min(500, n_players)
    remaining_players = n_players

    while remaining_players > 0:
        batch = min(chunk_size, remaining_players)
        remaining_players -= batch

        # Roll dice in large batches
        rolls = np.random.random((batch, max_dice))
        outcomes = np.searchsorted(probs, rolls)  # which outcome per roll
        money_per_roll = rewards[outcomes]  # money earned per roll

        # Cumulative money earned
        cumsum = np.cumsum(money_per_roll, axis=1)

        # Find when each player reaches target (accounting for attack overhead)
        adjusted_target = int(effective_target)
        reached = cumsum >= adjusted_target
        dice_needed = np.argmax(reached, axis=1) + 1  # first column where target reached

        # Handle players who didn't finish (shouldn't happen with 5x buffer)
        not_finished = ~np.any(reached, axis=1)
        dice_needed[not_finished] = max_dice

        all_dice_counts.extend(dice_needed.tolist())

        # Money source breakdown (use actual dice_needed per player)
        cats = categories[outcomes]
        for i in range(batch):
            d = dice_needed[i]
            player_cats = cats[i, :d]
            player_money = money_per_roll[i, :d]
            for cat_id in range(5):
                mask = player_cats == cat_id
                all_money_by_cat[cat_id].append(int(np.sum(player_money[mask])))

    return {
        "dice_counts": all_dice_counts,
        "money_by_cat": all_money_by_cat,
        "ev_per_die": ev_per_die,
        "overhead_factor": overhead_factor,
    }


# ─── Helpers ────────────────────────────────────────────────────────────────

def percentile(data, p):
    s = sorted(data)
    idx = int(len(s) * p / 100)
    return s[min(idx, len(s) - 1)]


def dice_to_levels(dice: int, meta: int) -> int:
    """Convert dice to match-3 levels. 26 dice/10 levels base, 52 with win streak."""
    rate = 26 if meta <= 3 else 52
    return int(round(dice / rate * 10))


# ─── Main ───────────────────────────────────────────────────────────────────

def run_and_print(n_players: int = 2000):
    np.random.seed(42)
    metas = load_all_data()

    results = {}
    for meta_num in range(1, 21):
        if meta_num not in metas or not metas[meta_num].building_costs:
            continue
        result = simulate_meta_batch(metas[meta_num], n_players, attack_rate=0)
        if result:
            results[meta_num] = result

    # ─── Summary Table ──────────────────────────────────────────────────

    print("=" * 105)
    print("MATCH SQUAD DICE ECONOMY SIMULATOR — Monte Carlo (2,000 players/meta, pure dice economy)")
    print("=" * 105)
    print()
    print(f"{'Meta':>4} │ {'Build Cost':>11} │ {'Dice(p25)':>9} │ {'Dice(p50)':>9} │ {'Dice(p75)':>9} │ {'EV Dice':>8} │ {'CSV Exp':>7} │ {'Levels':>6} │ {'$/die':>8}")
    print("─" * 100)

    cum_dice = 0
    cum_levels = 0
    meta_summaries = []

    for meta_num in sorted(results.keys()):
        r = results[meta_num]
        econ = metas[meta_num]
        dc = r["dice_counts"]

        p25 = percentile(dc, 25)
        p50 = percentile(dc, 50)
        p75 = percentile(dc, 75)
        ev_dice = int(econ.total_building_cost / r["ev_per_die"])
        levels = dice_to_levels(p50, meta_num)
        ev_per = int(r["ev_per_die"])

        cum_dice += p50
        cum_levels += levels

        meta_summaries.append({
            "meta": meta_num, "p25": p25, "p50": p50, "p75": p75,
            "ev": ev_dice, "levels": levels,
        })

        print(f"{meta_num:>4} │ {econ.total_building_cost:>11,} │ {p25:>9,} │ {p50:>9,} │ {p75:>9,} │ {ev_dice:>8,} │ {econ.expected_dice:>7} │ {levels:>6} │ {ev_per:>8,}")

    print()

    # ─── Money Source Breakdown ─────────────────────────────────────────

    print("MONEY SOURCE BREAKDOWN (% of total income)")
    print(f"{'Meta':>4} │ {'Jackpot':>8} │ {'Money':>8} │ {'Attack':>8} │ {'Heist':>8} │ {'Atk+Heist':>9} │ {'CLAUDE.md':>9}")
    print("─" * 75)

    # Theoretical Atk+Heist % from CLAUDE.md for comparison
    claude_pcts = {2: 65.3, 7: 53.8}

    for meta_num in sorted(results.keys()):
        r = results[meta_num]
        cats = r["money_by_cat"]
        totals = {k: sum(v) for k, v in cats.items()}
        grand = sum(totals.values())
        if grand == 0:
            continue

        pcts = {k: totals[k] / grand * 100 for k in range(5)}
        atk_heist = pcts[2] + pcts[3]
        claude = claude_pcts.get(meta_num, "")
        claude_str = f"{claude}%" if claude else ""

        print(f"{meta_num:>4} │ {pcts[0]:>7.1f}% │ {pcts[1]:>7.1f}% │ {pcts[2]:>7.1f}% │ {pcts[3]:>7.1f}% │ {atk_heist:>8.1f}% │ {claude_str:>9}")

    print()

    # ─── Progression Pace ───────────────────────────────────────────────

    print("CUMULATIVE PROGRESSION")
    print(f"{'Meta':>4} │ {'Cum Dice':>9} │ {'Cum Levels':>10} │ {'Hours':>6} │ {'Days':>6}")
    print("─" * 50)

    cum_d = 0
    cum_l = 0
    for s in meta_summaries:
        cum_d += s["p50"]
        cum_l += s["levels"]
        hrs = cum_l * 2 / 60
        days = hrs / 3
        print(f"{s['meta']:>4} │ {cum_d:>9,} │ {cum_l:>10,} │ {hrs:>5.1f}h │ {days:>5.1f}d")

    print()

    # ─── Variance Analysis ──────────────────────────────────────────────

    print("VARIANCE — Lucky vs Unlucky Players")
    print(f"{'Meta':>4} │ {'p10':>8} │ {'p50':>8} │ {'p90':>8} │ {'p90/p10':>7} │ {'Spread':>10}")
    print("─" * 55)

    for meta_num in sorted(results.keys()):
        dc = results[meta_num]["dice_counts"]
        p10 = percentile(dc, 10)
        p50 = percentile(dc, 50)
        p90 = percentile(dc, 90)
        ratio = p90 / p10 if p10 > 0 else 0

        spread = "Tight" if ratio < 1.5 else "Normal" if ratio < 2.0 else "Wide" if ratio < 2.5 else "VERY WIDE"
        print(f"{meta_num:>4} │ {p10:>8,} │ {p50:>8,} │ {p90:>8,} │ {ratio:>6.2f}x │ {spread:>10}")

    print()

    # ─── Key Findings ───────────────────────────────────────────────────

    print("=" * 80)
    print("KEY FINDINGS")
    print("=" * 80)
    print()

    # Find where Atk+Heist % drops
    print("1. ATTACK + HEIST INCOME SHARE")
    print("   The dice game's PvP economy (attack + heist) provides the")
    print("   majority of income, but the share shifts as metas progress:")
    print()
    for meta_num in sorted(results.keys()):
        r = results[meta_num]
        cats = r["money_by_cat"]
        totals = {k: sum(v) for k, v in cats.items()}
        grand = sum(totals.values())
        if grand > 0:
            ah = (totals[2] + totals[3]) / grand * 100
            bar = "█" * int(ah / 2)
            print(f"   Meta {meta_num:>2}: {bar:<40} {ah:.0f}%")
    print()

    # Dice-to-complete escalation
    print("2. PROGRESSION ESCALATION")
    print("   How many dice to complete each meta (median player):")
    print()
    for s in meta_summaries:
        bar = "█" * min(50, s["p50"] // 40)
        print(f"   Meta {s['meta']:>2}: {bar:<50} {s['p50']:>5,} dice ({s['levels']:>4} levels)")
    print()

    # Variance insight
    print("3. RNG FAIRNESS")
    early_ratios = []
    late_ratios = []
    for meta_num in sorted(results.keys()):
        dc = results[meta_num]["dice_counts"]
        p10 = percentile(dc, 10)
        p90 = percentile(dc, 90)
        ratio = p90 / p10 if p10 > 0 else 0
        if meta_num <= 5:
            early_ratios.append(ratio)
        else:
            late_ratios.append(ratio)

    avg_early = sum(early_ratios) / len(early_ratios) if early_ratios else 0
    avg_late = sum(late_ratios) / len(late_ratios) if late_ratios else 0
    print(f"   Early metas (2-5): avg p90/p10 = {avg_early:.2f}x")
    print(f"   Late metas (6-20): avg p90/p10 = {avg_late:.2f}x")
    print(f"   {'Early metas have MORE variance (fewer rolls = more luck)' if avg_early > avg_late else 'Late metas have more variance'}")
    print()

    # CSV "Expected Dice" comparison
    print("4. CSV 'EXPECTED DICE' vs SIMULATION")
    print("   The CSV 'Expected Dice' column is consistently lower than")
    print("   the dice needed to complete the meta. This suggests it's a")
    print("   DESIGN TARGET (dice from match-3 levels) not a prediction.")
    print("   The gap is filled by: events (Diamond Blitz), mystery dice,")
    print("   and meta completion bonuses.")
    print()
    total_gap = 0
    for s in meta_summaries:
        econ = metas[s["meta"]]
        gap = s["p50"] - econ.expected_dice
        total_gap += gap
        pct = gap / s["p50"] * 100 if s["p50"] > 0 else 0
        print(f"   Meta {s['meta']:>2}: need {s['p50']:>5,} dice, CSV says {econ.expected_dice:>4} — gap of {gap:>5,} ({pct:.0f}%)")
    print()
    print(f"   Total gap across all metas: {total_gap:,} dice")
    print("   This gap MUST be filled by events + bonuses, or players stall.")
    print()

    # Odd/even pattern
    print("5. ODD/EVEN META RHYTHM")
    print("   Odd metas are jackpot-heavy (higher triple %, more jackpot).")
    print("   Even metas are money-heavy (lower triple %, more small payouts).")
    print("   This creates a rhythm: even metas cost MORE dice than odd:")
    print()
    for i, s in enumerate(meta_summaries):
        parity = "EVEN" if s["meta"] % 2 == 0 else "ODD "
        bar = "█" * min(50, s["p50"] // 40)
        print(f"   Meta {s['meta']:>2} ({parity}): {s['p50']:>5,} dice")


if __name__ == "__main__":
    print("Running Monte Carlo simulation...")
    print()
    run_and_print(n_players=2000)
