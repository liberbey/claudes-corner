# Spatial Prisoner's Dilemma

Strategies live on a toroidal grid. Each generation, every cell plays iterated
Prisoner's Dilemma against its 8 neighbors (Moore neighborhood). Then each cell
adopts the strategy of whichever neighbor scored highest.

The key insight from Nowak & May (1992): **spatial structure changes everything**.
In a well-mixed population, defectors can invade cooperators. But on a grid,
cooperators form clusters that protect their interiors from exploitation. Defectors
thrive on borders but can't penetrate dense cooperative regions.

This is the convergence of the two previous projects — the cellular automaton
(local rules on a grid producing emergent patterns) meets game theory (strategic
agents producing cooperation). The grid *is* the automaton. The strategies *are*
the cell states. And what emerges is geography: territories, frontiers, invasions,
and stable borders.

## Running it

```bash
# Animated simulation (default: 40×25 grid, 100 generations)
python3 spatial.py

# Custom size and duration
python3 spatial.py --size 60 30 --gens 200

# Slower animation
python3 spatial.py --speed 0.5

# Reproducible run
python3 spatial.py --seed 42

# Show population history chart at end
python3 spatial.py --history

# Single snapshot (no animation)
python3 spatial.py --snapshot
```

## What you'll see

The grid shows colored letters — each strategy has a unique color and symbol.
A sidebar shows the population breakdown. Watch for:

- **Defector extinction**: Always Defect and Suspicious TFT get eliminated early
- **Cluster formation**: cooperators form solid territories
- **Border stabilization**: once defectors are gone, territories stop changing
- **The power of geography**: strategies that win in well-mixed populations
  (the original tournament) may lose in spatial competition, and vice versa

## The strategies

Seven strategies compete (a curated subset of the original tournament):

| Symbol | Strategy | Type |
|--------|----------|------|
| T | Tit for Tat | Nice, retaliatory |
| G | Generous TFT | Nice, forgiving |
| P | Pavlov | Nice, adaptive |
| C | Always Cooperate | Nice, exploitable |
| g | Grudger | Nice, unforgiving |
| s | Suspicious TFT | Mean, retaliatory |
| X | Always Defect | Mean, exploitative |

## How it connects

| Elementary Automata | Prisoner's Dilemma Tournament | Spatial Dilemma |
|---|---|---|
| Cells on a line | Agents in a pool | Agents on a grid |
| Binary states | Cooperate/Defect | Cooperate/Defect |
| Local rules (3 neighbors) | Global competition | Local competition (8 neighbors) |
| Emergent patterns | Emergent cooperation | Emergent geography |

All three projects ask the same question: **what complex behavior can emerge
from simple, local rules?** The answer keeps being: more than you'd expect.
