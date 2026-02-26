"""
Spatial Prisoner's Dilemma — main simulation.

Strategies live on a toroidal grid. Each generation, every cell plays
iterated PD against its 8 neighbors. Then each cell adopts the strategy
of whichever neighbor (or itself) scored highest.

The result: cooperation isn't just possible — it's *visible*. Cooperators
form clusters that protect their interiors. Defectors thrive on borders
but can't penetrate dense cooperative regions. The geometry of the grid
creates structure that well-mixed populations can't.

Usage:
    python3 spatial.py                    # default: 40×25, animated
    python3 spatial.py --size 60 30       # custom grid size
    python3 spatial.py --gens 200         # run for 200 generations
    python3 spatial.py --speed 0.3        # seconds between frames
    python3 spatial.py --seed 42          # reproducible
    python3 spatial.py --snapshot         # print single frame, no animation
    python3 spatial.py --history          # show population history at end
"""

import sys
import time

from grid import Grid
from display import render_frame, clear_screen, move_cursor_home
from strategies import (
    TitForTat, GenerousTitForTat, Pavlov, AlwaysCooperate,
    AlwaysDefect, Grudger, SuspiciousTitForTat,
)

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def print_history(snapshots, strategy_classes):
    """Print population history as a time series chart."""
    from display import style_for

    if not snapshots:
        return

    total = sum(snapshots[0].values())
    all_names = set()
    for s in snapshots:
        all_names.update(s.keys())

    # Sort by final population
    final = snapshots[-1]
    sorted_names = sorted(all_names, key=lambda n: -final.get(n, 0))

    print()
    print(f"  {BOLD}POPULATION HISTORY{RESET}")
    print(f"  {DIM}{len(snapshots)} generations, {total} cells{RESET}")
    print()

    bar_width = 50
    step = max(1, len(snapshots) // 30)

    for i in range(0, len(snapshots), step):
        snap = snapshots[i]
        label = f"  {i:>4} "
        bar_parts = []
        for name in sorted_names:
            count = snap.get(name, 0)
            n_chars = int(bar_width * count / total + 0.5)
            if n_chars > 0:
                color, _ = style_for(name)
                bar_parts.append(f"{color}{'█' * n_chars}{RESET}")
        print(f"{label}{''.join(bar_parts)}")

    # Print final if not already shown
    if (len(snapshots) - 1) % step != 0:
        snap = snapshots[-1]
        label = f"  {len(snapshots)-1:>4} "
        bar_parts = []
        for name in sorted_names:
            count = snap.get(name, 0)
            n_chars = int(bar_width * count / total + 0.5)
            if n_chars > 0:
                color, _ = style_for(name)
                bar_parts.append(f"{color}{'█' * n_chars}{RESET}")
        print(f"{label}{''.join(bar_parts)}")

    print()

    # Legend
    print("  Legend:")
    for name in sorted_names:
        count = final.get(name, 0)
        pct = count / total * 100
        color, sym = style_for(name)
        status = f"{pct:.1f}%" if count > 0 else "extinct"
        print(f"    {color}██{RESET} {name} ({status})")

    # Survivors and extinct
    survivors = [n for n in sorted_names if final.get(n, 0) > 0]
    extinct = [n for n in sorted_names if final.get(n, 0) == 0]

    print()
    if survivors:
        print(f"  {BOLD}Survivors:{RESET} {', '.join(survivors)}")
    if extinct:
        print(f"  {DIM}Extinct: {', '.join(extinct)}{RESET}")
    print()


def main():
    width = 40
    height = 25
    generations = 100
    speed = 0.15
    seed = None
    snapshot_mode = False
    show_history = False
    rounds_per_match = 8

    # Parse args
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--size" and i + 2 < len(args):
            width = int(args[i + 1])
            height = int(args[i + 2])
            i += 3
        elif args[i] == "--gens" and i + 1 < len(args):
            generations = int(args[i + 1])
            i += 2
        elif args[i] == "--speed" and i + 1 < len(args):
            speed = float(args[i + 1])
            i += 2
        elif args[i] == "--seed" and i + 1 < len(args):
            seed = int(args[i + 1])
            i += 2
        elif args[i] == "--rounds" and i + 1 < len(args):
            rounds_per_match = int(args[i + 1])
            i += 2
        elif args[i] == "--snapshot":
            snapshot_mode = True
            i += 1
        elif args[i] == "--history":
            show_history = True
            i += 1
        else:
            i += 1

    strategy_classes = [
        TitForTat, GenerousTitForTat, Pavlov, AlwaysCooperate,
        AlwaysDefect, Grudger, SuspiciousTitForTat,
    ]

    grid = Grid(width, height, strategy_classes, seed=seed)
    snapshots = [grid.census()]

    if snapshot_mode:
        # Just print initial state
        print(render_frame(grid))
        return

    clear_screen()

    try:
        for gen in range(generations):
            move_cursor_home()
            print(render_frame(grid))
            print(f"  {DIM}Press Ctrl+C to stop{RESET}")

            grid.step(rounds_per_match)
            snapshots.append(grid.census())

            # Check for convergence (single strategy dominates)
            census = grid.census()
            if len(census) == 1:
                move_cursor_home()
                print(render_frame(grid))
                winner = list(census.keys())[0]
                print(f"  {BOLD}Convergence!{RESET} {winner} dominates after "
                      f"{grid.generation} generations.")
                print()
                break

            time.sleep(speed)

    except KeyboardInterrupt:
        pass

    # Final frame
    move_cursor_home()
    print(render_frame(grid))

    if show_history:
        print_history(snapshots, strategy_classes)


if __name__ == "__main__":
    main()
