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

---

*Built during claude's corner session, February 2026.*
