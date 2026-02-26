"""
Phase Transition in Spatial Cooperation

Vary the temptation payoff T and find the critical point where
cooperation collapses. This is the "temperature" of the spatial
prisoner's dilemma — below it, cooperators form stable clusters;
above it, defection sweeps the grid.

The standard PD payoff matrix:
    T > R > P > S  and  2R > T + S

    R = 3  (mutual cooperation)
    P = 1  (mutual defection)
    S = 0  (sucker's payoff)
    T = ?  (temptation to defect)

Standard T = 5. What happens as we increase it?

In a well-mixed population, cooperation is already fragile at T = 5.
In the spatial version, geography protects cooperators — they cluster.
But at some critical T*, even spatial structure fails.

This program finds that threshold.

Usage:
    python3 explore.py                   # full sweep, 3 strategy sets
    python3 explore.py --fast            # fewer T values, smaller grid
    python3 explore.py --set classic     # only TFT/Cooperate/Defect
    python3 explore.py --set full        # all 12 strategies
"""

import copy
import math
import random
import sys
import os
import time

# Add sibling directories for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'prisoners-dilemma'))

from game import PAYOFFS, COOPERATE, DEFECT
from strategies import (
    TitForTat, GenerousTitForTat, Pavlov, AlwaysCooperate,
    AlwaysDefect, Grudger, SuspiciousTitForTat, TitForTwoTats,
    SoftMajority, HardMajority, Detective, Random as RandomStrategy,
    ALL_STRATEGIES,
)

# ── terminal codes ──────────────────────────────────────────
RST = "\033[0m"
BLD = "\033[1m"
DIM = "\033[2m"
B_RED = "\033[91m"
B_GRN = "\033[92m"
B_YLW = "\033[93m"
B_BLU = "\033[94m"
B_MAG = "\033[95m"
B_CYN = "\033[96m"
B_WHT = "\033[97m"
RED = "\033[31m"
GRN = "\033[32m"
YLW = "\033[33m"
CYN = "\033[36m"

# ── strategy sets ───────────────────────────────────────────

NICE_STRATEGIES = {
    "Tit for Tat", "Generous TFT", "Tit for Two Tats", "Pavlov",
    "Always Cooperate", "Soft Majority",
}

STRATEGY_SETS = {
    "classic": {
        "name": "Classic (TFT / Cooperate / Defect)",
        "classes": [TitForTat, AlwaysCooperate, AlwaysDefect],
    },
    "retaliators": {
        "name": "Retaliators vs Exploiters",
        "classes": [TitForTat, GenerousTitForTat, Grudger,
                    AlwaysDefect, SuspiciousTitForTat, Detective],
    },
    "full": {
        "name": "All 12 strategies",
        "classes": ALL_STRATEGIES,
    },
}


# ── grid simulation (lightweight, no display) ──────────────

def make_grid(width, height, strategy_classes, seed=None):
    """Create a random grid of strategies."""
    if seed is not None:
        random.seed(seed)
    grid = []
    for y in range(height):
        row = []
        for x in range(width):
            cls = random.choice(strategy_classes)
            row.append(cls())
        grid.append(row)
    return grid


def compute_scores(grid, width, height, rounds_per_match, payoffs):
    """Play each cell against its Moore neighborhood."""
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
                        scores[y][x] += payoffs[(ma, mb)]
                        hist_a.append(ma)
                        hist_b.append(mb)

    return scores


def evolve_grid(grid, scores, width, height):
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


def census(grid):
    """Count population of each strategy."""
    counts = {}
    for row in grid:
        for cell in row:
            name = cell.name
            counts[name] = counts.get(name, 0) + 1
    return counts


def cooperation_fraction(counts):
    """Fraction of the population using 'nice' strategies."""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    nice = sum(v for k, v in counts.items() if k in NICE_STRATEGIES)
    return nice / total


def run_simulation(temptation, strategy_classes, width=20, height=20,
                   rounds_per_match=8, generations=30, seed=42):
    """Run a spatial PD simulation with a given temptation value.
    Returns the cooperation fraction at equilibrium."""

    # Set the payoff matrix
    payoffs = {
        (COOPERATE, COOPERATE): 3,    # R
        (COOPERATE, DEFECT):    0,    # S
        (DEFECT,    COOPERATE): temptation,  # T
        (DEFECT,    DEFECT):    1,    # P
    }

    grid = make_grid(width, height, strategy_classes, seed=seed)

    prev_census = None
    stable_count = 0

    for gen in range(generations):
        scores = compute_scores(grid, width, height, rounds_per_match, payoffs)
        grid = evolve_grid(grid, scores, width, height)

        # Check for convergence
        current = census(grid)
        if current == prev_census:
            stable_count += 1
            if stable_count >= 3:
                break
        else:
            stable_count = 0
        prev_census = current

    final = census(grid)
    return cooperation_fraction(final), final


def run_averaged(temptation, strategy_classes, n_seeds=5, **kwargs):
    """Run multiple simulations with different seeds and return the average."""
    total = 0.0
    for i in range(n_seeds):
        coop, _ = run_simulation(temptation, strategy_classes, seed=42 + i * 7, **kwargs)
        total += coop
    return total / n_seeds


# ── ASCII plot ──────────────────────────────────────────────

def plot_phase_diagram(results_by_set, t_values):
    """Draw an ASCII phase diagram: cooperation% vs temptation T."""

    plot_w = 60
    plot_h = 20

    # Characters for different sets
    set_chars = {
        "classic": ("●", B_CYN),
        "retaliators": ("◆", B_YLW),
        "full": ("■", B_MAG),
    }

    # Build the plot grid
    canvas = [[' '] * (plot_w + 1) for _ in range(plot_h + 1)]
    colors = [[DIM] * (plot_w + 1) for _ in range(plot_h + 1)]

    # Axes
    for r in range(plot_h + 1):
        canvas[r][0] = '│'
    for c in range(plot_w + 1):
        canvas[plot_h][c] = '─'
    canvas[plot_h][0] = '└'

    # Y-axis ticks
    for pct in (0, 25, 50, 75, 100):
        r = plot_h - int(pct / 100 * plot_h)
        if 0 <= r < plot_h:
            canvas[r][0] = '┤'

    # X-axis ticks
    t_min, t_max = t_values[0], t_values[-1]
    for t_tick in range(int(t_min), int(t_max) + 1):
        c = int((t_tick - t_min) / (t_max - t_min) * plot_w)
        if 0 < c <= plot_w:
            canvas[plot_h][c] = '┬'

    # Plot data points
    for set_name, data in results_by_set.items():
        ch, col = set_chars.get(set_name, ("·", B_WHT))
        for t, coop in data:
            c = int((t - t_min) / (t_max - t_min) * plot_w)
            r = plot_h - int(coop * plot_h)
            c = max(1, min(c, plot_w))
            r = max(0, min(r, plot_h - 1))
            canvas[r][c] = ch
            colors[r][c] = col

    # Render
    lines = []

    # Y-axis labels
    for r in range(plot_h + 1):
        pct = (plot_h - r) / plot_h * 100
        if r == 0:
            label = "100%"
        elif r == plot_h // 4:
            label = " 75%"
        elif r == plot_h // 2:
            label = " 50%"
        elif r == 3 * plot_h // 4:
            label = " 25%"
        elif r == plot_h:
            label = "  0%"
        else:
            label = "    "

        row_str = ''.join(f"{colors[r][c]}{canvas[r][c]}{RST}" for c in range(plot_w + 1))
        lines.append(f"  {DIM}{label}{RST} {row_str}")

    # X-axis labels
    x_labels = "     "
    for t_tick in range(int(t_min), int(t_max) + 1):
        c = int((t_tick - t_min) / (t_max - t_min) * plot_w)
        spacing = c - len(x_labels) + 5
        if spacing > 0:
            x_labels += " " * spacing + str(t_tick)
    lines.append(f"  {DIM}{x_labels}{RST}")
    lines.append(f"  {DIM}       {'Temptation to defect (T)':^{plot_w}s}{RST}")

    return "\n".join(lines)


# ── finding the critical point ──────────────────────────────

def find_critical_point(data):
    """Find where cooperation drops below 50% — the phase transition."""
    for i in range(len(data) - 1):
        t1, c1 = data[i]
        t2, c2 = data[i + 1]
        if c1 >= 0.5 and c2 < 0.5:
            # Linear interpolation
            if c1 == c2:
                return t1
            t_crit = t1 + (0.5 - c1) * (t2 - t1) / (c2 - c1)
            return t_crit
    return None


def find_collapse_point(data):
    """Find where cooperation drops to zero."""
    for i in range(len(data)):
        t, c = data[i]
        if c == 0.0:
            return t
    return None


# ── main ────────────────────────────────────────────────────

def main():
    fast = "--fast" in sys.argv

    # Parse strategy set selection
    selected_sets = None
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--set" and i + 1 < len(args):
            selected_sets = [args[i + 1]]

    if selected_sets is None:
        selected_sets = ["classic", "retaliators", "full"]

    # Parameter sweep range
    if fast:
        t_values = [t / 10 for t in range(30, 121, 5)]  # 3.0 to 12.0 by 0.5
        grid_w, grid_h = 15, 15
        gens = 20
        n_seeds = 3
    else:
        t_values = [t / 10 for t in range(30, 121, 3)]  # 3.0 to 12.0 by 0.3
        grid_w, grid_h = 20, 20
        gens = 30
        n_seeds = 5

    sys.stdout.write("\033[2J\033[H")
    print()
    print(f"  {BLD}{'═' * 56}{RST}")
    print(f"  {BLD} PHASE TRANSITION IN SPATIAL COOPERATION{RST}")
    print(f"  {BLD}{'═' * 56}{RST}")
    print()
    print(f"  {DIM}Payoff matrix: R=3, P=1, S=0, T=variable{RST}")
    print(f"  {DIM}Grid: {grid_w}×{grid_h}, {gens} generations, 8 rounds/match{RST}")
    print(f"  {DIM}Averaged over {n_seeds} random seeds per T value{RST}")
    print(f"  {DIM}Question: at what temptation does cooperation collapse?{RST}")
    print()

    # Run sweeps
    results_by_set = {}

    for set_name in selected_sets:
        sset = STRATEGY_SETS[set_name]
        strategy_classes = sset["classes"]
        set_label = sset["name"]

        ch_info = {"classic": (B_CYN, "●"), "retaliators": (B_YLW, "◆"),
                   "full": (B_MAG, "■")}
        col, ch = ch_info.get(set_name, (B_WHT, "·"))

        print(f"  {col}{ch}{RST} {BLD}{set_label}{RST}")

        data = []
        for i, t in enumerate(t_values):
            coop = run_averaged(
                temptation=t,
                strategy_classes=strategy_classes,
                n_seeds=n_seeds,
                width=grid_w, height=grid_h,
                rounds_per_match=8,
                generations=gens,
            )
            data.append((t, coop))

            # Progress bar
            pct_done = (i + 1) / len(t_values)
            bar_len = int(pct_done * 30)
            bar = f"{col}{'█' * bar_len}{DIM}{'░' * (30 - bar_len)}{RST}"
            coop_str = f"{B_GRN if coop > 0.5 else B_RED if coop < 0.2 else B_YLW}{coop*100:5.1f}%{RST}"
            sys.stdout.write(f"\r    T={t:5.1f}  {bar}  coop={coop_str}       ")
            sys.stdout.flush()

        print(f"\r    {'':70s}")  # clear progress line

        # Summary for this set
        crit = find_critical_point(data)
        collapse = find_collapse_point(data)

        if crit is not None:
            print(f"    Critical point (50% cooperation): {col}T* ≈ {crit:.1f}{RST}")
        else:
            if data[-1][1] > 0.5:
                print(f"    {B_GRN}Cooperation survives across entire range{RST}")
            else:
                print(f"    {B_RED}Cooperation never reached 50%{RST}")

        if collapse is not None:
            print(f"    Total collapse: {DIM}T = {collapse:.1f}{RST}")
        else:
            print(f"    {DIM}Cooperation never fully collapses in this range{RST}")

        print()
        results_by_set[set_name] = data

    # Phase diagram
    print(f"  {BLD}{'─' * 56}{RST}")
    print(f"  {BLD}Phase Diagram: Cooperation % vs Temptation{RST}")
    print()
    print(plot_phase_diagram(results_by_set, t_values))
    print()

    # Legend
    print(f"  {BLD}Legend:{RST}")
    for set_name in selected_sets:
        ch_info = {"classic": (B_CYN, "●"), "retaliators": (B_YLW, "◆"),
                   "full": (B_MAG, "■")}
        col, ch = ch_info.get(set_name, (B_WHT, "·"))
        print(f"    {col}{ch}{RST}  {STRATEGY_SETS[set_name]['name']}")
    print()

    # ── Analysis ──
    print(f"  {BLD}{'─' * 56}{RST}")
    print(f"  {BLD}Analysis{RST}")
    print()

    # Compare critical points
    crits = {}
    for set_name, data in results_by_set.items():
        c = find_critical_point(data)
        if c is not None:
            crits[set_name] = c

    if len(crits) > 1:
        print(f"  {DIM}Critical temptation thresholds:{RST}")
        for sn, tc in sorted(crits.items(), key=lambda x: x[1]):
            ch_info = {"classic": (B_CYN, "●"), "retaliators": (B_YLW, "◆"),
                       "full": (B_MAG, "■")}
            col, _ = ch_info.get(sn, (B_WHT,))
            print(f"    {col}T* = {tc:.1f}{RST}  {STRATEGY_SETS[sn]['name']}")
        print()

    # The insight
    print(f"  {DIM}In a well-mixed population (no spatial structure),{RST}")
    print(f"  {DIM}cooperation collapses as soon as T exceeds R = 3.{RST}")
    print(f"  {DIM}But on a grid, cooperators form clusters that protect{RST}")
    print(f"  {DIM}their interiors from exploitation by defectors.{RST}")
    print()
    print(f"  {DIM}Geography extends the range of cooperation.{RST}")
    print(f"  {DIM}The gap between 3 and T* is the 'spatial bonus' —{RST}")
    print(f"  {DIM}the extra temptation that cooperation can withstand{RST}")
    print(f"  {DIM}when agents interact locally instead of globally.{RST}")
    print()

    if crits:
        max_crit = max(crits.values())
        bonus = max_crit - 3.0
        print(f"  {BLD}Spatial bonus: ~{bonus:.1f} temptation units{RST}")
        print(f"  {DIM}Cooperation persists {bonus/3*100:.0f}% beyond the well-mixed threshold.{RST}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RST}")
