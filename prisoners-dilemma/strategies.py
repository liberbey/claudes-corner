"""
Classic strategies for the iterated Prisoner's Dilemma.

Each strategy answers one question: given the history of this match,
should I cooperate or defect?

The beautiful thing about Axelrod's tournament: the winning strategies
weren't the cleverest. They were nice (never defect first), retaliatory
(punish defection), forgiving (don't hold grudges), and clear (be
predictable so opponents can learn to cooperate with you).
"""

import random


# --- The cooperators ---

class AlwaysCooperate:
    """The optimist. Always cooperates, no matter what."""
    name = "Always Cooperate"

    def choose(self, my_history, their_history):
        return True

    def reset(self):
        pass


class TitForTat:
    """Axelrod's tournament winner. Start nice, then mirror.

    Cooperate on the first move. After that, do whatever
    the opponent did last round. Four properties make it work:
    nice, retaliatory, forgiving, clear.
    """
    name = "Tit for Tat"

    def choose(self, my_history, their_history):
        if not their_history:
            return True
        return their_history[-1]

    def reset(self):
        pass


class TitForTwoTats:
    """More forgiving than TFT. Only retaliates after two consecutive defections.

    Tolerates a single defection — could be noise, could be a test.
    But two in a row? That's a pattern.
    """
    name = "Tit for Two Tats"

    def choose(self, my_history, their_history):
        if len(their_history) < 2:
            return True
        return not (their_history[-1] is False and their_history[-2] is False)

    def reset(self):
        pass


class GenerousTitForTat:
    """TFT with a 10% chance of forgiving a defection.

    Breaks out of defection spirals that regular TFT can get stuck in.
    A small amount of random generosity can stabilize cooperation.
    """
    name = "Generous TFT"

    def choose(self, my_history, their_history):
        if not their_history:
            return True
        if their_history[-1]:
            return True
        return random.random() < 0.1

    def reset(self):
        pass


class Pavlov:
    """Win-stay, lose-shift. Repeat your move if it worked, switch if it didn't.

    "Worked" means: we both cooperated, or I defected and they cooperated.
    Equivalently: cooperate iff both players made the same choice last round.

    Simpler than TFT in some ways — no concept of "retaliation",
    just a learning rule. But it can exploit unconditional cooperators
    (which TFT can't), and it recovers from mutual defection.
    """
    name = "Pavlov"

    def choose(self, my_history, their_history):
        if not my_history:
            return True
        # Cooperate iff both made the same choice last round
        return my_history[-1] == their_history[-1]

    def reset(self):
        pass


# --- The defectors ---

class AlwaysDefect:
    """The cynic. Always defects. The Nash equilibrium in a one-shot game.

    In a single round, defecting is rational regardless of the opponent.
    But iteration changes everything — being predictably hostile means
    no one will cooperate with you.
    """
    name = "Always Defect"

    def choose(self, my_history, their_history):
        return False

    def reset(self):
        pass


class SuspiciousTitForTat:
    """TFT but starts with a defection. Trust must be earned.

    The opening defection often triggers retaliation, leading to
    alternating or mutual defection. A small asymmetry in the
    opening move can cascade into very different outcomes.
    """
    name = "Suspicious TFT"

    def choose(self, my_history, their_history):
        if not their_history:
            return False
        return their_history[-1]

    def reset(self):
        pass


class Grudger:
    """Cooperates until betrayed. Then defects forever.

    Also called Grim Trigger. One defection and the relationship
    is over. The nuclear option of retaliation — maximally retaliatory,
    zero forgiveness. Effective as a deterrent but brittle:
    a single mistake (or noise) destroys cooperation permanently.
    """
    name = "Grudger"

    def __init__(self):
        self._betrayed = False

    def choose(self, my_history, their_history):
        if self._betrayed:
            return False
        if their_history and not their_history[-1]:
            self._betrayed = True
            return False
        return True

    def reset(self):
        self._betrayed = False


class Detective:
    """Probe, then adapt. Play C, D, C, C to test the opponent.

    If the opponent never retaliates during the probe, conclude
    they're exploitable and always defect. Otherwise, play TFT.

    The con artist of the tournament — cooperates with the strong,
    exploits the weak.
    """
    name = "Detective"

    _opening = [True, False, True, True]

    def __init__(self):
        self._exploit = None

    def choose(self, my_history, their_history):
        round_num = len(my_history)
        if round_num < 4:
            return self._opening[round_num]
        if self._exploit is None:
            # Did opponent ever defect during the opening?
            self._exploit = all(their_history[:4])
        if self._exploit:
            return False
        return their_history[-1]

    def reset(self):
        self._exploit = None


# --- The calculators ---

class HardMajority:
    """Defect by default. Cooperate only if opponent has cooperated
    strictly more than they've defected."""
    name = "Hard Majority"

    def choose(self, my_history, their_history):
        if not their_history:
            return False
        cooperations = sum(their_history)
        return cooperations > len(their_history) - cooperations

    def reset(self):
        pass


class SoftMajority:
    """Cooperate by default. Defect only if opponent has defected
    strictly more than they've cooperated."""
    name = "Soft Majority"

    def choose(self, my_history, their_history):
        if not their_history:
            return True
        cooperations = sum(their_history)
        return cooperations >= len(their_history) - cooperations

    def reset(self):
        pass


class Random:
    """Coin flip. The baseline — no strategy at all."""
    name = "Random"

    def choose(self, my_history, their_history):
        return random.choice([True, False])

    def reset(self):
        pass


# --- All strategies ---

ALL_STRATEGIES = [
    TitForTat,
    Pavlov,
    GenerousTitForTat,
    TitForTwoTats,
    SoftMajority,
    Grudger,
    Detective,
    HardMajority,
    SuspiciousTitForTat,
    AlwaysCooperate,
    Random,
    AlwaysDefect,
]


def create_all():
    """Instantiate one of each strategy."""
    return [cls() for cls in ALL_STRATEGIES]
