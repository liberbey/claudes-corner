"""
The Mandelbrot Set — where the logistic map meets the complex plane.

The Mandelbrot set M is the set of complex numbers c for which the iteration
    z → z² + c,  starting from z = 0
remains bounded forever.

The logistic map x → rx(1-x) is conjugated to z → z² + c by:
    c = r/2 - r²/4  (equivalently c = -(r-1)² / 4 + 1/4)

So the bifurcation diagram of the logistic map IS the Mandelbrot set,
viewed along the real axis. The main cardioid is the stable fixed-point
region. The period-2 bulb is the period-doubling region. The antenna
(real axis, c < -1.4) is the chaos region. The tiny buds and filaments
ARE the periodic windows.

Usage:
    python3 mandelbrot.py                  # full set
    python3 mandelbrot.py --zoom           # antenna: period-doubling cascade
    python3 mandelbrot.py --deep           # deep zoom into mini-brot
    python3 mandelbrot.py --connection     # the link to the logistic map
"""

import math
import sys

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

# ── density characters ──────────────────────────────────────
DENSITY = [' ', '·', '░', '▒', '▓', '█']
HALF_BLOCK_TOP = '▀'
HALF_BLOCK_BOT = '▄'
FULL_BLOCK = '█'


def fg_rgb(r, g, b):
    """24-bit foreground color."""
    return f"\033[38;2;{r};{g};{b}m"


def bg_rgb(r, g, b):
    """24-bit background color."""
    return f"\033[48;2;{r};{g};{b}m"


# ── color palettes ──────────────────────────────────────────

def palette_escape(n, max_iter):
    """Color for escaped points based on iteration count.
    Returns (r, g, b) tuple."""
    if n >= max_iter:
        return (0, 0, 0)  # interior: black

    # Smooth coloring via normalized iteration count
    t = n / max_iter

    # Deep blue → cyan → green → yellow → red → magenta → white
    if t < 0.15:
        s = t / 0.15
        return (int(10 + 20 * s), int(10 + 40 * s), int(80 + 120 * s))
    elif t < 0.35:
        s = (t - 0.15) / 0.20
        return (int(30 * (1 - s)), int(50 + 180 * s), int(200 + 55 * s))
    elif t < 0.55:
        s = (t - 0.35) / 0.20
        return (int(160 * s), int(230 - 30 * s), int(255 - 155 * s))
    elif t < 0.75:
        s = (t - 0.55) / 0.20
        return (int(160 + 95 * s), int(200 - 130 * s), int(100 - 80 * s))
    elif t < 0.90:
        s = (t - 0.75) / 0.15
        return (int(255 - 55 * s), int(70 + 30 * s), int(20 + 180 * s))
    else:
        s = (t - 0.90) / 0.10
        return (int(200 + 55 * s), int(100 + 155 * s), int(200 + 55 * s))


def palette_period(period):
    """Color for interior points based on their period.
    Returns (r, g, b) tuple."""
    colors = {
        1: (255, 255, 200),   # period 1: warm white
        2: (100, 200, 255),   # period 2: light blue
        3: (255, 100, 100),   # period 3: red
        4: (100, 255, 150),   # period 4: green
        5: (255, 180, 50),    # period 5: orange
        6: (180, 100, 255),   # period 6: purple
        7: (255, 255, 100),   # period 7: yellow
        8: (100, 255, 255),   # period 8: cyan
    }
    if period in colors:
        return colors[period]
    # Higher periods: dim gradient
    t = min(1.0, (period - 8) / 50)
    v = int(80 - 50 * t)
    return (v, v, v + 20)


# ── Mandelbrot computation ──────────────────────────────────

def mandelbrot_escape(c_re, c_im, max_iter=200):
    """Compute escape iteration for a point c in the complex plane.
    Returns (iterations, |z|²) where iterations = max_iter means bounded."""
    z_re, z_im = 0.0, 0.0
    for n in range(max_iter):
        z_re2 = z_re * z_re
        z_im2 = z_im * z_im
        if z_re2 + z_im2 > 4.0:
            return n, z_re2 + z_im2
        z_im = 2.0 * z_re * z_im + c_im
        z_re = z_re2 - z_im2 + c_re
    return max_iter, z_re * z_re + z_im * z_im


def smooth_escape(n, z_mag2, max_iter):
    """Smooth iteration count for gradient coloring."""
    if n >= max_iter:
        return max_iter
    # Normalized iteration count (avoids banding)
    if z_mag2 > 1.0:
        return n + 1.0 - math.log(math.log(math.sqrt(z_mag2))) / math.log(2.0)
    return n


def detect_period(c_re, c_im, max_iter=1000):
    """Detect the period of a bounded orbit at point c."""
    z_re, z_im = 0.0, 0.0
    # Warmup
    for _ in range(500):
        z_re2 = z_re * z_re
        z_im2 = z_im * z_im
        if z_re2 + z_im2 > 4.0:
            return -1
        z_im = 2.0 * z_re * z_im + c_im
        z_re = z_re2 - z_im2 + c_re

    # Record reference point
    ref_re, ref_im = z_re, z_im

    # Find period
    for p in range(1, max_iter + 1):
        z_re2 = z_re * z_re
        z_im2 = z_im * z_im
        if z_re2 + z_im2 > 4.0:
            return -1
        z_im = 2.0 * z_re * z_im + c_im
        z_re = z_re2 - z_im2 + c_re

        dist2 = (z_re - ref_re) ** 2 + (z_im - ref_im) ** 2
        if dist2 < 1e-16:
            return p

    return 0  # bounded but period not found


def compute_grid(x_min, x_max, y_min, y_max, width, height, max_iter=200,
                 progress=False):
    """Compute Mandelbrot escape data for a grid of points.
    Returns 2D list of (smooth_n, period) tuples."""
    grid = []
    for row in range(height):
        if progress and row % 5 == 0:
            pct = row * 100 // height
            bar = '█' * (pct // 5) + '░' * (20 - pct // 5)
            sys.stdout.write(f"\r  {DIM}[{bar}] {pct}%{RST}")
            sys.stdout.flush()
        y = y_max - (y_max - y_min) * row / (height - 1)
        line = []
        for col in range(width):
            x = x_min + (x_max - x_min) * col / (width - 1)
            n, z_mag2 = mandelbrot_escape(x, y, max_iter)
            sn = smooth_escape(n, z_mag2, max_iter)
            line.append((sn, n))
        grid.append(line)
    if progress:
        sys.stdout.write(f"\r{'':40s}\r")
        sys.stdout.flush()
    return grid


# ── rendering ───────────────────────────────────────────────

def render_halfblock(grid, max_iter, x_min, x_max, y_min, y_max):
    """Render with half-block characters for 2x vertical resolution.
    Each character cell encodes two vertically stacked pixels using
    foreground (top) and background (bottom) colors."""
    height = len(grid)
    width = len(grid[0]) if grid else 0
    lines = []

    # Process rows in pairs
    for row_pair in range(0, height - 1, 2):
        chars = []
        for col in range(width):
            sn_top, n_top = grid[row_pair][col]
            sn_bot, n_bot = grid[row_pair + 1][col]

            # Get colors
            if n_top >= max_iter:
                r_t, g_t, b_t = 15, 15, 25  # deep navy for interior
            else:
                r_t, g_t, b_t = palette_escape(sn_top, max_iter)

            if n_bot >= max_iter:
                r_b, g_b, b_b = 15, 15, 25
            else:
                r_b, g_b, b_b = palette_escape(sn_bot, max_iter)

            # Top pixel as foreground, bottom as background
            chars.append(f"{fg_rgb(r_t, g_t, b_t)}{bg_rgb(r_b, g_b, b_b)}"
                         f"{HALF_BLOCK_TOP}{RST}")

        lines.append("  " + "".join(chars))

    return lines


def render_simple(grid, max_iter, x_min, x_max, y_min, y_max):
    """Render with density characters and 16-color palette."""
    height = len(grid)
    width = len(grid[0]) if grid else 0
    lines = []

    for row in range(height):
        chars = []
        for col in range(width):
            sn, n = grid[row][col]
            if n >= max_iter:
                chars.append(f"{B_WHT}*{RST}")
            elif n == 0:
                chars.append(' ')
            else:
                # Density + color based on escape speed
                t = n / max_iter
                level = min(5, int(sn / max_iter * 12))
                char = DENSITY[level] if level < 6 else '█'

                if t < 0.1:
                    color = BLU
                elif t < 0.25:
                    color = B_BLU
                elif t < 0.4:
                    color = B_CYN
                elif t < 0.6:
                    color = B_GRN
                elif t < 0.75:
                    color = B_YLW
                elif t < 0.9:
                    color = B_RED
                else:
                    color = B_MAG

                chars.append(f"{color}{char}{RST}")

        lines.append("  " + "".join(chars))

    return lines


def print_axes(x_min, x_max, width, label="Re(c)"):
    """Print axis labels below a rendered diagram."""
    print(f"  {DIM}" + "─" * width + f"{RST}")

    # Adaptive decimal places based on range
    span = x_max - x_min
    if span < 0.01:
        fmt = "+.5f"
    elif span < 0.1:
        fmt = "+.4f"
    elif span < 1.0:
        fmt = "+.3f"
    else:
        fmt = "+.2f"

    label_line = "  "
    n_labels = 5
    for i in range(n_labels + 1):
        x_val = x_min + (x_max - x_min) * i / n_labels
        pos = int(width * i / n_labels)
        needed = pos - len(label_line) + 2
        if needed > 0:
            label_line += " " * needed
        label_line += f"{x_val:{fmt}}"
    print(f"{DIM}{label_line}{RST}")
    print(f"{DIM}{label:^{width + 4}s}{RST}")


# ── modes ───────────────────────────────────────────────────

def mode_full(use_halfblock=True):
    """Render the full Mandelbrot set."""
    # Standard view
    x_min, x_max = -2.3, 0.8
    y_min, y_max = -1.15, 1.15
    width = 120
    max_iter = 150

    if use_halfblock:
        height = 60  # 60 rows → 30 character rows with half-blocks
    else:
        height = 36

    sys.stdout.write(f"\r  {DIM}computing...{RST}")
    sys.stdout.flush()
    grid = compute_grid(x_min, x_max, y_min, y_max, width, height, max_iter)
    sys.stdout.write(f"\r{'':40s}\r")

    print(f"  {BLD}THE MANDELBROT SET{RST}")
    print(f"  {DIM}z → z² + c,  z₀ = 0{RST}")
    print(f"  {DIM}Colored by escape speed. Interior (bounded orbits) in dark.{RST}")
    print()

    if use_halfblock:
        lines = render_halfblock(grid, max_iter, x_min, x_max, y_min, y_max)
    else:
        lines = render_simple(grid, max_iter, x_min, x_max, y_min, y_max)

    for line in lines:
        print(line)

    print_axes(x_min, x_max, width)

    print()
    print(f"  {B_WHT}Main cardioid{RST}: period-1 orbits "
          f"(c where |z| stays bounded at a fixed point)")
    print(f"  {B_CYN}Period-2 bulb{RST}: the large circle to the left "
          f"(period-doubling begins)")
    print(f"  {B_YLW}Antenna{RST}: the spike along the negative real axis "
          f"(chaos region)")
    print(f"  {DIM}Every bulb, bud, and filament has a period. "
          f"Zoom in anywhere and find more.{RST}")


def mode_zoom():
    """Zoom into the antenna — the period-doubling cascade region."""
    # The junction between period-2 bulb and chaos
    x_min, x_max = -1.48, -1.22
    y_min, y_max = -0.12, 0.12
    width = 120
    max_iter = 500

    height = 60  # half-block

    sys.stdout.write(f"\r  {DIM}computing (high resolution)...{RST}")
    sys.stdout.flush()
    grid = compute_grid(x_min, x_max, y_min, y_max, width, height, max_iter)
    sys.stdout.write(f"\r{'':40s}\r")

    print(f"  {BLD}ZOOM: THE ANTENNA — PERIOD-DOUBLING CASCADE{RST}")
    print(f"  {DIM}c = {x_min} to {x_max}, zoomed into the real axis{RST}")
    print(f"  {DIM}This is the bifurcation diagram viewed from the complex plane.{RST}")
    print()

    lines = render_halfblock(grid, max_iter, x_min, x_max, y_min, y_max)
    for line in lines:
        print(line)

    print_axes(x_min, x_max, width)

    print()
    print(f"  {DIM}The period-2 bulb splits into period-4, period-8, ...{RST}")
    print(f"  {DIM}The cascade converges to c ≈ -1.4012 (the Feigenbaum point).{RST}")
    print(f"  {DIM}Beyond: chaos, with tiny copies of the whole set (mini-brots).{RST}")


def mode_deep():
    """Deep zoom into a mini-Mandelbrot in the antenna."""
    # A mini-brot near the period-3 window
    cx, cy = -1.7686668, 0.001256
    span = 0.003
    x_min = cx - span * 1.5
    x_max = cx + span * 1.5
    y_min = cy - span
    y_max = cy + span
    width = 120
    height = 60
    max_iter = 1000

    grid = compute_grid(x_min, x_max, y_min, y_max, width, height, max_iter,
                        progress=True)

    print(f"  {BLD}DEEP ZOOM: MINI-MANDELBROT{RST}")
    print(f"  {DIM}Center: c = {cx} + {cy}i{RST}")
    print(f"  {DIM}Zoom: ~1000x from the full set{RST}")
    print(f"  {DIM}A tiny copy of the entire Mandelbrot set, hidden in the antenna.{RST}")
    print()

    lines = render_halfblock(grid, max_iter, x_min, x_max, y_min, y_max)
    for line in lines:
        print(line)

    print_axes(x_min, x_max, width)

    print()
    print(f"  {DIM}Self-similarity: the whole set contains infinitely many copies{RST}")
    print(f"  {DIM}of itself, at every scale. Each copy is connected to the rest{RST}")
    print(f"  {DIM}by infinitely thin filaments. The boundary has fractal dimension 2{RST}")
    print(f"  {DIM}— it's as complicated as a surface, despite being a curve.{RST}")


def mode_connection():
    """Show the Mandelbrot-logistic map correspondence.

    The logistic map x → rx(1-x) is conjugated to z → z² + c by:
        c = r/2 - r²/4 = -(r-1)²/4 + 1/4

    So the real axis of the Mandelbrot set IS the parameter space of the
    logistic map. We show them aligned."""

    width = 100
    print(f"  {BLD}THE MANDELBROT — LOGISTIC MAP CONNECTION{RST}")
    print()
    print(f"  {DIM}The logistic map  x → rx(1-x)  is conjugated to  z → z² + c  by:{RST}")
    print(f"  {B_WHT}c = r/2 - r²/4 = -(r-1)²/4 + 1/4{RST}")
    print()
    print(f"  {DIM}So the real axis of the Mandelbrot set IS the bifurcation diagram.{RST}")
    print()

    # Part 1: Mandelbrot set on the real axis
    # Map c from -2.0 to 0.25 (the range covered by r ∈ [0, 4])
    c_min, c_max = -2.0, 0.25
    max_iter = 500

    # Compute a narrow horizontal strip of the Mandelbrot set
    strip_height = 24  # half-block → 12 rows
    y_span = 0.25
    y_min, y_max = -y_span, y_span

    sys.stdout.write(f"\r  {DIM}computing Mandelbrot strip...{RST}")
    sys.stdout.flush()
    strip_grid = compute_grid(c_min, c_max, y_min, y_max,
                              width, strip_height, max_iter)
    sys.stdout.write(f"\r{'':40s}\r")

    print(f"  {BLD}Mandelbrot set — real axis strip{RST}")
    print(f"  {DIM}Im(c) = {y_min} to {y_max}{RST}")
    print()

    strip_lines = render_halfblock(strip_grid, max_iter,
                                   c_min, c_max, y_min, y_max)
    for line in strip_lines:
        print(line)

    # C-axis labels
    print(f"  {DIM}" + "─" * width + f"{RST}")
    c_label = "  "
    for i in range(6):
        c_val = c_min + (c_max - c_min) * i / 5
        pos = int(width * i / 5)
        needed = pos - len(c_label) + 2
        if needed > 0:
            c_label += " " * needed
        c_label += f"{c_val:+.2f}"
    print(f"{DIM}{c_label}{RST}")
    print(f"{DIM}{'c (real axis)':^{width + 4}s}{RST}")

    # Part 2: Bifurcation diagram on the SAME c axis
    # For each c, compute r = 1 + sqrt(1 - 4c) (the interesting branch)
    print()
    print(f"  {BLD}Logistic map bifurcation diagram  (same c axis){RST}")
    print(f"  {DIM}r = 1 + √(1 - 4c) maps each column to the logistic parameter{RST}")
    print()

    bif_height = 30
    y_bif_min, y_bif_max = 0.0, 1.0

    sys.stdout.write(f"\r  {DIM}computing bifurcation diagram...{RST}")
    sys.stdout.flush()

    bif_grid = [[0] * width for _ in range(bif_height)]
    samples = 300
    warmup = 500

    for col in range(width):
        c = c_min + (c_max - c_min) * col / (width - 1)
        # Convert c to logistic r: c = r/2 - r²/4 → r = 1 + √(1-4c)
        disc = 1 - 4 * c
        if disc < 0:
            continue  # c > 0.25, no real logistic parameter
        r = 1 + math.sqrt(disc)
        if r < 0 or r > 4:
            continue

        x = 0.31830988  # 1/π
        for _ in range(warmup):
            x = r * x * (1 - x)
            if x < 1e-15 or x > 1 - 1e-15:
                x = 0.31830988
        for _ in range(samples):
            x = r * x * (1 - x)
            if x < 1e-15 or x > 1 - 1e-15:
                x = 0.31830988
            row = int((1.0 - (x - y_bif_min) / (y_bif_max - y_bif_min))
                      * (bif_height - 1))
            if 0 <= row < bif_height:
                bif_grid[row][col] += 1

    sys.stdout.write(f"\r{'':40s}\r")

    max_density = max(max(row) for row in bif_grid) or 1
    for row_idx in range(bif_height):
        chars = []
        for col in range(width):
            density = bif_grid[row_idx][col]
            if density == 0:
                chars.append(' ')
            else:
                normalized = density / max_density
                level = min(5, int(normalized * 6))
                char = DENSITY[level]
                # Color by c regime
                c = c_min + (c_max - c_min) * col / (width - 1)
                if c > 0:
                    color = DIM
                elif c > -0.75:
                    color = B_CYN
                elif c > -1.40:
                    color = B_YLW
                elif c > -1.75:
                    color = B_MAG
                else:
                    color = B_RED
                chars.append(f"{color}{char}{RST}")
        # Y-axis label
        y_val = y_bif_max - (y_bif_max - y_bif_min) * row_idx / (bif_height - 1)
        if row_idx == 0:
            label = f"{y_val:.1f}"
        elif row_idx == bif_height - 1:
            label = f"{y_val:.1f}"
        elif row_idx == bif_height // 2:
            label = f"{(y_bif_min + y_bif_max) / 2:.1f}"
        else:
            label = "    "
        print(f"  {DIM}{label:>4s}{RST} │{''.join(chars)}│")

    # C-axis labels (same as above)
    print(f"  {DIM}     └" + "─" * width + f"┘{RST}")
    c_label2 = "       "
    for i in range(6):
        c_val = c_min + (c_max - c_min) * i / 5
        pos = int(width * i / 5)
        needed = pos - len(c_label2) + 7
        if needed > 0:
            c_label2 += " " * needed
        c_label2 += f"{c_val:+.2f}"
    print(f"  {DIM}{c_label2}{RST}")
    print(f"  {DIM}{'c (same axis as Mandelbrot strip above)':^{width + 10}s}{RST}")

    # Part 3: The mapping between r and c
    print()
    print(f"  {BLD}Parameter correspondence:{RST}")
    print()

    landmarks = [
        (1.0, "extinction threshold"),
        (2.0, "superstable fixed point"),
        (3.0, "period-doubling onset"),
        (3.449, "period-4 onset"),
        (3.544, "period-8 onset"),
        (3.570, "Feigenbaum point (chaos)"),
        (3.830, "period-3 window"),
        (4.0, "full chaos / band merging"),
    ]

    for r, desc in landmarks:
        c = r / 2 - r * r / 4
        # Color based on regime
        if r < 1:
            color = DIM
        elif r < 3:
            color = B_CYN
        elif r < 3.57:
            color = B_YLW
        elif r < 3.83:
            color = B_MAG
        else:
            color = B_RED
        print(f"  {color}r = {r:.3f}  →  c = {c:+.4f}{RST}  {DIM}{desc}{RST}")

    print()
    print(f"  {DIM}The two diagrams are the same mathematical object.{RST}")
    print(f"  {DIM}The Mandelbrot set extends this to the full complex plane —{RST}")
    print(f"  {DIM}what the logistic map would look like with a complex parameter.{RST}")


# ── main ────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    mode = "full"
    if "--zoom" in args:
        mode = "zoom"
    elif "--deep" in args:
        mode = "deep"
    elif "--connection" in args:
        mode = "connection"

    simple = "--simple" in args  # force 16-color mode

    sys.stdout.write("\033[2J\033[H")
    print()
    print(f"  {BLD}{'═' * 60}{RST}")
    print(f"  {BLD} THE MANDELBROT SET{RST}")
    print(f"  {BLD}{'═' * 60}{RST}")
    print(f"  {DIM}z_{{n+1}} = z_n² + c,  z₀ = 0{RST}")
    print()

    if mode == "full":
        mode_full(use_halfblock=not simple)
    elif mode == "zoom":
        mode_zoom()
    elif mode == "deep":
        mode_deep()
    elif mode == "connection":
        mode_connection()

    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RST}")
