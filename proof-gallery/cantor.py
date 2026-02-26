"""
Cantor's Diagonal Argument: the reals are uncountable.

Suppose someone hands you a "complete" list of all real numbers
in [0,1]. We construct a real number that differs from every
entry in the list — at position n, it disagrees with the nth entry.

Therefore the list was incomplete. No list ever can be complete.
|ℝ| > |ℕ|.
"""

import math
import time
import sys

# ── terminal codes ──────────────────────────────────────────
RST = "\033[0m"
BLD = "\033[1m"
DIM = "\033[2m"
B_RED = "\033[91m"
B_GRN = "\033[92m"
B_YLW = "\033[93m"
B_CYN = "\033[96m"
B_WHT = "\033[97m"
BG_YLW = "\033[43m"
BG_GRN = "\033[42m"
UNDERLINE = "\033[4m"

# ── the "complete" list: 10 well-known constants in [0,1] ──
CONSTANTS = [
    (math.pi / 4,        "π/4"),
    (math.e / 3,         "e/3"),
    (math.sqrt(2) - 1,   "√2 − 1"),
    (math.log(2),         "ln 2"),
    (1 / 7,               "1/7"),
    (math.sqrt(3) - 1,   "√3 − 1"),
    (math.sin(1),         "sin 1"),
    (1 / math.e,          "1/e"),
    ((math.sqrt(5) - 1) / 2,  "φ − 1"),
    (math.log(3) / 2,    "ln3 / 2"),
]

N = len(CONSTANTS)
D = 14   # digits to show


def decimal_digits(value, n):
    """Extract the first n decimal digits of a value in (0,1)."""
    digits = []
    frac = value
    for _ in range(n):
        frac *= 10
        d = int(frac)
        digits.append(d)
        frac -= d
    return digits


def pause(seconds, fast):
    if not fast:
        time.sleep(seconds)


def main():
    fast = "--fast" in sys.argv

    # precompute
    grid = [decimal_digits(val, D) for val, _ in CONSTANTS]
    diagonal = [grid[i][i] for i in range(N)]
    anti = [(d + 1) if d < 9 else 1 for d in diagonal]

    sys.stdout.write("\033[2J\033[H")

    # ── title ──
    print()
    print(f"  {BLD}THEOREM{RST}: The real numbers are uncountable.")
    print(f"  {DIM}— Georg Cantor, 1891{RST}")
    print()
    print(f"  {DIM}Proof: given any list of reals, we construct one not in it.{RST}")
    print()
    pause(2.5, fast)

    # ── phase 1: present the list ──
    print(f"  Suppose every real in [0,1] appears in this list:")
    print()
    pause(1, fast)

    for i in range(N):
        dstr = " ".join(str(d) for d in grid[i])
        name = CONSTANTS[i][1]
        print(f"    f({i + 1:2d}) = 0. {dstr} …   {DIM}{name}{RST}")
        pause(0.25, fast)

    print(f"    {DIM}  ⋮{RST}")
    print()
    pause(2, fast)

    # ── phase 2: reveal the diagonal ──
    print(f"  {BLD}The diagonal{RST}: the {UNDERLINE}nth digit of the nth entry{RST}.")
    print()
    pause(1.5, fast)

    for i in range(N):
        parts = []
        for j in range(D):
            d = str(grid[i][j])
            if j == i:
                parts.append(f"{BG_YLW}{BLD} {d} {RST}")
            else:
                parts.append(f" {DIM}{d}{RST} ")
        dstr = "".join(parts)
        name = CONSTANTS[i][1]
        print(f"    f({i + 1:2d}) = 0.{dstr}…   {DIM}{name}{RST}")
        pause(0.25, fast)

    print(f"    {DIM}  ⋮{RST}")
    print()
    pause(1.5, fast)

    # ── phase 3: construct the anti-diagonal ──
    diag_str = "  ".join(str(d) for d in diagonal)
    anti_str = "  ".join(str(d) for d in anti)

    print(f"  Diagonal reads:       {B_YLW}{diag_str}{RST}")
    pause(1, fast)
    print(f"  Choose different:     {B_GRN}{anti_str}{RST}   {DIM}(each digit + 1){RST}")
    pause(1, fast)

    anti_num = "0." + "".join(str(d) for d in anti) + "…"
    print()
    print(f"  Constructed number:   {BLD}{B_GRN}d = {anti_num}{RST}")
    print()
    pause(2, fast)

    # ── phase 4: the contradiction ──
    print(f"  {BLD}d cannot be in the list:{RST}")
    print()
    pause(0.5, fast)

    for i in range(N):
        print(f"    d ≠ f({i + 1:2d}):  digit {i + 1:2d} is "
              f"{B_GRN}{anti[i]}{RST}, but f({i + 1:2d}) has "
              f"{B_YLW}{diagonal[i]}{RST}")
        pause(0.25, fast)

    print(f"    {DIM}  ⋮{RST}")
    print(f"    d ≠ f(n):   digit n differs, {DIM}for every n.{RST}")
    print()
    pause(2, fast)

    # ── QED ──
    print(f"  {DIM}d ∈ [0,1] but d ≠ f(n) for any n ∈ ℕ.{RST}")
    print(f"  {DIM}The list was incomplete — and it always will be.{RST}")
    print(f"  {DIM}No bijection ℕ → [0,1] exists.{RST}")
    print()
    print(f"  {BLD}|ℝ| > |ℕ|  ∎{RST}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RST}")
