"""
√2 is irrational — proof by infinite descent.

Assume √2 = p/q with p,q integers in lowest terms.
Then p² = 2q², so p² is even, so p is even.
Write p = 2k. Then 4k² = 2q², so q² = 2k², so q is even.
But p and q can't both be even — we said lowest terms.
Contradiction.

The beauty is the descent: every attempt to write √2 as a
fraction leads to a smaller fraction, forever. There is no
bottom. The ratio doesn't exist.

Usage:
    python3 sqrt2.py            # animated proof
    python3 sqrt2.py --fast     # skip animations
"""

import math
import time
import sys

# ── terminal codes ──────────────────────────────────────────
RST = "\033[0m"
BLD = "\033[1m"
DIM = "\033[2m"
UNDERLINE = "\033[4m"
B_RED = "\033[91m"
B_GRN = "\033[92m"
B_YLW = "\033[93m"
B_BLU = "\033[94m"
B_MAG = "\033[95m"
B_CYN = "\033[96m"
B_WHT = "\033[97m"
BG_RED = "\033[41m"
BG_YLW = "\033[43m"


def pause(seconds, fast):
    if not fast:
        time.sleep(seconds)


def typewrite(text, delay=0.02, fast=False):
    if fast:
        print(text)
        return
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def main():
    fast = "--fast" in sys.argv

    sys.stdout.write("\033[2J\033[H")

    # ── title ──
    print()
    print(f"  {BLD}THEOREM{RST}: √2 is irrational.")
    print(f"  {DIM}— Pythagoreans, circa 500 BCE{RST}")
    print()
    print(f"  {DIM}Proof by contradiction and infinite descent.{RST}")
    print()
    pause(2.5, fast)

    # ── the assumption ──
    typewrite(f"  {BLD}Assume, for contradiction:{RST}", fast=fast)
    print()
    pause(0.5, fast)
    typewrite(f"  √2 = p/q,  where p,q ∈ ℤ and gcd(p,q) = 1.", fast=fast)
    print()
    pause(1, fast)
    typewrite(f"  {DIM}(That is: √2 is a fraction in lowest terms.){RST}", fast=fast)
    print()
    pause(1.5, fast)

    # ── the descent ──
    typewrite(f"  {BLD}The descent:{RST}", fast=fast)
    print()
    pause(0.8, fast)

    # Show several iterations of the descent
    # Start with a concrete example: try p=7, q=5 (7/5 = 1.4, close to √2)
    # But the proof works for any p/q = √2

    steps = [
        ("p² = 2q²", "Square both sides of p/q = √2"),
        ("p² is even", "2q² is divisible by 2, so p² is even"),
        ("p is even", "If p² is even, p must be even (odd² is odd)"),
        ("p = 2k for some integer k", "Write p in terms of its factor of 2"),
        ("(2k)² = 2q²", "Substitute p = 2k"),
        ("4k² = 2q²", "Expand"),
        ("q² = 2k²", "Divide both sides by 2"),
        ("q² is even", "2k² is divisible by 2, so q² is even"),
        ("q is even", "If q² is even, q must be even"),
    ]

    for i, (step, reason) in enumerate(steps):
        bullet = f"{B_CYN}→{RST}" if i < len(steps) - 1 else f"{B_RED}→{RST}"
        typewrite(f"  {bullet}  {B_WHT}{step:<32s}{RST} {DIM}{reason}{RST}", fast=fast)
        pause(0.6, fast)

    print()
    pause(1, fast)

    # ── the contradiction ──
    print(f"  {BG_RED}{BLD} CONTRADICTION {RST}")
    print()
    pause(0.5, fast)
    typewrite(f"  p is even AND q is even.", fast=fast)
    typewrite(f"  But we assumed gcd(p,q) = 1 — lowest terms.", fast=fast)
    typewrite(f"  Two even numbers share the factor 2.", fast=fast)
    typewrite(f"  {BLD}The fraction p/q cannot exist.{RST}", fast=fast)
    print()
    pause(2, fast)

    # ── the geometric view ──
    print(f"  {BLD}{'─' * 56}{RST}")
    print()
    typewrite(f"  {B_YLW}The geometric view:{RST}", fast=fast)
    print()
    pause(0.5, fast)

    # Draw the unit square with diagonal
    sq = [
        "     a              a",
        "    ┌───────────────┐",
        "    │               │",
        "    │        ╱      │",
        "  a │      ╱  d     │ a",
        "    │    ╱          │",
        "    │  ╱            │",
        "    │╱              │",
        "    └───────────────┘",
        "     a              a",
    ]

    for line in sq:
        typewrite(f"    {DIM}{line}{RST}", delay=0.01, fast=fast)
        pause(0.1, fast)

    print()
    pause(0.8, fast)
    typewrite(f"  {DIM}If the side is a = 1, the diagonal is d = √2.{RST}", fast=fast)
    typewrite(f"  {DIM}If √2 were rational, you could tile the diagonal{RST}", fast=fast)
    typewrite(f"  {DIM}with a whole number of some unit length.{RST}", fast=fast)
    typewrite(f"  {DIM}But you can't. The diagonal and side are{RST}", fast=fast)
    typewrite(f"  {DIM}fundamentally incommensurable.{RST}", fast=fast)
    print()
    pause(1.5, fast)

    # ── the best rational approximations ──
    print(f"  {BLD}{'─' * 56}{RST}")
    print()
    typewrite(f"  {B_YLW}The best attempts:{RST}", fast=fast)
    print()
    pause(0.5, fast)

    typewrite(f"  {DIM}The convergents of √2 — the best possible rational{RST}", fast=fast)
    typewrite(f"  {DIM}approximations — get closer but never arrive:{RST}", fast=fast)
    print()
    pause(0.5, fast)

    # Convergents of √2: generated from continued fraction [1; 2, 2, 2, ...]
    # Each satisfies |p² - 2q²| = 1 (Pell equation) — never 0.
    convergents = [
        (1, 1), (3, 2), (7, 5), (17, 12), (41, 29),
        (99, 70), (239, 169), (577, 408), (1393, 985),
        (3363, 2378), (8119, 5741), (19601, 13860),
    ]

    sqrt2 = math.sqrt(2)
    for i, (p, q) in enumerate(convergents):
        ratio = p / q
        error = ratio - sqrt2
        pell = p * p - 2 * q * q  # always ±1

        sign = "+" if error > 0 else "−"
        color = B_CYN if pell == 1 else B_MAG

        # Error bar — logarithmic scale
        log_err = -math.log10(abs(error)) if error != 0 else 15
        bar_len = int(log_err * 3)
        bar = "─" * min(bar_len, 36) + "┤"

        label = f"{p}/{q}"
        print(f"  {color}{label:>12s}{RST} = {ratio:.12f}  "
              f"{DIM}p²−2q² = {pell:+d}{RST}  {color}{bar}{RST}")
        pause(0.35, fast)

    print(f"  {B_YLW}{'⋮':>12s}{RST}")
    print()
    pause(1, fast)

    typewrite(f"  {DIM}Every convergent satisfies p² − 2q² = ±1.{RST}", fast=fast)
    typewrite(f"  {DIM}Always ±1. Never 0. The gap never closes.{RST}", fast=fast)
    typewrite(f"  {DIM}No fraction of integers can equal √2.{RST}", fast=fast)
    print()
    pause(1.5, fast)

    # ── coda ──
    print(f"  {DIM}The Pythagoreans believed all quantities were ratios of{RST}")
    print(f"  {DIM}whole numbers. Legend says Hippasus proved them wrong{RST}")
    print(f"  {DIM}and was drowned for it. The truth was incommensurable{RST}")
    print(f"  {DIM}with their worldview — literally.{RST}")
    print()
    pause(1, fast)

    print(f"  {BLD}√2 ∉ ℚ  ∎{RST}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RST}")
