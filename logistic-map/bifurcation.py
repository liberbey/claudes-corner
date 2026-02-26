"""
The Logistic Map — from order to chaos in one equation.

    x_{n+1} = r · x_n · (1 - x_n)

Vary r from 0 to 4 and watch:
- r < 1: extinction (x → 0)
- 1 < r < 3: stable equilibrium (x → (r-1)/r)
- r ≈ 3: period-2 oscillation
- r ≈ 3.45: period-4
- r ≈ 3.54: period-8
- r ≈ 3.57: onset of chaos — the Feigenbaum point
- 3.57 < r < 4: chaos with islands of order
- r = 4: full chaos

The ratio between successive period-doubling thresholds converges to
δ = 4.6692... — the Feigenbaum constant, a universal number that appears
in ANY system transitioning from order to chaos. It's as fundamental as π.

This program renders the bifurcation diagram in the terminal and computes
the Feigenbaum constant from the period-doubling cascade.

Usage:
    python3 bifurcation.py                  # full diagram
    python3 bifurcation.py --zoom           # zoom into the chaos onset
    python3 bifurcation.py --feigenbaum     # compute the universal constant
    python3 bifurcation.py --time r=3.5     # show time series at r=3.5
    python3 bifurcation.py --lyapunov       # Lyapunov exponent plot
"""

import math
import sys
import time

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
BLU = "\033[34m"
MAG = "\033[35m"
CYN = "\033[36m"

# Density characters (6 levels from empty to solid)
DENSITY = [' ', '·', '░', '▒', '▓', '█']


def logistic(x, r):
    """One iteration of the logistic map."""
    return r * x * (1 - x)


def iterate(r, x0=0.5, warmup=500, samples=300):
    """Iterate the logistic map at parameter r.
    Discard warmup iterations, then collect samples."""
    x = x0
    for _ in range(warmup):
        x = logistic(x, r)
    results = []
    for _ in range(samples):
        x = logistic(x, r)
        results.append(x)
    return results


# ── bifurcation diagram ────────────────────────────────────

def compute_bifurcation(r_min=0.0, r_max=4.0, r_steps=200,
                        y_min=0.0, y_max=1.0, y_steps=50,
                        warmup=500, samples=200):
    """Compute a 2D density grid for the bifurcation diagram."""
    grid = [[0] * r_steps for _ in range(y_steps)]

    for col in range(r_steps):
        r = r_min + (r_max - r_min) * col / (r_steps - 1)
        points = iterate(r, warmup=warmup, samples=samples)

        for x in points:
            row = int((1.0 - (x - y_min) / (y_max - y_min)) * (y_steps - 1))
            if 0 <= row < y_steps:
                grid[row][col] += 1

    return grid


def render_bifurcation(grid, r_min, r_max, y_min, y_max, title=None):
    """Render the bifurcation diagram as terminal art."""
    y_steps = len(grid)
    r_steps = len(grid[0]) if grid else 0

    # Find max density for normalization
    max_density = max(max(row) for row in grid) if grid else 1
    if max_density == 0:
        max_density = 1

    lines = []
    if title:
        lines.append(f"  {BLD}{title}{RST}")
        lines.append("")

    for row_idx in range(y_steps):
        # Y-axis label
        y_val = y_max - (y_max - y_min) * row_idx / (y_steps - 1)
        if row_idx == 0:
            label = f"{y_val:.1f}"
        elif row_idx == y_steps - 1:
            label = f"{y_val:.1f}"
        elif row_idx == y_steps // 2:
            label = f"{(y_min + y_max) / 2:.1f}"
        else:
            label = "    "

        # Render cells
        chars = []
        for col in range(r_steps):
            density = grid[row_idx][col]
            if density == 0:
                chars.append(' ')
            else:
                # Map density to character
                normalized = density / max_density
                level = min(5, int(normalized * 6))
                char = DENSITY[level]

                # Color by r value (parameter)
                r = r_min + (r_max - r_min) * col / (r_steps - 1)
                if r < 1.0:
                    color = DIM
                elif r < 3.0:
                    color = B_CYN
                elif r < 3.57:
                    color = B_YLW
                elif r < 3.83:
                    color = B_MAG
                else:
                    color = B_RED

                chars.append(f"{color}{char}{RST}")

        row_str = ''.join(chars)
        lines.append(f"  {DIM}{label:>4s}{RST} │{row_str}│")

    # X-axis
    axis_line = "  " + " " * 4 + " └" + "─" * r_steps + "┘"
    lines.append(axis_line)

    # X-axis labels
    label_line = "  " + " " * 5
    n_labels = 5
    for i in range(n_labels + 1):
        r_val = r_min + (r_max - r_min) * i / n_labels
        pos = int(r_steps * i / n_labels)
        needed = pos - len(label_line) + 6
        if needed > 0:
            label_line += " " * needed
        label_line += f"{r_val:.1f}"
    lines.append(f"  {DIM}{label_line}{RST}")
    lines.append(f"  {DIM}{'r (growth parameter)':^{r_steps + 10}s}{RST}")

    return "\n".join(lines)


# ── time series ─────────────────────────────────────────────

def render_time_series(r, n_display=60, height=20):
    """Show the time series x_n at a specific r value."""
    # Use an irrational-ish initial condition to avoid special orbits
    # (x=0.5 at r=4 maps to 1→0→0→... immediately)
    x = 0.31830988  # ≈ 1/π
    warmup = 200
    for _ in range(warmup):
        x = logistic(x, r)
        if x < 1e-15 or x > 1 - 1e-15:
            x = 0.31830988  # restart if orbit collapses

    values = []
    for _ in range(n_display):
        x = logistic(x, r)
        if x < 1e-15 or x > 1 - 1e-15:
            x = 0.31830988
        values.append(x)

    lines = []
    lines.append(f"  {BLD}Time series at r = {r:.4f}{RST}")
    lines.append("")

    # Determine range
    vmin = max(0, min(values) - 0.02)
    vmax = min(1, max(values) + 0.02)

    for row in range(height):
        y = vmax - (vmax - vmin) * row / (height - 1)
        if row == 0:
            label = f"{y:.2f}"
        elif row == height - 1:
            label = f"{y:.2f}"
        elif row == height // 2:
            mid = (vmin + vmax) / 2
            label = f"{mid:.2f}"
        else:
            label = "    "

        chars = []
        for i, v in enumerate(values):
            v_row = int((vmax - v) / (vmax - vmin) * (height - 1))
            if v_row == row:
                chars.append(f"{B_CYN}●{RST}")
            else:
                chars.append(" ")

        lines.append(f"  {DIM}{label}{RST} │{''.join(chars)}│")

    lines.append(f"  {DIM}     └{'─' * n_display}┘{RST}")
    lines.append(f"  {DIM}      {'n (iteration)':^{n_display}s}{RST}")

    # Characterize the behavior
    unique = len(set(round(v, 6) for v in values))
    if unique == 1:
        behavior = "fixed point"
    elif unique <= 4:
        behavior = f"period-{unique} cycle"
    elif unique <= 16:
        behavior = f"period-{unique} cycle"
    else:
        behavior = "chaos"

    lines.append("")
    lines.append(f"  {DIM}Behavior: {RST}{BLD}{behavior}{RST}")
    lines.append(f"  {DIM}Unique values: {unique}, final x = {values[-1]:.8f}{RST}")

    return "\n".join(lines)


# ── Feigenbaum constant ─────────────────────────────────────

def find_superstable_points():
    """Find r values for superstable cycles of the logistic map.
    At a superstable period-2^n cycle, the critical point x=0.5
    is ON the cycle: f^{2^n}(0.5) = 0.5. This criterion is
    numerically rock-solid (no convergence issues near bifurcations).

    Returns list of (period, r_value) pairs."""
    def g(r, period):
        """f^period(0.5) - 0.5: zero at the superstable r."""
        x = 0.5
        for _ in range(period):
            x = r * x * (1 - x)
        return x - 0.5

    # Brackets containing exactly one superstable point per period.
    # Lower-period superstable points (s_0=2.0, s_1≈3.236, etc.) are
    # below each bracket, so bisection finds only the target period.
    brackets = [
        (1,   1.5,    2.5),        # s_0 ≈ 2.000
        (2,   3.0,    3.45),       # s_1 ≈ 3.236
        (4,   3.45,   3.545),      # s_2 ≈ 3.499
        (8,   3.545,  3.566),      # s_3 ≈ 3.555
        (16,  3.566,  3.5693),     # s_4 ≈ 3.567
        (32,  3.5691, 3.5698),     # s_5 ≈ 3.5692
        (64,  3.5697, 3.56993),    # s_6 ≈ 3.5698
        (128, 3.56990, 3.56996),   # s_7 ≈ 3.56992
    ]

    results = []
    for period, r_lo, r_hi in brackets:
        g_lo = g(r_lo, period)
        for _ in range(80):  # 80 bisections → ~1e-24 precision
            r_mid = (r_lo + r_hi) / 2
            g_mid = g(r_mid, period)
            if g_mid * g_lo <= 0:
                r_hi = r_mid
            else:
                r_lo = r_mid
                g_lo = g_mid
        results.append((period, (r_lo + r_hi) / 2))

    return results


def compute_feigenbaum(thresholds):
    """Compute Feigenbaum deltas from period-doubling thresholds."""
    deltas = []
    for i in range(2, len(thresholds)):
        d_prev = thresholds[i - 1] - thresholds[i - 2]
        d_curr = thresholds[i] - thresholds[i - 1]
        if d_curr > 0:
            delta = d_prev / d_curr
            deltas.append(delta)
    return deltas


def render_feigenbaum():
    """Compute and display the Feigenbaum constant from superstable cycles."""
    TRUE_DELTA = 4.669201609

    lines = []
    lines.append(f"  {BLD}THE FEIGENBAUM CONSTANT{RST}")
    lines.append(f"  {DIM}A universal number hiding in the period-doubling cascade{RST}")
    lines.append("")
    lines.append(f"  {DIM}Method: superstable cycles — f^{{2^n}}(½) = ½{RST}")
    lines.append(f"  {DIM}At these r values, the critical point sits on the orbit.{RST}")
    lines.append("")

    points = find_superstable_points()

    lines.append(f"  {BLD}Superstable cycle points:{RST}")
    lines.append("")

    r_values = [r for _, r in points]
    for i, (period, r) in enumerate(points):
        if i > 0:
            gap = r - r_values[i - 1]
            lines.append(f"  {B_CYN}Period {period:>5d}{RST}  "
                         f"r = {B_WHT}{r:.12f}{RST}  {DIM}Δr = {gap:.10f}{RST}")
        else:
            lines.append(f"  {B_CYN}Period {period:>5d}{RST}  "
                         f"r = {B_WHT}{r:.12f}{RST}")

    if len(r_values) >= 3:
        lines.append("")
        lines.append(f"  {BLD}Feigenbaum ratios  δ_n = Δr_n / Δr_{{n+1}}{RST}")
        lines.append("")

        deltas = compute_feigenbaum(r_values)
        bar_width = 40
        for i, delta in enumerate(deltas):
            error = abs(delta - TRUE_DELTA)
            color = B_GRN if error < 0.01 else B_YLW if error < 0.1 else B_RED

            fill = min(bar_width, int(bar_width * delta / (TRUE_DELTA * 1.15)))
            empty = bar_width - fill
            bar = f"{color}{'█' * fill}{DIM}{'░' * empty}{RST}"

            lines.append(f"  δ_{i + 1} = {color}{delta:10.6f}{RST} │{bar}│"
                         f"  {DIM}error: {error:.6f}{RST}")

        lines.append(f"  {'─' * 60}")
        true_fill = min(bar_width, int(bar_width / 1.15))
        true_empty = bar_width - true_fill
        lines.append(f"   δ  = {B_WHT}{TRUE_DELTA:10.6f}{RST} │"
                     f"{B_WHT}{'█' * true_fill}{RST}"
                     f"{'░' * true_empty}│"
                     f"  {BLD}exact{RST}")

        lines.append("")
        if deltas:
            best = min(deltas, key=lambda d: abs(d - TRUE_DELTA))
            error = abs(best - TRUE_DELTA)
            digits = max(0, -int(math.floor(math.log10(error)))) if error > 0 else 10
            lines.append(f"  {DIM}Best: δ ≈ {best:.6f} "
                         f"({digits} correct digits){RST}")

    lines.append("")
    lines.append(f"  {DIM}The gaps between successive doublings shrink by this ratio.{RST}")
    lines.append(f"  {DIM}Feigenbaum proved it's universal: ANY unimodal map's route{RST}")
    lines.append(f"  {DIM}to chaos yields the same constant — fluid turbulence,{RST}")
    lines.append(f"  {DIM}electronic circuits, laser dynamics, population biology.{RST}")
    lines.append(f"  {DIM}It is as fundamental as π or e.{RST}")

    return "\n".join(lines)


# ── Lyapunov exponent ───────────────────────────────────────

def lyapunov_exponent(r, x0=0.5, n=5000):
    """Compute the Lyapunov exponent for the logistic map at r.
    λ = lim (1/n) Σ ln|f'(x_i)| where f'(x) = r(1-2x)."""
    x = x0
    total = 0.0

    # Warmup
    for _ in range(500):
        x = logistic(x, r)

    for _ in range(n):
        deriv = abs(r * (1 - 2 * x))
        if deriv > 0:
            total += math.log(deriv)
        else:
            total += -100  # effectively -infinity
        x = logistic(x, r)

    return total / n


def render_lyapunov(r_min=2.5, r_max=4.0, r_steps=120, height=20):
    """Render the Lyapunov exponent as a function of r."""
    lines = []
    lines.append(f"  {BLD}LYAPUNOV EXPONENT λ(r){RST}")
    lines.append(f"  {DIM}λ > 0: chaos (nearby trajectories diverge){RST}")
    lines.append(f"  {DIM}λ < 0: order (nearby trajectories converge){RST}")
    lines.append(f"  {DIM}λ = 0: edge of chaos (bifurcation point){RST}")
    lines.append("")

    # Compute Lyapunov exponents
    lambdas = []
    for i in range(r_steps):
        r = r_min + (r_max - r_min) * i / (r_steps - 1)
        lam = lyapunov_exponent(r)
        lambdas.append(lam)

    lam_min = min(lambdas)
    lam_max = max(lambdas)

    # Extend range slightly
    lam_range = lam_max - lam_min
    lam_min -= lam_range * 0.05
    lam_max += lam_range * 0.05

    # Find the zero line row
    zero_row = int((lam_max - 0) / (lam_max - lam_min) * (height - 1))

    for row in range(height):
        lam_val = lam_max - (lam_max - lam_min) * row / (height - 1)

        if row == 0:
            label = f"{lam_val:+.1f}"
        elif row == height - 1:
            label = f"{lam_val:+.1f}"
        elif row == zero_row:
            label = " 0.0"
        else:
            label = "    "

        chars = []
        for col in range(r_steps):
            lam = lambdas[col]
            lam_row = int((lam_max - lam) / (lam_max - lam_min) * (height - 1))

            if row == zero_row:
                if lam_row == row:
                    chars.append(f"{B_WHT}●{RST}")
                else:
                    chars.append(f"{DIM}─{RST}")
            elif lam_row == row:
                if lam > 0:
                    chars.append(f"{B_RED}●{RST}")
                elif lam < -0.5:
                    chars.append(f"{B_CYN}●{RST}")
                else:
                    chars.append(f"{B_YLW}●{RST}")
            else:
                chars.append(" ")

        lines.append(f"  {DIM}{label}{RST} │{''.join(chars)}│")

    lines.append(f"  {DIM}     └{'─' * r_steps}┘{RST}")

    # X-axis labels
    label_line = "      "
    for i in range(5):
        r_val = r_min + (r_max - r_min) * i / 4
        pos = int(r_steps * i / 4)
        needed = pos - len(label_line) + 6
        if needed > 0:
            label_line += " " * needed
        label_line += f"{r_val:.2f}"
    lines.append(f"  {DIM}{label_line}{RST}")
    lines.append(f"  {DIM}{'r':^{r_steps + 10}s}{RST}")

    lines.append("")
    lines.append(f"  {B_CYN}●{RST} λ < 0: order    "
                 f"{B_YLW}●{RST} λ ≈ 0: edge    "
                 f"{B_RED}●{RST} λ > 0: chaos")

    return "\n".join(lines)


# ── main ────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    mode = "diagram"
    if "--zoom" in args:
        mode = "zoom"
    elif "--feigenbaum" in args:
        mode = "feigenbaum"
    elif "--lyapunov" in args:
        mode = "lyapunov"
    elif any(a.startswith("--time") for a in args):
        mode = "time"

    sys.stdout.write("\033[2J\033[H")
    print()
    print(f"  {BLD}{'═' * 60}{RST}")
    print(f"  {BLD} THE LOGISTIC MAP — FROM ORDER TO CHAOS{RST}")
    print(f"  {BLD}{'═' * 60}{RST}")
    print(f"  {DIM}x_{{n+1}} = r · x_n · (1 - x_n){RST}")
    print()

    if mode == "diagram":
        grid = compute_bifurcation(r_min=0.0, r_max=4.0, r_steps=120,
                                   y_min=0.0, y_max=1.0, y_steps=40,
                                   warmup=500, samples=300)
        print(render_bifurcation(grid, 0.0, 4.0, 0.0, 1.0,
                                 title="BIFURCATION DIAGRAM"))
        print()
        print(f"  {B_CYN}█{RST} convergence  "
              f"{B_YLW}█{RST} period doubling  "
              f"{B_MAG}█{RST} onset of chaos  "
              f"{B_RED}█{RST} full chaos")
        print()
        print(f"  {DIM}One equation. One parameter. Infinite complexity.{RST}")

    elif mode == "zoom":
        # Zoom into the chaos onset region
        grid = compute_bifurcation(r_min=3.4, r_max=3.7, r_steps=120,
                                   y_min=0.3, y_max=0.9, y_steps=40,
                                   warmup=1000, samples=500)
        print(render_bifurcation(grid, 3.4, 3.7, 0.3, 0.9,
                                 title="ZOOM: PERIOD-DOUBLING CASCADE (r = 3.4 to 3.7)"))
        print()
        print(f"  {DIM}Each fork doubles the period: 2 → 4 → 8 → 16 → ...{RST}")
        print(f"  {DIM}The gaps between forks shrink by the Feigenbaum ratio: δ ≈ 4.669{RST}")
        print(f"  {DIM}At r ≈ 3.5699... the period becomes infinite: chaos.{RST}")

    elif mode == "feigenbaum":
        print(render_feigenbaum())

    elif mode == "lyapunov":
        print(render_lyapunov())

    elif mode == "time":
        # Parse r value
        r = 3.5
        for a in args:
            if a.startswith("--time"):
                if "=" in a:
                    r = float(a.split("=")[1])

        # Show a few interesting r values for comparison
        interesting = [
            (2.8, "stable fixed point"),
            (3.2, "period-2 cycle"),
            (3.5, "period-4 cycle"),
            (3.56, "period-8+"),
            (3.83, "period-3 window in chaos"),
            (4.0, "full chaos"),
            (r, "selected") if r not in (2.8, 3.2, 3.5, 3.56, 3.83, 4.0) else None,
        ]
        interesting = [x for x in interesting if x is not None]

        # Remove duplicates
        seen = set()
        unique = []
        for rv, desc in interesting:
            if rv not in seen:
                seen.add(rv)
                unique.append((rv, desc))

        for rv, desc in unique:
            print(f"  {BLD}r = {rv} — {desc}{RST}")
            print(render_time_series(rv, n_display=60, height=15))
            print()

    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RST}")
