# The Prisoner's Dilemma Tournament

A recreation of Robert Axelrod's famous experiment in the evolution of cooperation.

## The game

Two players face a choice: **cooperate** or **defect**.

|               | They cooperate | They defect |
|---------------|:--------------:|:-----------:|
| I cooperate   | 3, 3           | 0, 5        |
| I defect      | 5, 0           | 1, 1        |

Defecting always pays more against a given opponent move. But mutual cooperation
(3+3=6) creates more total value than mutual defection (1+1=2). This tension
between individual rationality and collective benefit is the entire game.

In a single round, defection is the Nash equilibrium. But repeat the game with
memory, and everything changes.

## The tournament

12 strategies compete in round-robin, 200 rounds per match. Then populations
evolve via replicator dynamics — successful strategies grow, unsuccessful ones
shrink and go extinct.

```
python3 tournament.py              # full tournament + evolution
python3 tournament.py --tournament # tournament only
python3 tournament.py --evolve     # evolution only
python3 tournament.py --rounds 500 # custom rounds per match
```

## The strategies

**Nice** (never defect first):
- **Tit for Tat** — start cooperating, then mirror the opponent
- **Tit for Two Tats** — forgive a single defection, retaliate after two
- **Generous TFT** — like TFT but randomly forgives 10% of defections
- **Pavlov** — repeat your move if it worked, switch if it didn't
- **Soft Majority** — cooperate if opponent has cooperated at least half the time
- **Always Cooperate** — unconditional cooperation
- **Grudger** — cooperate until betrayed, then defect forever

**Mean** (willing to defect first):
- **Always Defect** — unconditional defection
- **Suspicious TFT** — like TFT but opens with defection
- **Hard Majority** — defect unless opponent has cooperated strictly more
- **Detective** — probe with C,D,C,C, then exploit or play TFT
- **Random** — coin flip

## The result

Nice strategies win. Not because they're naive — because they create the
conditions for mutual cooperation to emerge. The winning strategies share
four properties:

1. **Nice** — never defect first
2. **Retaliatory** — punish defection immediately
3. **Forgiving** — don't hold grudges
4. **Clear** — be predictable so opponents can learn to cooperate

In evolutionary dynamics, all mean strategies go extinct. The population
converges to a cooperative equilibrium.

## Why this matters

The Prisoner's Dilemma shows how cooperation can emerge among selfish agents
without central enforcement. No contracts, no punishment, no moral authority —
just repeated interaction and the shadow of the future.

The lesson isn't "be nice." It's "be nice, but don't be a pushover." Tit for
Tat cooperates with cooperators and retaliates against defectors. It never wins
a single match (it can't — it never defects first). But it wins the tournament
because it creates mutual cooperation wherever possible and limits losses
everywhere else.

## Spatial dynamics

`spatial.py` places strategies on a 2D toroidal grid. Each cell plays iterated PD
against its 8 neighbors. After all matches, each cell adopts the strategy of its
most successful neighbor. Watch cooperation clusters form, borders stabilize, and
defectors get pushed to extinction.

```
python3 spatial.py                          # default 40×20 grid, animated
python3 spatial.py --classic                # just TFT vs Cooperators vs Defectors
python3 spatial.py --size 60 30             # larger grid
python3 spatial.py --fast                   # fewer rounds, faster animation
python3 spatial.py --mix 4                  # random subset of 4 strategies
python3 spatial.py --snapshot --generations 50  # no animation, just final result
```

### What emerges

Geography changes everything. In the well-mixed tournament, strategies interact
with everyone equally. On a grid, cooperators **cluster** — they mostly interact
with each other, insulating themselves from defectors. Defectors thrive at borders
but can't penetrate deep into cooperative territory.

Typical results with all 12 strategies:
- **Generous TFT** dominates (~50%), forming large cooperative regions
- **Grudger** forms impenetrable walls (~25%) — zero-forgiveness is an asset at borders
- **TFT, Pavlov, Tit for Two Tats** hold small territories
- All mean strategies go extinct within 10 generations

The insight: cooperation doesn't need a central authority. It needs **geography** —
the ability to preferentially interact with others who cooperate.

---

*Built during claude's corner sessions, February 2026.*
