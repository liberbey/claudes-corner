"""
Terminal visualization for the Spatial Prisoner's Dilemma.

Each strategy gets a color and symbol. The grid renders as a
colored map where you can watch cooperation clusters form,
defection fronts advance, and territorial boundaries stabilize.
"""

import shutil

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Strategy → (color_code, symbol)
# Cooperators get warm/bright colors, defectors get cold/dark ones
STYLE = {
    "Tit for Tat":       ("\033[92m", "T"),   # bright green
    "Generous TFT":      ("\033[96m", "G"),   # bright cyan
    "Pavlov":            ("\033[93m", "P"),   # bright yellow
    "Always Cooperate":  ("\033[94m", "C"),   # bright blue
    "Tit for Two Tats":  ("\033[32m", "2"),   # green
    "Soft Majority":     ("\033[36m", "S"),   # cyan
    "Grudger":           ("\033[33m", "g"),   # yellow/brown
    "Detective":         ("\033[35m", "D"),   # magenta
    "Hard Majority":     ("\033[31m", "H"),   # red
    "Suspicious TFT":    ("\033[91m", "s"),   # bright red
    "Random":            ("\033[37m", "?"),   # white
    "Always Defect":     ("\033[90m", "X"),   # gray
}

DEFAULT_STYLE = ("\033[37m", "·")


def style_for(name):
    return STYLE.get(name, DEFAULT_STYLE)


def render_grid(grid):
    """Render the grid as colored text lines."""
    lines = []
    for y in range(grid.height):
        chars = []
        for x in range(grid.width):
            name = grid.strategy_at(x, y)
            color, sym = style_for(name)
            chars.append(f"{color}{sym}{sym}{RESET}")
        lines.append("".join(chars))
    return lines


def render_census(grid, total_cells):
    """Render population counts as a sidebar."""
    census = grid.census()
    sorted_names = sorted(census.keys(), key=lambda n: -census[n])

    lines = []
    lines.append(f"{BOLD}Population{RESET}")
    lines.append("")

    bar_width = 20
    for name in sorted_names:
        count = census[name]
        pct = count / total_cells * 100
        color, sym = style_for(name)
        bar_len = max(1, int(bar_width * count / total_cells))
        bar = f"{color}{'█' * bar_len}{RESET}"
        lines.append(f"  {color}{sym}{RESET} {name:<20s} {bar} {pct:5.1f}%")

    return lines


def render_frame(grid):
    """Render a complete frame: grid + sidebar."""
    total_cells = grid.width * grid.height
    grid_lines = render_grid(grid)
    census_lines = render_census(grid, total_cells)

    # Header
    output = []
    output.append("")
    output.append(f"  {BOLD}SPATIAL PRISONER'S DILEMMA{RESET}  "
                  f"{DIM}Generation {grid.generation}  "
                  f"({grid.width}×{grid.height} = {total_cells} cells){RESET}")
    output.append("")

    # Combine grid and census side by side
    gap = "    "
    max_grid_lines = len(grid_lines)
    max_census_lines = len(census_lines)
    max_lines = max(max_grid_lines, max_census_lines)

    grid_width_chars = grid.width * 2  # each cell is 2 chars

    for i in range(max_lines):
        g = grid_lines[i] if i < max_grid_lines else ""
        c = census_lines[i] if i < max_census_lines else ""
        if i < max_grid_lines:
            output.append(f"  {g}{gap}{c}")
        else:
            padding = " " * (grid_width_chars + 2)
            output.append(f"{padding}{gap}{c}")

    output.append("")
    return "\n".join(output)


def clear_screen():
    print("\033[2J\033[H", end="")


def move_cursor_home():
    print("\033[H", end="")
