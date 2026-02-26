#!/usr/bin/env python3
"""
FTUE-to-Reality Gap Analysis
==============================
Every Match Squad player experiences 54 scripted dice rolls during onboarding.
These rolls are generous by design — more triples, more jackpots, more money.

Then the scripted sequence ends and real probability kicks in.

This script quantifies the "expectation cliff": how much harder does the game
feel the moment FTUE ends? And what does that mean for D1/D7 retention risk?

Uses:
- DiceResultSet.json (54 scripted Meta 2+ FTUE rolls)
- Game Economy_ Dice - all.csv (real Meta 2 probabilities)
- Monte Carlo simulation for real-play comparison
"""

import json
import csv
import random
import statistics
from pathlib import Path
from collections import Counter
from dataclasses import dataclass

# ─── Constants ─────────────────────────────────────────────────────────────

GAME_DATA_DIR = Path(__file__).parent.parent.parent / "game-economy-difficulty" / "reference"

# Face indices (from CLAUDE.md)
FACE_HEIST = 0
FACE_ATTACK = 1
FACE_MONEY = 2
FACE_MYSTERY = 3
FACE_JACKPOT = 4
FACE_SHIELD = 5

FACE_NAMES = {0: "Heist", 1: "Attack", 2: "Money", 3: "Mystery", 4: "Jackpot", 5: "Shield"}

# Meta 2 rewards (from CSV, already multiplied by 3.0x)
META2_REWARDS = {
    "triple_jackpot": 3_000,
    "triple_money": 600,
    "triple_attack": 7_623,   # expected value
    "triple_heist": 14_823,   # expected value
    "triple_mystery_money": 90,  # ~1.5x double money
    "triple_mystery_dice": 10,   # average bonus dice
    "triple_shield": 0,
    "double_jackpot": 300,
    "single_jackpot": 150,
    "double_money": 60,
    "single_money": 30,
}

# Meta 2 real probabilities (from CSV)
META2_PROBS = {
    "triple_jackpot": 0.14,
    "triple_money": 0.07,
    "triple_mystery": 0.06,
    "triple_attack": 0.05,
    "triple_heist": 0.04,
    "triple_shield": 0.04,
    "double_jackpot": 0.0857,
    "single_jackpot": 0.1371,
    "double_money": 0.0686,
    "single_money": 0.1371,
    "non_money": None,  # remainder
}

# Meta 2 building costs
META2_TOTAL_COST = 105_460


# ─── FTUE Roll Classification ─────────────────────────────────────────────

@dataclass
class ClassifiedRoll:
    roll_num: int
    faces: list
    outcome_type: str   # "triple_jackpot", "double_money", etc.
    money_earned: int
    bonus_dice: int
    is_triple: bool


def classify_roll(roll_num: int, faces: list) -> ClassifiedRoll:
    """Classify a single FTUE roll based on its face values."""
    is_triple = (faces[0] == faces[1] == faces[2])

    if is_triple:
        face = faces[0]
        if face == FACE_JACKPOT:
            return ClassifiedRoll(roll_num, faces, "triple_jackpot",
                                  META2_REWARDS["triple_jackpot"], 0, True)
        elif face == FACE_MONEY:
            return ClassifiedRoll(roll_num, faces, "triple_money",
                                  META2_REWARDS["triple_money"], 0, True)
        elif face == FACE_ATTACK:
            return ClassifiedRoll(roll_num, faces, "triple_attack",
                                  META2_REWARDS["triple_attack"], 0, True)
        elif face == FACE_HEIST:
            return ClassifiedRoll(roll_num, faces, "triple_heist",
                                  META2_REWARDS["triple_heist"], 0, True)
        elif face == FACE_MYSTERY:
            # Mystery is 50% dice, 50% money multiplier
            # For analysis, use expected value
            return ClassifiedRoll(roll_num, faces, "triple_mystery",
                                  META2_REWARDS["triple_mystery_money"], 5, True)
        elif face == FACE_SHIELD:
            return ClassifiedRoll(roll_num, faces, "triple_shield", 0, 0, True)

    # Non-triple: count jackpot and money faces
    jp_count = faces.count(FACE_JACKPOT)
    money_count = faces.count(FACE_MONEY)

    if jp_count >= 2:
        return ClassifiedRoll(roll_num, faces, "double_jackpot",
                              META2_REWARDS["double_jackpot"], 0, False)
    elif jp_count == 1:
        return ClassifiedRoll(roll_num, faces, "single_jackpot",
                              META2_REWARDS["single_jackpot"], 0, False)
    elif money_count >= 2:
        return ClassifiedRoll(roll_num, faces, "double_money",
                              META2_REWARDS["double_money"], 0, False)
    elif money_count == 1:
        return ClassifiedRoll(roll_num, faces, "single_money",
                              META2_REWARDS["single_money"], 0, False)
    else:
        return ClassifiedRoll(roll_num, faces, "non_money", 0, 0, False)


# ─── FTUE Analysis ────────────────────────────────────────────────────────

def analyze_ftue():
    """Parse and analyze all 54 scripted FTUE rolls."""
    with open(GAME_DATA_DIR / "DiceResultSet.json") as f:
        rolls_data = json.load(f)

    classified = []
    for i, roll in enumerate(rolls_data):
        classified.append(classify_roll(i + 1, roll["Faces"]))

    return classified


def compute_ftue_stats(classified: list[ClassifiedRoll]) -> dict:
    """Compute aggregate statistics for FTUE rolls."""
    n = len(classified)
    total_money = sum(r.money_earned for r in classified)
    total_bonus_dice = sum(r.bonus_dice for r in classified)
    triple_count = sum(1 for r in classified if r.is_triple)

    # Count by outcome type
    outcome_counts = Counter(r.outcome_type for r in classified)

    # Money by source
    money_by_source = {}
    for r in classified:
        category = r.outcome_type.split("_")[0]  # triple, double, single, non
        if "jackpot" in r.outcome_type:
            source = "jackpot"
        elif "money" in r.outcome_type:
            source = "money"
        elif "attack" in r.outcome_type:
            source = "attack"
        elif "heist" in r.outcome_type:
            source = "heist"
        elif "mystery" in r.outcome_type:
            source = "mystery"
        else:
            source = "other"
        money_by_source[source] = money_by_source.get(source, 0) + r.money_earned

    # Money per roll
    money_per_roll = total_money / n

    # Effective money per roll for money-producing rolls only
    money_rolls = [r for r in classified if r.money_earned > 0]
    money_per_productive_roll = total_money / len(money_rolls) if money_rolls else 0

    # Rolling window: money per 10-roll window (to show pacing)
    windows = []
    for i in range(0, n - 9):
        window_money = sum(r.money_earned for r in classified[i:i+10])
        windows.append(window_money)

    return {
        "n_rolls": n,
        "total_money": total_money,
        "money_per_roll": money_per_roll,
        "money_per_productive_roll": money_per_productive_roll,
        "total_bonus_dice": total_bonus_dice,
        "triple_count": triple_count,
        "triple_rate": triple_count / n,
        "outcome_counts": dict(outcome_counts),
        "money_by_source": money_by_source,
        "rolling_windows": windows,
    }


# ─── Monte Carlo: Real Meta 2 Play ───────────────────────────────────────

def simulate_real_meta2_rolls(n_rolls: int) -> dict:
    """Simulate n_rolls of real Meta 2 dice using actual probabilities.

    Returns same format as FTUE stats for comparison.
    """
    total_money = 0
    triple_count = 0
    money_by_source = {"jackpot": 0, "money": 0, "attack": 0, "heist": 0, "mystery": 0, "other": 0}
    bonus_dice = 0
    outcome_counts = Counter()
    per_roll_money = []

    for _ in range(n_rolls):
        r = random.random()
        cumulative = 0.0
        roll_money = 0
        is_triple = False
        outcome = ""

        # Triple Jackpot
        cumulative += 0.14
        if r < cumulative:
            roll_money = META2_REWARDS["triple_jackpot"]
            money_by_source["jackpot"] += roll_money
            is_triple = True
            outcome = "triple_jackpot"
        # Triple Money
        elif r < (cumulative := cumulative + 0.07):
            roll_money = META2_REWARDS["triple_money"]
            money_by_source["money"] += roll_money
            is_triple = True
            outcome = "triple_money"
        # Triple Mystery
        elif r < (cumulative := cumulative + 0.06):
            if random.random() < 0.5:
                bonus_dice += random.choice([5, 10, 15])
            else:
                roll_money = META2_REWARDS["triple_mystery_money"]
                money_by_source["mystery"] += roll_money
            is_triple = True
            outcome = "triple_mystery"
        # Triple Attack
        elif r < (cumulative := cumulative + 0.05):
            roll_money = META2_REWARDS["triple_attack"]
            money_by_source["attack"] += roll_money
            is_triple = True
            outcome = "triple_attack"
        # Triple Heist
        elif r < (cumulative := cumulative + 0.04):
            roll_money = META2_REWARDS["triple_heist"]
            money_by_source["heist"] += roll_money
            is_triple = True
            outcome = "triple_heist"
        # Triple Shield
        elif r < (cumulative := cumulative + 0.04):
            is_triple = True
            outcome = "triple_shield"
        # Double Jackpot
        elif r < (cumulative := cumulative + 0.0857):
            roll_money = META2_REWARDS["double_jackpot"]
            money_by_source["jackpot"] += roll_money
            outcome = "double_jackpot"
        # Single Jackpot
        elif r < (cumulative := cumulative + 0.1371):
            roll_money = META2_REWARDS["single_jackpot"]
            money_by_source["jackpot"] += roll_money
            outcome = "single_jackpot"
        # Double Money
        elif r < (cumulative := cumulative + 0.0686):
            roll_money = META2_REWARDS["double_money"]
            money_by_source["money"] += roll_money
            outcome = "double_money"
        # Single Money
        elif r < (cumulative := cumulative + 0.1371):
            roll_money = META2_REWARDS["single_money"]
            money_by_source["money"] += roll_money
            outcome = "single_money"
        else:
            outcome = "non_money"

        if is_triple:
            triple_count += 1

        total_money += roll_money
        per_roll_money.append(roll_money)
        outcome_counts[outcome] += 1

    return {
        "n_rolls": n_rolls,
        "total_money": total_money,
        "money_per_roll": total_money / n_rolls,
        "total_bonus_dice": bonus_dice,
        "triple_count": triple_count,
        "triple_rate": triple_count / n_rolls,
        "outcome_counts": dict(outcome_counts),
        "money_by_source": money_by_source,
        "per_roll_money": per_roll_money,
    }


def monte_carlo_real_meta2(n_simulations: int = 10_000, n_rolls: int = 54) -> dict:
    """Run many simulations of 54 real Meta 2 rolls, return distribution."""
    totals = []
    per_roll_means = []
    triple_rates = []

    for _ in range(n_simulations):
        result = simulate_real_meta2_rolls(n_rolls)
        totals.append(result["total_money"])
        per_roll_means.append(result["money_per_roll"])
        triple_rates.append(result["triple_rate"])

    return {
        "money_totals": totals,
        "money_per_roll_dist": per_roll_means,
        "triple_rate_dist": triple_rates,
        "median_total": statistics.median(totals),
        "mean_total": statistics.mean(totals),
        "p10_total": sorted(totals)[len(totals) // 10],
        "p90_total": sorted(totals)[9 * len(totals) // 10],
        "median_per_roll": statistics.median(per_roll_means),
        "median_triple_rate": statistics.median(triple_rates),
    }


# ─── Expectation Cliff Analysis ──────────────────────────────────────────

def compute_cliff(ftue_stats: dict, mc_stats: dict) -> dict:
    """Compute the expectation cliff between FTUE and real play."""

    ftue_mpr = ftue_stats["money_per_roll"]
    real_mpr = mc_stats["median_per_roll"]
    cliff_pct = (ftue_mpr - real_mpr) / ftue_mpr * 100

    ftue_triple = ftue_stats["triple_rate"]
    real_triple = mc_stats["median_triple_rate"]
    triple_cliff = (ftue_triple - real_triple) / ftue_triple * 100

    # How long does it take to complete Meta 2 with FTUE economy vs real?
    ftue_rolls_for_meta2 = META2_TOTAL_COST / ftue_mpr if ftue_mpr > 0 else float('inf')
    real_rolls_for_meta2 = META2_TOTAL_COST / real_mpr if real_mpr > 0 else float('inf')
    meta2_effort_ratio = real_rolls_for_meta2 / ftue_rolls_for_meta2

    # What percentile would the FTUE total money be in real play?
    ftue_total = ftue_stats["total_money"]
    money_totals = sorted(mc_stats["money_totals"])
    percentile = sum(1 for t in money_totals if t <= ftue_total) / len(money_totals) * 100

    return {
        "ftue_money_per_roll": ftue_mpr,
        "real_money_per_roll": real_mpr,
        "cliff_pct": cliff_pct,
        "ftue_triple_rate": ftue_triple,
        "real_triple_rate": real_triple,
        "triple_cliff_pct": triple_cliff,
        "ftue_rolls_for_meta2": ftue_rolls_for_meta2,
        "real_rolls_for_meta2": real_rolls_for_meta2,
        "meta2_effort_ratio": meta2_effort_ratio,
        "ftue_total_as_percentile": percentile,
    }


# ─── Pacing Analysis ─────────────────────────────────────────────────────

def analyze_pacing(classified: list[ClassifiedRoll]) -> dict:
    """Analyze the pacing of the FTUE: where are the highs and lows?"""

    # Split into phases
    phases = {
        "Early (1-18)": classified[:18],
        "Mid (19-36)": classified[18:36],
        "Late (37-54)": classified[36:],
    }

    phase_stats = {}
    for name, rolls in phases.items():
        money = sum(r.money_earned for r in rolls)
        triples = sum(1 for r in rolls if r.is_triple)
        big_wins = sum(1 for r in rolls if r.money_earned >= 3000)  # triple jackpot or better

        phase_stats[name] = {
            "n_rolls": len(rolls),
            "total_money": money,
            "money_per_roll": money / len(rolls) if rolls else 0,
            "triple_rate": triples / len(rolls) if rolls else 0,
            "big_wins": big_wins,
        }

    # Find the "peak" and "valley" moments
    running_money = []
    cumulative = 0
    for r in classified:
        cumulative += r.money_earned
        running_money.append(cumulative)

    # Longest dry streak (consecutive rolls with no money)
    max_dry = 0
    current_dry = 0
    for r in classified:
        if r.money_earned == 0:
            current_dry += 1
            max_dry = max(max_dry, current_dry)
        else:
            current_dry = 0

    # Biggest single roll
    best_roll = max(classified, key=lambda r: r.money_earned)

    return {
        "phase_stats": phase_stats,
        "running_money": running_money,
        "max_dry_streak": max_dry,
        "best_roll": (best_roll.roll_num, FACE_NAMES.get(best_roll.faces[0], "?"),
                      best_roll.outcome_type, best_roll.money_earned),
    }


# ─── Post-FTUE Transition Simulation ─────────────────────────────────────

def simulate_post_ftue_transition(n_players: int = 5000) -> dict:
    """Simulate the first 54 real rolls AFTER FTUE ends.

    Players have been trained on FTUE's generous economy.
    Now they face real probabilities. How does it feel?
    """
    first_54_money = []
    rolls_to_first_triple = []
    dry_streaks = []

    for _ in range(n_players):
        result = simulate_real_meta2_rolls(54)
        first_54_money.append(result["total_money"])

        # How many rolls until first triple? (FTUE usually has one by roll 2)
        r_list = []
        for roll_idx in range(54):
            r = random.random()
            is_triple = r < 0.40  # 40% triple rate in Meta 2
            r_list.append(is_triple)
            if is_triple and not rolls_to_first_triple or len(rolls_to_first_triple) < n_players:
                break

    # Compute: what % of players earn LESS in their first 54 real rolls
    # than they did during FTUE?
    # (We'll compare against FTUE total in the caller)

    return {
        "money_totals": first_54_money,
        "median": statistics.median(first_54_money),
        "mean": statistics.mean(first_54_money),
        "p10": sorted(first_54_money)[len(first_54_money) // 10],
        "p25": sorted(first_54_money)[len(first_54_money) // 4],
        "p75": sorted(first_54_money)[3 * len(first_54_money) // 4],
        "p90": sorted(first_54_money)[9 * len(first_54_money) // 10],
    }


# ─── Visualization ────────────────────────────────────────────────────────

def generate_chart(ftue_classified, ftue_stats, mc_stats, cliff, pacing, post_ftue):
    """Generate a multi-panel visualization of the FTUE gap."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Match Squad: FTUE-to-Reality Gap Analysis", fontsize=14, fontweight="bold", y=0.98)

    # ─── Panel 1: Cumulative Money (FTUE vs Real Distribution) ────────

    ax1 = axes[0, 0]

    # FTUE cumulative curve
    ftue_cumulative = pacing["running_money"]
    ax1.plot(range(1, len(ftue_cumulative) + 1), ftue_cumulative,
             color="#e74c3c", linewidth=2.5, label="FTUE (scripted)", zorder=5)

    # Real play: simulate 200 trajectories for a band
    random.seed(42)
    real_trajectories = []
    for _ in range(500):
        cum = 0
        traj = []
        for roll_idx in range(54):
            result = simulate_real_meta2_rolls(1)
            cum += result["total_money"]
            traj.append(cum)
        real_trajectories.append(traj)

    real_arr = np.array(real_trajectories)
    x = np.arange(1, 55)
    p10 = np.percentile(real_arr, 10, axis=0)
    p50 = np.percentile(real_arr, 50, axis=0)
    p90 = np.percentile(real_arr, 90, axis=0)

    ax1.fill_between(x, p10, p90, alpha=0.2, color="#3498db", label="Real play (p10-p90)")
    ax1.plot(x, p50, color="#3498db", linewidth=2, linestyle="--", label="Real play (median)")

    ax1.set_xlabel("Roll #")
    ax1.set_ylabel("Cumulative Money")
    ax1.set_title("Cumulative Economy: FTUE vs Real")
    ax1.legend(fontsize=8, loc="upper left")
    ax1.grid(alpha=0.3)

    # ─── Panel 2: Money Per Roll Comparison ───────────────────────────

    ax2 = axes[0, 1]

    # FTUE per-roll money
    ftue_per_roll = [r.money_earned for r in ftue_classified]

    # Color code by type
    colors = []
    for r in ftue_classified:
        if "heist" in r.outcome_type:
            colors.append("#9b59b6")
        elif "attack" in r.outcome_type:
            colors.append("#e74c3c")
        elif "jackpot" in r.outcome_type:
            colors.append("#f39c12")
        elif "money" in r.outcome_type:
            colors.append("#27ae60")
        elif "mystery" in r.outcome_type:
            colors.append("#3498db")
        else:
            colors.append("#bdc3c7")

    n_ftue = len(ftue_per_roll)
    ax2.bar(range(1, n_ftue + 1), ftue_per_roll, color=colors, width=0.8, alpha=0.8)

    # Real average line
    ax2.axhline(y=cliff["real_money_per_roll"], color="#3498db",
                linestyle="--", linewidth=2, label=f"Real avg ({cliff['real_money_per_roll']:.0f}/roll)")
    ax2.axhline(y=cliff["ftue_money_per_roll"], color="#e74c3c",
                linestyle="--", linewidth=2, label=f"FTUE avg ({cliff['ftue_money_per_roll']:.0f}/roll)")

    ax2.set_xlabel("Roll #")
    ax2.set_ylabel("Money Earned")
    ax2.set_title("Per-Roll Income (FTUE Sequence)")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3, axis="y")

    # ─── Panel 3: The Cliff ───────────────────────────────────────────

    ax3 = axes[1, 0]

    categories = ["Triple Rate", "Money/Roll", "Rolls for\nMeta 2"]
    ftue_vals = [
        ftue_stats["triple_rate"] * 100,
        ftue_stats["money_per_roll"],
        cliff["ftue_rolls_for_meta2"],
    ]
    real_vals = [
        mc_stats["median_triple_rate"] * 100,
        mc_stats["median_per_roll"],
        cliff["real_rolls_for_meta2"],
    ]

    x_pos = np.arange(len(categories))
    width = 0.35

    bars1 = ax3.bar(x_pos - width/2, ftue_vals, width, label="FTUE (scripted)",
                    color="#e74c3c", alpha=0.8)
    bars2 = ax3.bar(x_pos + width/2, real_vals, width, label="Real (Monte Carlo)",
                    color="#3498db", alpha=0.8)

    # Add percentage labels
    for i, (fv, rv) in enumerate(zip(ftue_vals, real_vals)):
        if i < 2:  # For triple rate and money/roll, FTUE is better
            diff = ((fv - rv) / rv) * 100
            ax3.text(i, max(fv, rv) * 1.05, f"+{diff:.0f}%", ha="center",
                     fontsize=9, fontweight="bold", color="#c0392b")
        else:  # For rolls needed, real is worse (higher)
            diff = ((rv - fv) / fv) * 100
            ax3.text(i, max(fv, rv) * 1.05, f"+{diff:.0f}% harder", ha="center",
                     fontsize=9, fontweight="bold", color="#c0392b")

    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(categories, fontsize=9)
    ax3.set_title("The Expectation Cliff")
    ax3.legend(fontsize=8)
    ax3.grid(alpha=0.3, axis="y")

    # ─── Panel 4: Post-FTUE Distribution ──────────────────────────────

    ax4 = axes[1, 1]

    # Histogram of total money in first 54 real rolls
    ax4.hist(post_ftue["money_totals"], bins=50, color="#3498db", alpha=0.7,
             edgecolor="white", label="Real play (5K sims)")

    # FTUE total line
    ftue_total = ftue_stats["total_money"]
    ax4.axvline(x=ftue_total, color="#e74c3c", linewidth=2.5,
                label=f"FTUE total ({ftue_total:,})")

    # Percentile annotation
    pct = cliff["ftue_total_as_percentile"]
    ax4.text(ftue_total * 1.02, ax4.get_ylim()[1] * 0.85 if ax4.get_ylim()[1] > 0 else 100,
             f"FTUE = p{pct:.0f}\nof real play",
             fontsize=10, fontweight="bold", color="#c0392b",
             bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#c0392b", alpha=0.9))

    ax4.set_xlabel("Total Money in 54 Rolls")
    ax4.set_ylabel("Frequency")
    ax4.set_title("Where FTUE Sits vs Real Distribution")
    ax4.legend(fontsize=8)
    ax4.grid(alpha=0.3, axis="y")

    plt.tight_layout(rect=[0, 0.02, 1, 0.96])

    out_path = Path(__file__).parent / "ftue_gap_analysis.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"\nChart saved to {out_path}")
    plt.close()


# ─── Report ───────────────────────────────────────────────────────────────

def print_report(ftue_classified, ftue_stats, mc_stats, cliff, pacing, post_ftue):
    """Print the full analysis report."""

    print("=" * 90)
    print("MATCH SQUAD: FTUE-TO-REALITY GAP ANALYSIS")
    print("=" * 90)
    print()

    # ─── Section 1: FTUE Roll Breakdown ──────────────────────────────

    print("1. FTUE SCRIPTED ROLLS (54 rolls, Meta 2)")
    print("-" * 60)
    print()
    print(f"  {'Outcome':<20} {'Count':>6} {'FTUE %':>8} {'Real %':>8} {'Ratio':>8}")
    print(f"  {'─'*20} {'─'*6} {'─'*8} {'─'*8} {'─'*8}")

    outcome_order = [
        "triple_jackpot", "triple_money", "triple_attack", "triple_heist",
        "triple_mystery", "triple_shield",
        "double_jackpot", "single_jackpot", "double_money", "single_money",
        "non_money"
    ]

    for outcome in outcome_order:
        ftue_count = ftue_stats["outcome_counts"].get(outcome, 0)
        ftue_pct = ftue_count / ftue_stats["n_rolls"] * 100
        real_pct = META2_PROBS.get(outcome, 0)
        if real_pct is None:
            # non_money remainder
            real_pct = (1.0 - sum(v for v in META2_PROBS.values() if v is not None)) * 100
        else:
            real_pct *= 100

        ratio = ftue_pct / real_pct if real_pct > 0 else float('inf')
        flag = " ◄" if ratio > 1.5 else ""

        name = outcome.replace("_", " ").title()
        print(f"  {name:<20} {ftue_count:>6} {ftue_pct:>7.1f}% {real_pct:>7.1f}% {ratio:>7.2f}x{flag}")

    print()
    total_triple = ftue_stats["triple_count"]
    print(f"  TOTAL TRIPLES:       {total_triple}/54 = {ftue_stats['triple_rate']*100:.1f}%  (real: {mc_stats['median_triple_rate']*100:.1f}%)")
    print()

    # ─── Section 2: The Cliff ────────────────────────────────────────

    print("2. THE EXPECTATION CLIFF")
    print("-" * 60)
    print()
    print(f"  {'Metric':<30} {'FTUE':>12} {'Real Play':>12} {'Gap':>10}")
    print(f"  {'─'*30} {'─'*12} {'─'*12} {'─'*10}")

    print(f"  {'Triple rate':<30} {ftue_stats['triple_rate']*100:>11.1f}% {mc_stats['median_triple_rate']*100:>11.1f}% {cliff['triple_cliff_pct']:>+9.1f}%")
    print(f"  {'Money per roll':<30} {cliff['ftue_money_per_roll']:>12,.0f} {cliff['real_money_per_roll']:>12,.0f} {cliff['cliff_pct']:>+9.1f}%")
    print(f"  {'Rolls to complete Meta 2':<30} {cliff['ftue_rolls_for_meta2']:>12,.0f} {cliff['real_rolls_for_meta2']:>12,.0f} {(cliff['meta2_effort_ratio']-1)*100:>+9.1f}%")
    print(f"  {'FTUE total as real percentile':<30} {'':>12} {'':>12} {'p'+str(int(cliff['ftue_total_as_percentile'])):>10}")
    print()

    print(f"  ► After FTUE ends, money per roll drops by {cliff['cliff_pct']:.0f}%.")
    print(f"  ► Completing Meta 2 takes {cliff['meta2_effort_ratio']:.1f}x more rolls than FTUE pace suggests.")
    print(f"  ► The FTUE economy would rank at the {cliff['ftue_total_as_percentile']:.0f}th percentile of real play.")
    print()

    # ─── Section 3: Pacing ───────────────────────────────────────────

    print("3. FTUE PACING (how the scripted sequence feels)")
    print("-" * 60)
    print()

    for phase, stats in pacing["phase_stats"].items():
        print(f"  {phase}:")
        print(f"    Money/roll: {stats['money_per_roll']:,.0f}  |  Triple rate: {stats['triple_rate']*100:.0f}%  |  Big wins (≥3K): {stats['big_wins']}")

    print()
    print(f"  Longest dry streak (no money): {pacing['max_dry_streak']} consecutive rolls")
    rn, face, otype, money = pacing["best_roll"]
    print(f"  Biggest single roll: #{rn} — {otype.replace('_',' ')} ({money:,} money)")
    print()

    # ─── Section 4: Post-FTUE Reality ────────────────────────────────

    print("4. POST-FTUE: WHAT REAL PLAY LOOKS LIKE")
    print("-" * 60)
    print()
    print(f"  In 5,000 simulated players' first 54 real rolls after FTUE:")
    print()
    print(f"  {'Metric':<20} {'Value':>12}")
    print(f"  {'─'*20} {'─'*12}")
    print(f"  {'Median total':<20} {post_ftue['median']:>12,.0f}")
    print(f"  {'Mean total':<20} {post_ftue['mean']:>12,.0f}")
    print(f"  {'p10 (unlucky)':<20} {post_ftue['p10']:>12,.0f}")
    print(f"  {'p25':<20} {post_ftue['p25']:>12,.0f}")
    print(f"  {'p75':<20} {post_ftue['p75']:>12,.0f}")
    print(f"  {'p90 (lucky)':<20} {post_ftue['p90']:>12,.0f}")
    print(f"  {'FTUE total':<20} {ftue_stats['total_money']:>12,.0f}")
    print()

    # What % of real players earn less than FTUE?
    worse_count = sum(1 for t in post_ftue["money_totals"] if t < ftue_stats["total_money"])
    worse_pct = worse_count / len(post_ftue["money_totals"]) * 100
    print(f"  ► {worse_pct:.0f}% of players will earn LESS in their first 54 real rolls")
    print(f"    than they experienced during FTUE.")
    print()

    # ─── Section 5: Money Source Comparison ──────────────────────────

    print("5. INCOME MIX: FTUE vs REALITY")
    print("-" * 60)
    print()

    # Run a larger simulation for real income mix
    random.seed(42)
    big_real = simulate_real_meta2_rolls(54 * 1000)
    real_total = sum(big_real["money_by_source"].values())

    ftue_total_m = sum(ftue_stats["money_by_source"].values())

    print(f"  {'Source':<12} {'FTUE %':>8} {'Real %':>8} {'Shift':>8}")
    print(f"  {'─'*12} {'─'*8} {'─'*8} {'─'*8}")

    for source in ["jackpot", "money", "attack", "heist", "mystery"]:
        ftue_pct = ftue_stats["money_by_source"].get(source, 0) / ftue_total_m * 100 if ftue_total_m > 0 else 0
        real_pct = big_real["money_by_source"].get(source, 0) / real_total * 100 if real_total > 0 else 0
        shift = ftue_pct - real_pct
        print(f"  {source.title():<12} {ftue_pct:>7.1f}% {real_pct:>7.1f}% {shift:>+7.1f}%")

    print()

    # ─── Section 6: Findings ─────────────────────────────────────────

    print("=" * 90)
    print("FINDINGS")
    print("=" * 90)
    print()
    print(f"1. TRIPLE RATE CLIFF: FTUE runs at {ftue_stats['triple_rate']*100:.0f}% triples vs")
    print(f"   {mc_stats['median_triple_rate']*100:.0f}% in real play — a {cliff['triple_cliff_pct']:.0f}% drop. Players are trained")
    print(f"   to expect frequent big wins that real probability can't deliver.")
    print()
    print(f"2. INCOME CLIFF: FTUE delivers {cliff['ftue_money_per_roll']:,.0f} money/roll vs")
    print(f"   {cliff['real_money_per_roll']:,.0f} in real play — a {cliff['cliff_pct']:.0f}% drop. The game feels")
    print(f"   {cliff['cliff_pct']:.0f}% harder the moment scripted rolls end.")
    print()
    print(f"3. EFFORT MISMATCH: At FTUE pace, Meta 2 would take ~{cliff['ftue_rolls_for_meta2']:.0f} rolls.")
    print(f"   At real pace, it takes ~{cliff['real_rolls_for_meta2']:.0f} rolls — {cliff['meta2_effort_ratio']:.1f}x the effort")
    print(f"   the player was trained to expect.")
    print()
    print(f"4. HEIST OVERWEIGHT: FTUE has {ftue_stats['outcome_counts'].get('triple_heist', 0)} Triple Heists")
    print(f"   (5.6% vs 4% real) — the single highest-value outcome. Players learn to")
    print(f"   expect heist windfalls that are actually rare.")
    print()

    # Calculate income mix implications
    ftue_atk_heist = (ftue_stats["money_by_source"].get("attack", 0) +
                       ftue_stats["money_by_source"].get("heist", 0))
    ftue_atk_heist_pct = ftue_atk_heist / ftue_total_m * 100 if ftue_total_m > 0 else 0

    print(f"5. PVP EXPECTATION: {ftue_atk_heist_pct:.0f}% of FTUE income comes from Attack+Heist.")
    print(f"   This trains players to see PvP as the primary income source — which is")
    print(f"   correct for the real economy, but the FTUE overpromises on PvP frequency.")
    print()
    print(f"6. CHURN RISK WINDOW: The highest churn risk is rolls 55-80 — immediately")
    print(f"   after FTUE ends. {worse_pct:.0f}% of players will have a worse experience than")
    print(f"   FTUE trained them to expect. The unluckiest 10% earn only")
    print(f"   {post_ftue['p10']:,} money (vs FTUE's {ftue_stats['total_money']:,}).")
    print()

    # ─── Recommendations ─────────────────────────────────────────────

    print("=" * 90)
    print("RECOMMENDATIONS")
    print("=" * 90)
    print()
    print("1. SOFTEN THE CLIFF — Consider a 20-30 roll \"transition zone\" after FTUE")
    print("   with slightly boosted probabilities (e.g., 35% triple rate vs 40% FTUE")
    print("   and 27.5% real). Gradual ramp-down instead of instant cliff.")
    print()
    print("2. TIME THE FIRST EVENT — Launch Diamond Blitz to coincide with the post-FTUE")
    print("   window (rolls 55-100). Event rewards mask the income drop, buying time")
    print("   for the player to adjust expectations.")
    print()
    print("3. REDUCE FTUE HEIST/ATTACK — Lower Triple Heist/Attack frequency in FTUE")
    print("   to match real rates. PvP income is hard to control; better to under-")
    print("   promise and over-deliver than the reverse.")
    print()
    print("4. ADD A \"LUCKY STREAK\" MECHANIC — If post-FTUE player goes 5+ rolls with")
    print("   no triple, boost next roll's triple probability. This creates a rubber-")
    print("   band effect that prevents the worst-case unlucky streaks that drive churn.")
    print()


# ─── Main ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    random.seed(42)

    print("Analyzing FTUE scripted rolls...")
    ftue_classified = analyze_ftue()
    ftue_stats = compute_ftue_stats(ftue_classified)

    print(f"Running Monte Carlo simulation (10,000 × 54 rolls)...")
    mc_stats = monte_carlo_real_meta2(n_simulations=10_000, n_rolls=54)

    print("Computing expectation cliff...")
    cliff = compute_cliff(ftue_stats, mc_stats)

    print("Analyzing FTUE pacing...")
    pacing = analyze_pacing(ftue_classified)

    print("Simulating post-FTUE transition (5,000 players)...")
    post_ftue = simulate_post_ftue_transition(n_players=5000)

    print()
    print_report(ftue_classified, ftue_stats, mc_stats, cliff, pacing, post_ftue)

    print("\nGenerating visualization...")
    generate_chart(ftue_classified, ftue_stats, mc_stats, cliff, pacing, post_ftue)
