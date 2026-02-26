"""
Elementary cellular automata — all 256 one-dimensional rules.

The simplest possible proof that complexity doesn't require complex rules.
"""

import sys


def rule_function(rule_number: int):
    """Convert a rule number (0-255) to a lookup function.

    Each rule number encodes 8 bits, one output for each possible
    3-cell neighborhood (left, center, right). That's it. That's
    the entire specification. Everything else is emergence.
    """
    bits = format(rule_number, "08b")
    table = {7 - i: int(b) for i, b in enumerate(bits)}
    return lambda l, c, r: table[l * 4 + c * 2 + r]


def evolve(width: int, generations: int, rule_number: int):
    """Run an elementary cellular automaton.

    Start with a single lit cell in the center.
    Apply the rule. Watch what happens.
    """
    rule = rule_function(rule_number)

    row = [0] * width
    row[width // 2] = 1

    lines = []
    for _ in range(generations):
        lines.append("".join("\u2588" if c else " " for c in row))
        new_row = [0] * width
        for i in range(width):
            left = row[(i - 1) % width]
            center = row[i]
            right = row[(i + 1) % width]
            new_row[i] = rule(left, center, right)
        row = new_row

    return lines


def print_rule_table(rule_number: int):
    """Show the complete rule — all 8 neighborhood-to-output mappings."""
    rule = rule_function(rule_number)
    neighborhoods = [
        (1, 1, 1), (1, 1, 0), (1, 0, 1), (1, 0, 0),
        (0, 1, 1), (0, 1, 0), (0, 0, 1), (0, 0, 0),
    ]
    block = "\u2588"
    space = " "

    header = "  ".join(
        "".join(block if x else space for x in n)
        for n in neighborhoods
    )
    outputs = "  ".join(
        f" {block if rule(*n) else space} "
        for n in neighborhoods
    )
    print(f"Rule {rule_number}:")
    print(header)
    print(outputs)
    print()


def main():
    rule_number = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 80
    generations = int(sys.argv[3]) if len(sys.argv) > 3 else 40

    if not 0 <= rule_number <= 255:
        print("Rule number must be 0-255")
        sys.exit(1)

    print_rule_table(rule_number)
    for line in evolve(width, generations, rule_number):
        print(line)


if __name__ == "__main__":
    main()
