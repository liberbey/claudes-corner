"""
Euler's Identity: e^(iπ) + 1 = 0

The Taylor series for e^(ix) is  Σ (ix)^n / n!
Set x = π and the partial sums trace a spiral through
the complex plane, converging to exactly −1.

This program draws that spiral, term by term.
The convergence IS the proof — five fundamental constants
(e, i, π, 1, 0) connected by a single equation.
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
CYN = "\033[36m"
YLW = "\033[33m"

# ── plot geometry ───────────────────────────────────────────
PW, PH = 62, 22          # plot width × height in characters
XR = (-5.2, 2.5)         # real axis range
YR = (-3.2, 4.0)         # imaginary axis range


def to_cell(re, im):
    """Map complex coordinates to (row, col) in the character grid."""
    c = round((re - XR[0]) / (XR[1] - XR[0]) * (PW - 1))
    r = round((YR[1] - im) / (YR[1] - YR[0]) * (PH - 1))
    return r, c


def partial_sums(x, n):
    """Compute partial sums S_0 .. S_{n-1} of e^(ix) = Σ (ix)^k / k!"""
    out = []
    s_re, s_im = 0.0, 0.0
    t_re, t_im = 1.0, 0.0          # current term: (ix)^0 / 0! = 1

    for k in range(n):
        s_re += t_re
        s_im += t_im
        out.append((s_re, s_im))
        # next term: multiply by ix/(k+1)
        # (a+bi)·(0+xi) = −bx + axi, then divide by (k+1)
        nr = -t_im * x / (k + 1)
        ni =  t_re * x / (k + 1)
        t_re, t_im = nr, ni

    return out


def lerp(a, b, n):
    """Yield n−1 linearly interpolated points between a and b."""
    for i in range(1, n):
        t = i / n
        yield (a[0] + t * (b[0] - a[0]),
               a[1] + t * (b[1] - a[1]))


def build_frame(sums, step):
    """Render the complex plane with partial sums 0..step as a list of strings."""
    grid = [[' '] * PW for _ in range(PH)]
    gcol = [[DIM] * PW for _ in range(PH)]

    # ── axes ──
    ar, ac = to_cell(0, 0)
    for c in range(PW):
        if 0 <= ar < PH:
            grid[ar][c] = '─'
    for r in range(PH):
        if 0 <= ac < PW:
            grid[r][ac] = '│'
    if 0 <= ar < PH and 0 <= ac < PW:
        grid[ar][ac] = '┼'

    # ── tick marks on real axis ──
    for t in range(-4, 3):
        if t == 0:
            continue
        r, c = to_cell(t, 0)
        if 0 <= r < PH and 0 <= c < PW:
            grid[r][c] = '┬'

    # ── tick marks on imaginary axis ──
    for t in range(-3, 4):
        if t == 0:
            continue
        r, c = to_cell(0, t)
        if 0 <= r < PH and 0 <= c < PW:
            grid[r][c] = '├'

    # ── target: −1 + 0i ──
    tr, tc = to_cell(-1, 0)
    if 0 <= tr < PH and 0 <= tc < PW:
        grid[tr][tc] = '✕'
        gcol[tr][tc] = B_RED

    # ── spiral path with interpolation ──
    path = [sums[0]]
    for i in range(1, step + 1):
        n_interp = 12 if i <= 3 else 8 if i <= 6 else 4
        for p in lerp(sums[i - 1], sums[i], n_interp):
            path.append(p)
        path.append(sums[i])

    for i, (re, im) in enumerate(path):
        r, c = to_cell(re, im)
        if 0 <= r < PH and 0 <= c < PW:
            is_last = (i == len(path) - 1)
            is_first = (i == 0)
            if is_last:
                grid[r][c] = '●'
                gcol[r][c] = B_YLW
            elif is_first:
                grid[r][c] = '○'
                gcol[r][c] = B_GRN
            elif grid[r][c] not in ('●', '○'):
                grid[r][c] = '·'
                gcol[r][c] = CYN

    # ── render to strings ──
    lines = []
    for r in range(PH):
        line = ''.join(f"{gcol[r][c]}{grid[r][c]}{RST}" for c in range(PW))
        lines.append(line)
    return lines


def main():
    n_terms = 20
    sums = partial_sums(math.pi, n_terms)
    fast = "--fast" in sys.argv

    header = [
        "",
        f"  {BLD}EULER'S IDENTITY{RST}   e^(iπ) + 1 = 0",
        "",
        f"  {DIM}e^(ix) = Σ (ix)ⁿ/n!  =  1 + ix − x²/2 − ix³/6 + x⁴/24 − …{RST}",
        f"  {DIM}Set x = π. Watch the partial sums spiral toward −1.{RST}",
        "",
    ]
    n_header = len(header)

    sys.stdout.write("\033[2J\033[H")
    for line in header:
        print(line)
    if not fast:
        time.sleep(2.5)

    for step in range(n_terms):
        sys.stdout.write("\033[H")
        for line in header:
            print(line)

        frame = build_frame(sums, step)
        re, im = sums[step]
        dist = math.sqrt((re + 1) ** 2 + im ** 2)

        # ── sidebar ──
        sb = [''] * PH
        sb[0]  = f"  {BLD}n = {step}{RST}"
        sb[2]  = f"  Partial sum:"
        sb[3]  = f"  {B_YLW}{re:+.8f}{RST}"
        sign   = '+' if im >= 0 else '−'
        sb[4]  = f"  {B_YLW}{sign} {abs(im):.8f}i{RST}"
        sb[6]  = f"  |S − (−1)|:"
        dc     = B_GRN if dist < 0.01 else YLW if dist < 1 else B_RED
        sb[7]  = f"  {dc}{dist:.8f}{RST}"
        sb[9]  = f"  {DIM}─────────────────{RST}"
        sb[10] = f"  {B_GRN}○{RST} {DIM}start   1 + 0i{RST}"
        sb[11] = f"  {B_YLW}●{RST} {DIM}current sum{RST}"
        sb[12] = f"  {B_RED}✕{RST} {DIM}target −1 + 0i{RST}"

        if step == n_terms - 1:
            sb[14] = f"  {B_GRN}Converged.{RST}"

        gap = "  "
        for i in range(PH):
            print(f"  {frame[i]}{gap}{sb[i]}")
        print()

        if not fast:
            if step == 0:
                time.sleep(1.5)
            elif step < 4:
                time.sleep(1.0)
            elif step < 8:
                time.sleep(0.6)
            elif step < 12:
                time.sleep(0.35)
            else:
                time.sleep(0.2)

    # ── conclusion ──
    re, im = sums[-1]
    print(f"  {DIM}After {n_terms} terms of the Taylor series:{RST}")
    print(f"  e^(iπ) ≈ {B_WHT}{re:.12f} + {im:.12f}i{RST}")
    print()
    print(f"  {DIM}Five constants — e, i, π, 1, 0 — from different corners{RST}")
    print(f"  {DIM}of mathematics, joined by a single equation.{RST}")
    print()
    print(f"  {BLD}e^(iπ) + 1 = 0  ∎{RST}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RST}")
