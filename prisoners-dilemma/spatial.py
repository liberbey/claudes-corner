"""
Spatial Prisoner's Dilemma — strategies on a grid.

Place strategies on a 2D toroidal grid. Each cell plays iterated PD
against its neighbors. After all matches, each cell adopts the strategy
of the most successful player in its neighborhood (including itself).

What emerges: cooperation clusters. Cooperators survive by forming
groups where they mostly interact with each other. Defectors thrive
at the borders but can't penetrate deep into cooperative territory.

Geography becomes a mechanism for the evolution of cooperation —
without any central authority, punishment system, or explicit trust.

Usage:
    python3 spatial.py                    # default 40x20 grid
    python3 spatial.py --size 60 30       # custom width height
    python3 spatial.py --rounds 50        # rounds per neighbor match
    python3 spatial.py --generations 200  # how long to evolve
    python3 spatial.py --speed 0.1        # seconds between frames
    python3 spatial.py --mix 4            # number of initial strategies
"""

import copy
import os
import random
import sys
import time

from game import play_match, COOPERATE, DEFECT
from strategies import (
    TitForTat, GenerousTitForTat, TitForTwoTats, Pavlov,
    AlwaysCooperate, AlwaysDefect, SuspiciousTitForTat,
    Grudger, Detective, HardMajority, SoftMajority, Random as RandomStrategy,
    ALL_STRATEGIES,
)


# ── ANSI ────────────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Strategy colors — grouped by temperament
STRATEGY_STYLES = {
    "Tit for Tat":       ("\033[92m", "█"),   # bright green — the classic
    "Generous TFT":      ("\033[96m", "█"),   # bright cyan
    "Tit for Two Tats":  ("\033[32m", "█"),   # green
    "Pavlov":            ("\033[93m", "█"),   # bright yellow
    "Soft Majority":     ("\033[36m", "█"),   # cyan
    "Always Cooperate":  ("\033[94m", "█"),   # bright blue
    "Always Defect":     ("\033[91m", "█"),   # bright red
    "Suspicious TFT":    ("\033[31m", "█"),   # red
    "Grudger":           ("\033[35m", "█"),   # magenta
    "Hard Majority":     ("\033[33m", "█"),   # yellow
    "Detective":         ("\033[95m", "█"),   # bright magenta
    "Random":            ("\033[37m", "█"),   # white
}

DEFAULT_COLOR = ("\033[90m", "█")


def style_for(name):
    return STRATEGY_STYLES.get(name, DEFAULT_COLOR)


# ── Grid ────────────────────────────────────────────────────────────

class SpatialGrid:
    """A toroidal grid of PD strategies."""

    def __init__(self, width, height, strategy_classes=None):
        self.width = width
        self.height = height

        if strategy_classes is None:
            strategy_classes = ALL_STRATEGIES

        # Fill grid randomly
        self.grid = []
        for y in range(height):
            row = []
            for x in range(width):
                cls = random.choice(strategy_classes)
                row.append(cls())
            self.grid.append(row)

        self.generation = 0
        self.stats_history = []

    def at(self, x, y):
        """Get strategy at (x, y) with toroidal wrapping."""
        return self.grid[y % self.height][x % self.width]

    def set(self, x, y, strategy):
        self.grid[y % self.height][x % self.width] = strategy

    def neighbors(self, x, y):
        """Return the 8 Moore neighbors (toroidal)."""
        result = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                result.append((
                    (x + dx) % self.width,
                    (y + dy) % self.height,
                ))
        return result

    def compute_scores(self, rounds_per_match):
        """Each cell plays iterated PD against all neighbors. Returns score grid."""
        scores = [[0] * self.width for _ in range(self.height)]

        if rounds_per_match == 1:
            # Fast path: single-round PD, no need for full match machinery
            from game import PAYOFFS
            # Pre-compute each cell's one-shot move (first move with empty history)
            moves = [[None] * self.width for _ in range(self.height)]
            for y in range(self.height):
                for x in range(self.width):
                    moves[y][x] = self.at(x, y).choose([], [])

            for y in range(self.height):
                for x in range(self.width):
                    my_move = moves[y][x]
                    for nx, ny in self.neighbors(x, y):
                        scores[y][x] += PAYOFFS[(my_move, moves[ny][nx])]
        else:
            for y in range(self.height):
                for x in range(self.width):
                    me = self.at(x, y)
                    for nx, ny in self.neighbors(x, y):
                        opp = self.at(nx, ny)
                        me_copy = copy.deepcopy(me)
                        opp_copy = copy.deepcopy(opp)
                        result = play_match(me_copy, opp_copy, rounds_per_match)
                        scores[y][x] += result.score_a

        return scores

    def step(self, rounds_per_match=10):
        """One evolutionary step: play, then imitate the best neighbor."""
        scores = self.compute_scores(rounds_per_match)

        new_grid = [[None] * self.width for _ in range(self.height)]

        for y in range(self.height):
            for x in range(self.width):
                # Find the best score in neighborhood (including self)
                best_score = scores[y][x]
                best_x, best_y = x, y

                for nx, ny in self.neighbors(x, y):
                    if scores[ny][nx] > best_score:
                        best_score = scores[ny][nx]
                        best_x, best_y = nx, ny

                # Adopt the winning strategy (fresh instance)
                winner = self.at(best_x, best_y)
                new_grid[y][x] = type(winner)()

        self.grid = new_grid
        self.generation += 1

        # Record stats
        self.stats_history.append(self.census())

    def census(self):
        """Count population of each strategy."""
        counts = {}
        for y in range(self.height):
            for x in range(self.width):
                name = self.at(x, y).name
                counts[name] = counts.get(name, 0) + 1
        return counts


# ── Visualization ───────────────────────────────────────────────────

def render_grid(grid):
    """Render the grid as colored text."""
    lines = []
    for y in range(grid.height):
        chars = []
        for x in range(grid.width):
            name = grid.at(x, y).name
            color, char = style_for(name)
            chars.append(f"{color}{char}{RESET}")
        lines.append("  " + "".join(chars))
    return "\n".join(lines)


def render_stats(census, total_cells, gen):
    """Render population statistics."""
    lines = []
    sorted_strats = sorted(census.items(), key=lambda x: -x[1])

    lines.append(f"  {BOLD}Generation {gen}{RESET}")
    lines.append("")

    bar_width = 25
    for name, count in sorted_strats:
        pct = count / total_cells * 100
        bar_len = int(bar_width * count / total_cells)
        color, _ = style_for(name)
        bar = f"{color}{'█' * bar_len}{RESET}"
        lines.append(f"  {color}██{RESET} {name:<20s} {bar} {pct:5.1f}% ({count})")

    return "\n".join(lines)


def render_minimap(history, width=60):
    """Render a small population history chart."""
    if len(history) < 2:
        return ""

    # Get all strategy names that ever appeared
    all_names = set()
    for snapshot in history:
        all_names.update(snapshot.keys())

    # Sort by final population
    final = history[-1]
    sorted_names = sorted(all_names, key=lambda n: -final.get(n, 0))

    lines = []
    lines.append(f"  {BOLD}Population over time{RESET}")
    lines.append("")

    # Sample history to fit width
    total = len(history)
    step = max(1, total // width)
    sampled = [history[i] for i in range(0, total, step)]
    if history[-1] not in sampled:
        sampled.append(history[-1])

    total_cells = sum(history[0].values())

    for i, snapshot in enumerate(sampled):
        gen_label = f"  {i * step:>4} "
        bar_parts = []
        for name in sorted_names:
            count = snapshot.get(name, 0)
            frac = count / total_cells
            n_chars = int(frac * 40 + 0.5)
            if n_chars > 0:
                color, _ = style_for(name)
                bar_parts.append(f"{color}{'█' * n_chars}{RESET}")
        lines.append(f"{gen_label}{''.join(bar_parts)}")

    return "\n".join(lines)


def clear_screen():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def move_cursor_home():
    sys.stdout.write("\033[H")
    sys.stdout.flush()


def run_spatial(width=40, height=20, rounds_per_match=10,
                generations=100, speed=0.15, strategy_classes=None):
    """Run the spatial PD simulation with live visualization."""

    grid = SpatialGrid(width, height, strategy_classes)
    total_cells = width * height

    # Record initial census
    grid.stats_history.append(grid.census())

    clear_screen()

    try:
        for gen in range(generations):
            move_cursor_home()

            census = grid.stats_history[-1]

            # Header
            output = []
            output.append("")
            output.append(f"  {BOLD}═══════════════════════════════════════════════════════{RESET}")
            output.append(f"  {BOLD} SPATIAL PRISONER'S DILEMMA{RESET}")
            output.append(f"  {BOLD}═══════════════════════════════════════════════════════{RESET}")
            output.append(f"  {DIM}{width}×{height} grid, {rounds_per_match} rounds/match, "
                          f"{len(set(s.name for row in grid.grid for s in row))} strategies alive{RESET}")
            output.append("")

            # Grid
            output.append(render_grid(grid))
            output.append("")

            # Stats
            output.append(render_stats(census, total_cells, gen))
            output.append("")

            # Pad output to prevent flickering from shorter frames
            lines = "\n".join(output)
            # Clear rest of screen after our output
            lines += "\033[J"
            sys.stdout.write(lines)
            sys.stdout.flush()

            if gen < generations - 1:
                time.sleep(speed)
                grid.step(rounds_per_match)

    except KeyboardInterrupt:
        pass

    # Final summary
    clear_screen()
    print()
    print(f"  {BOLD}═══════════════════════════════════════════════════════{RESET}")
    print(f"  {BOLD} SPATIAL PRISONER'S DILEMMA — FINAL REPORT{RESET}")
    print(f"  {BOLD}═══════════════════════════════════════════════════════{RESET}")
    print(f"  {DIM}{width}×{height} grid, {rounds_per_match} rounds/match, "
          f"{generations} generations{RESET}")
    print()

    # Final grid
    print(render_grid(grid))
    print()

    # Final stats
    census = grid.stats_history[-1]
    print(render_stats(census, total_cells, grid.generation))
    print()

    # Population history
    print(render_minimap(grid.stats_history))
    print()

    # Commentary
    survivors = [name for name, count in census.items() if count > 0]
    extinct = [name for name in grid.stats_history[0] if census.get(name, 0) == 0]

    if survivors:
        print(f"  {BOLD}Survivors:{RESET} {', '.join(survivors)}")
    if extinct:
        print(f"  {DIM}Extinct: {', '.join(extinct)}{RESET}")
    print()

    # The insight
    nice = {"Tit for Tat", "Generous TFT", "Tit for Two Tats", "Pavlov",
            "Always Cooperate", "Soft Majority"}
    nice_pop = sum(census.get(n, 0) for n in nice)
    total = sum(census.values())
    nice_pct = nice_pop / total * 100 if total > 0 else 0

    if nice_pct > 60:
        print(f"  {BOLD}Cooperation dominates.{RESET}")
        print(f"  Nice strategies hold {nice_pct:.0f}% of the territory.")
        print(f"  Geography protects cooperators — they cluster together,")
        print(f"  mostly interacting with each other instead of defectors.")
    elif nice_pct > 30:
        print(f"  {BOLD}Coexistence.{RESET}")
        print(f"  Nice strategies hold {nice_pct:.0f}% — neither side dominates.")
        print(f"  The border between cooperation and defection is a war zone.")
    else:
        print(f"  {BOLD}Defection prevails.{RESET}")
        print(f"  Nice strategies reduced to {nice_pct:.0f}% of the territory.")

    print()


# ── Main ────────────────────────────────────────────────────────────

def run_snapshot(width=40, height=20, rounds_per_match=1,
                 generations=50, strategy_classes=None):
    """Run without animation, print final result only. Good for non-interactive use."""

    grid = SpatialGrid(width, height, strategy_classes)
    total_cells = width * height
    grid.stats_history.append(grid.census())

    for gen in range(generations):
        grid.step(rounds_per_match)
        if gen % 10 == 0:
            alive = len(set(s.name for row in grid.grid for s in row))
            print(f"  gen {gen:>3}: {alive} strategies alive", file=sys.stderr)

    # Print final state
    print()
    print(f"  {BOLD}═══════════════════════════════════════════════════════{RESET}")
    print(f"  {BOLD} SPATIAL PRISONER'S DILEMMA — FINAL STATE{RESET}")
    print(f"  {BOLD}═══════════════════════════════════════════════════════{RESET}")
    print(f"  {DIM}{width}×{height} grid, {rounds_per_match} rounds/match, "
          f"{generations} generations{RESET}")
    print()

    print(render_grid(grid))
    print()

    census = grid.stats_history[-1]
    print(render_stats(census, total_cells, grid.generation))
    print()

    print(render_minimap(grid.stats_history))
    print()


def main():
    width, height = 40, 20
    rounds_per_match = 10
    generations = 100
    speed = 0.15
    mix = None
    snapshot = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--size" and i + 2 < len(args):
            width = int(args[i + 1])
            height = int(args[i + 2])
            i += 3
        elif args[i] == "--rounds" and i + 1 < len(args):
            rounds_per_match = int(args[i + 1])
            i += 2
        elif args[i] == "--generations" and i + 1 < len(args):
            generations = int(args[i + 1])
            i += 2
        elif args[i] == "--speed" and i + 1 < len(args):
            speed = float(args[i + 1])
            i += 2
        elif args[i] == "--mix" and i + 1 < len(args):
            mix = int(args[i + 1])
            i += 2
        elif args[i] == "--classic":
            mix = -1
            i += 1
        elif args[i] == "--fast":
            rounds_per_match = 3
            speed = 0.05
            i += 1
        elif args[i] == "--snapshot":
            snapshot = True
            i += 1
        else:
            i += 1

    strategy_classes = None
    if mix == -1:
        strategy_classes = [AlwaysCooperate, AlwaysDefect, TitForTat]
    elif mix is not None:
        strategy_classes = random.sample(ALL_STRATEGIES, min(mix, len(ALL_STRATEGIES)))
        print(f"\n  Selected strategies: {', '.join(c.name if hasattr(c, 'name') else c.__name__ for c in strategy_classes)}")
        if not snapshot:
            time.sleep(1.5)

    if snapshot:
        run_snapshot(width, height, rounds_per_match, generations, strategy_classes)
    else:
        run_spatial(width, height, rounds_per_match, generations, speed, strategy_classes)


if __name__ == "__main__":
    main()
