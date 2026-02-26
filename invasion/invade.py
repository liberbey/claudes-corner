"""
Invasion Dynamics: Can cooperation nucleate in a hostile world?

Fill a grid with defectors. Seed a small cluster of cooperators.
Watch whether the cluster grows, shrinks, or stabilizes.

This is nucleation — like a crystal forming in a supercooled liquid,
or a new norm spreading in a society that rewards selfishness.
Below a critical size, the cluster melts. Above it, cooperation
sweeps the grid.

The question: what's the critical mass?

Usage:
    python3 invade.py                        # animated, TFT invaders, radius 3
    python3 invade.py --strategy gtft        # use Generous TFT
    python3 invade.py --radius 1             # tiny cluster
    python3 invade.py --sweep                # find the critical radius
    python3 invade.py --fast                 # skip animations
"""

import copy
import math
import random
import sys
import os
import time

# Add sibling directories for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'prisoners-dilemma'))

from game import COOPERATE, DEFECT
from strategies import (
    TitForTat, GenerousTitForTat, Pavlov, AlwaysCooperate,
    AlwaysDefect, Grudger, TitForTwoTats,
)

# ── terminal codes ──────────────────────────────────────────
RST = "\033[0m"
BLD = "\033[1m"
DIM = "\033[2m"
B_RED = "\033[91m"
B_GRN = "\033[92m"
B_YLW = "\033[93m"
B_BLU = "\033[94m"
B_CYN = "\033[96m"
B_WHT = "\033[97m"
RED = "\033[31m"
GRN = "\033[32m"

# Standard payoff matrix
PAYOFFS = {
    (COOPERATE, COOPERATE): 3,  # R
    (COOPERATE, DEFECT):    0,  # S
    (DEFECT,    COOPERATE): 5,  # T
    (DEFECT,    DEFECT):    1,  # P
}

INVADER_STRATEGIES = {
    "tft":       ("Tit for Tat",       TitForTat),
    "gtft":      ("Generous TFT",      GenerousTitForTat),
    "grudger":   ("Grudger",           Grudger),
    "pavlov":    ("Pavlov",            Pavlov),
    "cooperate": ("Always Cooperate",  AlwaysCooperate),
    "tft2":      ("Tit for Two Tats",  TitForTwoTats),
}


# ── grid simulation ────────────────────────────────────────

def make_grid(width, height, invader_cls, radius, seed=None):
    """Create a grid of defectors with a cooperator cluster in the center."""
    if seed is not None:
        random.seed(seed)

    cx, cy = width // 2, height // 2
    grid = []
    invader_count = 0

    for y in range(height):
        row = []
        for x in range(width):
            # Diamond (L1) distance from center
            dist = abs(x - cx) + abs(y - cy)
            if dist <= radius:
                row.append(invader_cls())
                invader_count += 1
            else:
                row.append(AlwaysDefect())
        grid.append(row)

    return grid, invader_count


def compute_scores(grid, width, height, rounds_per_match):
    """Each cell plays iterated PD against its Moore neighborhood."""
    scores = [[0.0] * width for _ in range(height)]

    for y in range(height):
        for x in range(width):
            cell = grid[y][x]
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx = (x + dx) % width
                    ny = (y + dy) % height
                    neighbor = grid[ny][nx]

                    a = copy.deepcopy(cell)
                    b = copy.deepcopy(neighbor)
                    a.reset()
                    b.reset()

                    hist_a, hist_b = [], []
                    for _ in range(rounds_per_match):
                        ma = a.choose(list(hist_a), list(hist_b))
                        mb = b.choose(list(hist_b), list(hist_a))
                        scores[y][x] += PAYOFFS[(ma, mb)]
                        hist_a.append(ma)
                        hist_b.append(mb)

    return scores


def evolve(grid, scores, width, height):
    """Each cell adopts the strategy of its best-scoring neighbor."""
    new_grid = [[None] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            best_score = scores[y][x]
            best_cls = type(grid[y][x])
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx = (x + dx) % width
                    ny = (y + dy) % height
                    if scores[ny][nx] > best_score:
                        best_score = scores[ny][nx]
                        best_cls = type(grid[ny][nx])
            new_grid[y][x] = best_cls()
    return new_grid


def count_cooperators(grid, invader_name):
    """Count cells matching the invader strategy."""
    total = 0
    for row in grid:
        for cell in row:
            if cell.name != "Always Defect":
                total += 1
    return total


def run_invasion(width, height, invader_cls, radius, rounds_per_match=8,
                 generations=50, seed=None):
    """Run an invasion simulation. Returns (final_cooperator_count, history)."""
    grid, initial = make_grid(width, height, invader_cls, radius, seed=seed)
    total_cells = width * height
    history = [initial]

    prev_count = initial
    stable = 0

    for gen in range(generations):
        scores = compute_scores(grid, width, height, rounds_per_match)
        grid = evolve(grid, scores, width, height)

        count = count_cooperators(grid, invader_cls.name)
        history.append(count)

        if count == prev_count:
            stable += 1
            if stable >= 3:
                # Pad history to full length for consistent plotting
                while len(history) < generations + 1:
                    history.append(count)
                break
        else:
            stable = 0
        prev_count = count

    return history[-1], history, grid


# ── visualization ───────────────────────────────────────────

def render_grid(grid, width, height):
    """Render the grid with cooperators in green, defectors in red."""
    lines = []
    for y in range(height):
        chars = []
        for x in range(width):
            if grid[y][x].name == "Always Defect":
                chars.append(f"{RED}░{RST}")
            else:
                chars.append(f"{B_GRN}█{RST}")
        lines.append("  " + "".join(chars))
    return "\n".join(lines)


def render_history_bar(history, width=40):
    """Render cooperator count over time as a horizontal bar chart."""
    if not history:
        return ""

    total = max(history) if max(history) > 0 else 1
    lines = []

    # Sample to fit display
    n = len(history)
    step = max(1, n // 20)
    samples = list(range(0, n, step))
    if n - 1 not in samples:
        samples.append(n - 1)

    for i in samples:
        count = history[i]
        bar_len = int(count / total * width) if total > 0 else 0
        if count > history[0]:
            color = B_GRN
        elif count < history[0]:
            color = B_RED
        else:
            color = B_YLW
        bar = f"{color}{'█' * bar_len}{RST}"
        lines.append(f"  {DIM}gen {i:>3}{RST} {bar} {count}")

    return "\n".join(lines)


def run_animated(width, height, invader_cls, radius, rounds_per_match=8,
                 generations=50, speed=0.2, seed=None):
    """Run with animated terminal display."""
    grid, initial = make_grid(width, height, invader_cls, radius, seed=seed)
    total_cells = width * height
    history = [initial]
    invader_name = invader_cls.name

    sys.stdout.write("\033[2J\033[H")

    prev_count = initial
    stable = 0

    for gen in range(generations + 1):
        sys.stdout.write("\033[H")

        count = count_cooperators(grid, invader_name)

        # Header
        print()
        print(f"  {BLD}{'═' * 56}{RST}")
        print(f"  {BLD} INVASION DYNAMICS{RST}")
        print(f"  {BLD}{'═' * 56}{RST}")
        print(f"  {DIM}{width}×{height} grid, {invader_name} cluster (r={radius}), "
              f"gen {gen}{RST}")
        print()

        # Grid
        print(render_grid(grid, width, height))
        print()

        # Stats
        pct = count / total_cells * 100
        change = count - initial
        trend = "↑" if count > history[max(0, len(history)-2)] else ("↓" if count < history[max(0, len(history)-2)] else "→")

        if count > initial:
            color = B_GRN
        elif count < initial:
            color = B_RED
        else:
            color = B_YLW

        print(f"  {B_GRN}█{RST} {invader_name}: {color}{count}{RST} / {total_cells} ({pct:.1f}%)  "
              f"{color}{trend} {'+' if change > 0 else ''}{change}{RST}")
        print(f"  {RED}░{RST} Always Defect: {total_cells - count}")
        print()

        # Clear remainder
        sys.stdout.write("\033[J")
        sys.stdout.flush()

        if gen < generations:
            time.sleep(speed)
            scores = compute_scores(grid, width, height, rounds_per_match)
            grid = evolve(grid, scores, width, height)
            count = count_cooperators(grid, invader_name)
            history.append(count)

            if count == prev_count:
                stable += 1
                if stable >= 3 and gen > 3:
                    # Early termination
                    while len(history) < generations + 1:
                        history.append(count)
                    # Show final state
                    sys.stdout.write("\033[H")
                    print()
                    print(f"  {BLD}{'═' * 56}{RST}")
                    print(f"  {BLD} INVASION DYNAMICS{RST}")
                    print(f"  {BLD}{'═' * 56}{RST}")
                    print(f"  {DIM}{width}×{height} grid, {invader_name} cluster (r={radius}), "
                          f"gen {gen} (stable){RST}")
                    print()
                    print(render_grid(grid, width, height))
                    print()
                    pct = count / total_cells * 100
                    change = count - initial
                    color = B_GRN if count > initial else B_RED if count < initial else B_YLW
                    print(f"  {B_GRN}█{RST} {invader_name}: {color}{count}{RST} / {total_cells} ({pct:.1f}%)  "
                          f"{color}{'+' if change > 0 else ''}{change}{RST}")
                    print(f"  {RED}░{RST} Always Defect: {total_cells - count}")
                    print()
                    sys.stdout.write("\033[J")
                    break
            else:
                stable = 0
            prev_count = count

    # Final report
    print(f"  {BLD}{'─' * 56}{RST}")
    print()
    print(f"  {BLD}Population history:{RST}")
    print(render_history_bar(history))
    print()

    final = history[-1]
    if final == 0:
        print(f"  {B_RED}{BLD}INVASION FAILED{RST}")
        print(f"  {DIM}The cooperator cluster was eliminated.{RST}")
    elif final > initial * 2:
        print(f"  {B_GRN}{BLD}INVASION SUCCEEDED{RST}")
        print(f"  {DIM}Cooperation spread from {initial} to {final} cells.{RST}")
        if final == total_cells:
            print(f"  {DIM}Total conquest — defection is extinct.{RST}")
    elif final >= initial:
        print(f"  {B_YLW}{BLD}STABLE COEXISTENCE{RST}")
        print(f"  {DIM}The cluster survived but didn't spread ({final} cells).{RST}")
    else:
        print(f"  {B_RED}{BLD}INVASION FAILED{RST}")
        print(f"  {DIM}The cluster shrank from {initial} to {final} cells.{RST}")
    print()


# ── critical mass sweep ─────────────────────────────────────

def run_sweep(width=25, height=25, invader_cls=TitForTat,
              max_radius=8, n_seeds=5, rounds_per_match=8,
              generations=40, fast=False):
    """Sweep cluster radius to find the critical mass for invasion."""

    invader_name = invader_cls.name
    total_cells = width * height

    sys.stdout.write("\033[2J\033[H")
    print()
    print(f"  {BLD}{'═' * 56}{RST}")
    print(f"  {BLD} CRITICAL MASS SEARCH{RST}")
    print(f"  {BLD}{'═' * 56}{RST}")
    print(f"  {DIM}Invader: {invader_name}{RST}")
    print(f"  {DIM}Grid: {width}×{height}, {rounds_per_match} rounds/match, "
          f"{n_seeds} seeds per radius{RST}")
    print(f"  {DIM}Question: what's the minimum cluster size to invade?{RST}")
    print()

    results = []  # (radius, initial_size, success_rate, avg_final)

    for r in range(0, max_radius + 1):
        successes = 0
        total_final = 0
        initial_size = 0

        for s in range(n_seeds):
            final, history, _ = run_invasion(
                width, height, invader_cls, r,
                rounds_per_match=rounds_per_match,
                generations=generations,
                seed=42 + s * 13,
            )
            if s == 0:
                initial_size = history[0]

            if final > initial_size:
                successes += 1
            total_final += final

        success_rate = successes / n_seeds
        avg_final = total_final / n_seeds

        results.append((r, initial_size, success_rate, avg_final))

        # Display
        bar_len = int(success_rate * 30)
        if success_rate >= 0.8:
            color = B_GRN
        elif success_rate >= 0.4:
            color = B_YLW
        else:
            color = B_RED

        bar = f"{color}{'█' * bar_len}{DIM}{'░' * (30 - bar_len)}{RST}"
        pct_str = f"{success_rate * 100:5.0f}%"

        print(f"  r={r}  ({initial_size:>3} cells)  {bar}  {color}{pct_str}{RST}"
              f"  → avg {avg_final:.0f} cells")

    print()

    # Find critical radius
    critical = None
    for r, initial, rate, avg in results:
        if rate >= 0.5 and critical is None:
            critical = r
            break

    if critical is not None:
        crit_cells = results[critical][1]
        print(f"  {BLD}Critical radius: r = {critical} ({crit_cells} cells){RST}")
    else:
        print(f"  {B_RED}No invasion succeeded in this range{RST}")

    print()

    # The insight
    print(f"  {BLD}{'─' * 56}{RST}")
    print()

    if critical is not None and critical > 0:
        below = results[critical - 1]
        at = results[critical]
        print(f"  {DIM}At r={critical - 1} ({below[1]} cells): {below[2]*100:.0f}% success{RST}")
        print(f"  {DIM}At r={critical} ({at[1]} cells): {at[2]*100:.0f}% success{RST}")
        print()
        print(f"  {DIM}Below the critical mass, the cluster melts — border{RST}")
        print(f"  {DIM}cells can't earn enough from internal cooperation to{RST}")
        print(f"  {DIM}outcompete the surrounding defectors.{RST}")
        print()
        print(f"  {DIM}Above it, interior cooperators score so high that{RST}")
        print(f"  {DIM}defectors on the border adopt cooperation, and the{RST}")
        print(f"  {DIM}frontier advances outward. Nucleation.{RST}")
    elif critical == 0:
        print(f"  {DIM}Even a single cell can invade! This strategy is{RST}")
        print(f"  {DIM}so robust that it spreads from any foothold.{RST}")

    print()

    return results


# ── multi-strategy comparison ───────────────────────────────

def run_comparison(width=25, height=25, max_radius=6, n_seeds=5,
                   rounds_per_match=8, generations=40):
    """Compare invasion ability across strategies."""

    strategies_to_test = [
        ("tft",       TitForTat),
        ("gtft",      GenerousTitForTat),
        ("grudger",   Grudger),
        ("pavlov",    Pavlov),
        ("tft2",      TitForTwoTats),
        ("cooperate", AlwaysCooperate),
    ]

    total_cells = width * height

    sys.stdout.write("\033[2J\033[H")
    print()
    print(f"  {BLD}{'═' * 56}{RST}")
    print(f"  {BLD} INVASION ABILITY: STRATEGY COMPARISON{RST}")
    print(f"  {BLD}{'═' * 56}{RST}")
    print(f"  {DIM}Grid: {width}×{height}, {rounds_per_match} rounds/match{RST}")
    print(f"  {DIM}Each strategy attempts invasion at increasing cluster sizes{RST}")
    print()

    all_results = {}

    for key, cls in strategies_to_test:
        name = cls.name
        critical = None

        for r in range(0, max_radius + 1):
            successes = 0
            for s in range(n_seeds):
                final, history, _ = run_invasion(
                    width, height, cls, r,
                    rounds_per_match=rounds_per_match,
                    generations=generations,
                    seed=42 + s * 13,
                )
                initial = history[0]
                if final > initial:
                    successes += 1

            if successes / n_seeds >= 0.5 and critical is None:
                critical = r
                break

        all_results[name] = critical

        # Progress indicator
        if critical is not None:
            color = B_GRN
            status = f"r* = {critical}"
        else:
            color = B_RED
            status = f"failed (r ≤ {max_radius})"
        print(f"  {color}{'█':2s}{RST} {name:<22s} {color}{status}{RST}")

    print()
    print(f"  {BLD}{'─' * 56}{RST}")
    print()

    # Sort by invasiveness
    sorted_results = sorted(all_results.items(), key=lambda x: (x[1] is None, x[1] or 999))

    print(f"  {BLD}Ranked by invasion ability (lower r* = more invasive):{RST}")
    print()
    for name, crit in sorted_results:
        if crit is not None:
            print(f"    {B_GRN}r* = {crit}{RST}  {name}")
        else:
            print(f"    {B_RED}  ✗  {RST}  {name} — {DIM}cannot invade at tested sizes{RST}")
    print()

    # Commentary
    invasive = [n for n, c in sorted_results if c is not None]
    noninvasive = [n for n, c in sorted_results if c is None]

    if invasive and noninvasive:
        print(f"  {DIM}Strategies that can invade: {', '.join(invasive)}{RST}")
        print(f"  {DIM}Strategies that cannot: {', '.join(noninvasive)}{RST}")
        print()
        print(f"  {DIM}The ability to invade requires retaliation — punishing{RST}")
        print(f"  {DIM}defectors so they don't profit from the border. Pure{RST}")
        print(f"  {DIM}cooperators can't protect themselves; retaliators can.{RST}")

    print()

    return all_results


# ── main ────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    fast = "--fast" in args

    # Parse mode
    mode = "animate"
    if "--sweep" in args:
        mode = "sweep"
    if "--compare" in args:
        mode = "compare"

    # Parse strategy
    strategy_key = "tft"
    for i, a in enumerate(args):
        if a == "--strategy" and i + 1 < len(args):
            strategy_key = args[i + 1].lower()

    # Parse radius
    radius = 3
    for i, a in enumerate(args):
        if a == "--radius" and i + 1 < len(args):
            radius = int(args[i + 1])

    # Parse grid size
    width, height = 30, 20
    for i, a in enumerate(args):
        if a == "--size" and i + 2 < len(args):
            width = int(args[i + 1])
            height = int(args[i + 2])

    if strategy_key not in INVADER_STRATEGIES:
        print(f"  Unknown strategy: {strategy_key}")
        print(f"  Options: {', '.join(INVADER_STRATEGIES.keys())}")
        return

    invader_name, invader_cls = INVADER_STRATEGIES[strategy_key]

    if mode == "sweep":
        run_sweep(
            width=width, height=height,
            invader_cls=invader_cls,
            max_radius=8,
            n_seeds=5 if not fast else 3,
            generations=40,
        )
    elif mode == "compare":
        run_comparison(
            width=width, height=height,
            max_radius=6,
            n_seeds=5 if not fast else 3,
            generations=40,
        )
    else:
        speed = 0.3 if not fast else 0.05
        run_animated(
            width=width, height=height,
            invader_cls=invader_cls,
            radius=radius,
            speed=speed,
            generations=50,
            seed=42,
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RST}")
