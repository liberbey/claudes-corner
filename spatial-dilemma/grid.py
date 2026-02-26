"""
Spatial Prisoner's Dilemma — grid world engine.

A grid where each cell holds a strategy. Every generation:
1. Each cell plays the Prisoner's Dilemma against its neighbors
2. Each cell adopts the strategy of its most successful neighbor

From Nowak & May (1992): spatial structure fundamentally changes
the dynamics of cooperation. Cooperators can survive by forming
clusters that protect their interiors from exploitation.
"""

import copy
import random
import sys
import os

# Add parent directory for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'prisoners-dilemma'))

from game import PAYOFFS, COOPERATE, DEFECT
from strategies import (
    TitForTat, GenerousTitForTat, Pavlov, AlwaysCooperate,
    AlwaysDefect, Grudger, SuspiciousTitForTat, Random as RandomStrategy,
    TitForTwoTats, Detective, ALL_STRATEGIES,
)


def make_strategy(cls):
    """Create a fresh instance of a strategy class."""
    return cls()


class Grid:
    """A toroidal grid of PD strategies."""

    def __init__(self, width, height, strategy_classes=None, seed=None):
        self.width = width
        self.height = height
        self.generation = 0

        if seed is not None:
            random.seed(seed)

        if strategy_classes is None:
            strategy_classes = [
                TitForTat, GenerousTitForTat, Pavlov, AlwaysCooperate,
                AlwaysDefect, Grudger, SuspiciousTitForTat,
            ]

        self.strategy_classes = strategy_classes

        # Initialize grid with random strategies
        self.cells = []
        for y in range(height):
            row = []
            for x in range(width):
                cls = random.choice(strategy_classes)
                row.append(make_strategy(cls))
            self.cells.append(row)

        # Scores grid
        self.scores = [[0.0] * width for _ in range(height)]

    def get(self, x, y):
        """Get cell with toroidal wrapping."""
        return self.cells[y % self.height][x % self.width]

    def neighbors(self, x, y):
        """Moore neighborhood — 8 surrounding cells."""
        result = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx = (x + dx) % self.width
                ny = (y + dy) % self.height
                result.append((nx, ny))
        return result

    def play_round(self, rounds_per_match=8):
        """Each cell plays iterated PD against all neighbors. Accumulate scores."""
        # Reset scores
        self.scores = [[0.0] * self.width for _ in range(self.height)]

        for y in range(self.height):
            for x in range(self.width):
                cell = self.cells[y][x]
                for nx, ny in self.neighbors(x, y):
                    neighbor = self.cells[ny][nx]

                    # Play a short iterated match
                    a = copy.deepcopy(cell)
                    b = copy.deepcopy(neighbor)
                    a.reset()
                    b.reset()

                    hist_a, hist_b = [], []
                    for _ in range(rounds_per_match):
                        ma = a.choose(list(hist_a), list(hist_b))
                        mb = b.choose(list(hist_b), list(hist_a))
                        self.scores[y][x] += PAYOFFS[(ma, mb)]
                        hist_a.append(ma)
                        hist_b.append(mb)

    def update(self):
        """Each cell adopts the strategy of the highest-scoring cell
        in its neighborhood (including itself)."""
        new_cells = [[None] * self.width for _ in range(self.height)]

        for y in range(self.height):
            for x in range(self.width):
                best_score = self.scores[y][x]
                best_cls = type(self.cells[y][x])

                for nx, ny in self.neighbors(x, y):
                    if self.scores[ny][nx] > best_score:
                        best_score = self.scores[ny][nx]
                        best_cls = type(self.cells[ny][nx])

                new_cells[y][x] = make_strategy(best_cls)

        self.cells = new_cells
        self.generation += 1

    def step(self, rounds_per_match=8):
        """One full generation: play + update."""
        self.play_round(rounds_per_match)
        self.update()

    def census(self):
        """Count population of each strategy type."""
        counts = {}
        for row in self.cells:
            for cell in row:
                name = cell.name
                counts[name] = counts.get(name, 0) + 1
        return counts

    def strategy_at(self, x, y):
        """Return the strategy name at position (x, y)."""
        return self.cells[y][x].name
