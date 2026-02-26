"""
Prisoner's Dilemma tournament — round-robin + evolutionary dynamics.

Recreates Axelrod's famous experiment: strategies compete in iterated
Prisoner's Dilemma, then populations evolve based on fitness.

The result that changed game theory: simple, "nice" strategies win.
Not because they're clever, but because they create the conditions
for mutual cooperation to emerge.

Usage:
    python3 tournament.py              # full tournament + evolution
    python3 tournament.py --tournament # tournament only
    python3 tournament.py --evolve     # evolution only
    python3 tournament.py --rounds 500 # custom rounds per match
"""

import copy
import sys

from game import play_match, PAYOFFS, COOPERATE, DEFECT
from strategies import create_all


# ── ANSI colors ──────────────────────────────────────────────────────

COLORS = [
    "\033[92m",   # bright green
    "\033[96m",   # bright cyan
    "\033[93m",   # bright yellow
    "\033[94m",   # bright blue
    "\033[95m",   # bright magenta
    "\033[91m",   # bright red
    "\033[32m",   # green
    "\033[36m",   # cyan
    "\033[33m",   # yellow
    "\033[34m",   # blue
    "\033[35m",   # magenta
    "\033[31m",   # red
]
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def colored(text, color_idx):
    return f"{COLORS[color_idx % len(COLORS)]}{text}{RESET}"


def bold(text):
    return f"{BOLD}{text}{RESET}"


def dim(text):
    return f"{DIM}{text}{RESET}"


# ── Tournament ───────────────────────────────────────────────────────

def run_pairwise(strategies, rounds_per_match=200):
    """Compute pairwise scores: result[a][b] = a's total score against b."""
    names = [s.name for s in strategies]
    scores = {n: {} for n in names}

    for i, a in enumerate(strategies):
        for j, b in enumerate(strategies):
            a_copy = copy.deepcopy(a)
            b_copy = copy.deepcopy(b)
            result = play_match(a_copy, b_copy, rounds_per_match)
            scores[a.name][b.name] = result.score_a

    return scores


def print_tournament(pairwise, strategies):
    """Print tournament results as a ranked scoreboard."""
    # Total score = sum of scores against all opponents
    totals = {}
    for s in strategies:
        totals[s.name] = sum(pairwise[s.name].values())

    ranked = sorted(totals.items(), key=lambda x: -x[1])
    max_score = ranked[0][1]
    max_name_len = max(len(name) for name, _ in ranked)

    print()
    print(bold("  TOURNAMENT RESULTS"))
    print(f"  {dim(f'{len(strategies)} strategies × {len(strategies)} opponents × round-robin')}")
    print()

    bar_width = 35
    for rank, (name, score) in enumerate(ranked):
        idx = next(i for i, s in enumerate(strategies) if s.name == name)
        bar_len = int(bar_width * score / max_score)
        bar = colored("█" * bar_len, idx)
        pad = " " * (max_name_len - len(name))
        rank_str = f"{rank + 1:>3}."
        print(f"  {rank_str} {name}{pad}  {bar} {score}")

    print()

    # Highlight key matchups
    print(f"  {bold('Key matchups')} {dim('(per-match scores)')}")
    print()
    matchups = [
        ("Tit for Tat", "Always Cooperate"),
        ("Tit for Tat", "Always Defect"),
        ("Always Cooperate", "Always Defect"),
        ("Tit for Tat", "Grudger"),
        ("Pavlov", "Always Cooperate"),
        ("Detective", "Always Cooperate"),
        ("Detective", "Tit for Tat"),
    ]
    for a_name, b_name in matchups:
        if a_name in pairwise and b_name in pairwise[a_name]:
            sa = pairwise[a_name][b_name]
            sb = pairwise[b_name][a_name]
            print(f"    {a_name} vs {b_name}: {sa}–{sb}")

    print()
    return ranked


# ── Evolutionary dynamics ────────────────────────────────────────────

def evolve(strategies, pairwise, generations=50):
    """Replicator dynamics: populations evolve based on fitness.

    Each generation:
      fitness(i) = Σ_j  score(i,j) × population(j)
      new_pop(i) = old_pop(i) × fitness(i) / avg_fitness

    Strategies that do well against the current population grow.
    Strategies that do poorly shrink and eventually go extinct.
    """
    n = len(strategies)
    population = {s.name: 1.0 / n for s in strategies}
    history = [dict(population)]
    active_names = [s.name for s in strategies]

    for gen in range(generations):
        # Expected fitness of each strategy against current population
        fitness = {}
        for name in active_names:
            fitness[name] = sum(
                pairwise[name][opp] * population.get(opp, 0)
                for opp in active_names
            )

        # Average fitness
        avg_fitness = sum(
            fitness[name] * population[name]
            for name in active_names
        )
        if avg_fitness == 0:
            break

        # Replicator update
        new_pop = {}
        for name in active_names:
            new_pop[name] = population[name] * fitness[name] / avg_fitness

        # Extinction threshold
        active_names = [n for n in active_names if new_pop.get(n, 0) > 0.001]
        total = sum(new_pop[n] for n in active_names)
        population = {n: new_pop[n] / total for n in active_names}

        history.append(dict(population))

    return history


def print_evolution(history, strategies):
    """Print population dynamics as a stacked bar chart."""
    # Build color map from original strategy order
    color_map = {}
    for i, s in enumerate(strategies):
        color_map[s.name] = i

    # Find which strategies ever appear
    all_names = set()
    for snapshot in history:
        all_names.update(snapshot.keys())

    # Sort by final population (largest first)
    final = history[-1]
    sorted_names = sorted(all_names, key=lambda n: -final.get(n, 0))

    # Identify survivors (>1% in final generation)
    survivors = [n for n in sorted_names if final.get(n, 0) > 0.01]
    extinct = [n for n in sorted_names if final.get(n, 0) <= 0.01]

    print(bold("  EVOLUTIONARY DYNAMICS"))
    print(f"  {dim(f'Replicator dynamics, {len(history)-1} generations')}")
    print()

    bar_width = 60

    # Print every Nth generation to fit nicely
    total_gens = len(history)
    if total_gens <= 25:
        step = 1
    elif total_gens <= 50:
        step = 2
    else:
        step = max(1, total_gens // 25)

    for gen_idx in range(0, total_gens, step):
        snapshot = history[gen_idx]
        gen_label = f"  {gen_idx:>3} "
        bar_chars = []

        for name in sorted_names:
            frac = snapshot.get(name, 0)
            n_chars = int(frac * bar_width + 0.5)
            ci = color_map.get(name, 0)
            bar_chars.append(colored("█" * n_chars, ci))

        # Ensure total bar length is consistent
        print(f"{gen_label}{''.join(bar_chars)}")

    # Always print the last generation if we didn't already
    if (total_gens - 1) % step != 0:
        snapshot = history[-1]
        gen_label = f"  {total_gens - 1:>3} "
        bar_chars = []
        for name in sorted_names:
            frac = snapshot.get(name, 0)
            n_chars = int(frac * bar_width + 0.5)
            ci = color_map.get(name, 0)
            bar_chars.append(colored("█" * n_chars, ci))
        print(f"{gen_label}{''.join(bar_chars)}")

    # Legend
    print()
    print("  Legend:")
    for name in sorted_names:
        ci = color_map.get(name, 0)
        pct = final.get(name, 0) * 100
        marker = colored("██", ci)
        status = f"{pct:.1f}%" if pct > 0.1 else "extinct"
        print(f"    {marker} {name} ({status})")

    print()

    # Summary
    if survivors:
        print(f"  {bold('Survivors:')} {', '.join(survivors)}")
    if extinct:
        print(f"  {dim('Extinct:')} {dim(', '.join(extinct))}")
    print()


# ── Commentary ───────────────────────────────────────────────────────

def print_header(rounds_per_match):
    print()
    print(bold("  ═══════════════════════════════════════════════════════"))
    print(bold("   THE PRISONER'S DILEMMA TOURNAMENT"))
    print(bold("  ═══════════════════════════════════════════════════════"))
    print()
    print(f"  Two players. One choice: {bold('cooperate')} or {bold('defect')}.")
    print(f"  Both cooperate → 3 each.  Both defect → 1 each.")
    print(f"  One defects    → defector gets 5, cooperator gets 0.")
    print()
    print(f"  Defecting always pays more. But mutual cooperation")
    print(f"  beats mutual defection. {dim('That tension is everything.')}")
    print()
    print(f"  {rounds_per_match} rounds per match. Iterated — with memory.")
    print()


def print_commentary(ranked):
    """Print observations about the tournament results."""
    winner = ranked[0][0]
    loser = ranked[-1][0]

    print(bold("  OBSERVATIONS"))
    print()

    nice_strategies = {
        "Tit for Tat", "Always Cooperate", "Tit for Two Tats",
        "Generous TFT", "Pavlov", "Soft Majority",
    }
    mean_strategies = {
        "Always Defect", "Suspicious TFT", "Hard Majority",
    }

    nice_ranks = []
    mean_ranks = []
    for rank, (name, _) in enumerate(ranked):
        if name in nice_strategies:
            nice_ranks.append(rank + 1)
        if name in mean_strategies:
            mean_ranks.append(rank + 1)

    avg_nice = sum(nice_ranks) / len(nice_ranks) if nice_ranks else 0
    avg_mean = sum(mean_ranks) / len(mean_ranks) if mean_ranks else 0

    print(f"  Winner: {bold(winner)}")
    print()
    print(f"  Average rank of 'nice' strategies (never defect first): {avg_nice:.1f}")
    print(f"  Average rank of 'mean' strategies (defect first):       {avg_mean:.1f}")
    print()

    if avg_nice < avg_mean:
        print("  Nice strategies outperform mean ones — not because they're naive,")
        print("  but because they create environments where cooperation is possible.")
        print("  The best strategies are nice, retaliatory, forgiving, and clear.")
    print()


# ── Main ─────────────────────────────────────────────────────────────

def main():
    rounds_per_match = 200
    generations = 50
    show_tournament = True
    show_evolution = True

    # Parse args
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--tournament":
            show_evolution = False
        elif arg == "--evolve":
            show_tournament = False
        elif arg == "--rounds" and i + 1 < len(args):
            rounds_per_match = int(args[i + 1])
        elif arg == "--generations" and i + 1 < len(args):
            generations = int(args[i + 1])

    strategies = create_all()
    print_header(rounds_per_match)

    # Compute all pairwise matchups
    pairwise = run_pairwise(strategies, rounds_per_match)

    if show_tournament:
        ranked = print_tournament(pairwise, strategies)
        print_commentary(ranked)

    if show_evolution:
        history = evolve(strategies, pairwise, generations)
        print_evolution(history, strategies)


if __name__ == "__main__":
    main()
