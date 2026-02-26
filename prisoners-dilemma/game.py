"""
The Prisoner's Dilemma — core game mechanics.

Two players. One choice each: cooperate or defect.
The payoff matrix encodes the fundamental tension between
individual rationality and collective benefit.

Defecting always pays more against a given opponent move.
But mutual cooperation beats mutual defection.
That gap is where all the interesting behavior lives.
"""

from dataclasses import dataclass, field

# Actions
COOPERATE = True
DEFECT = False

# Standard payoff matrix (Axelrod's values)
# T > R > P > S  and  2R > T + S
PAYOFFS = {
    (COOPERATE, COOPERATE): 3,  # R: reward for mutual cooperation
    (COOPERATE, DEFECT):    0,  # S: sucker's payoff
    (DEFECT,    COOPERATE): 5,  # T: temptation to defect
    (DEFECT,    DEFECT):    1,  # P: punishment for mutual defection
}


@dataclass
class MatchResult:
    strategy_a: str
    strategy_b: str
    score_a: int
    score_b: int
    rounds: int
    cooperation_a: float  # fraction of rounds a cooperated
    cooperation_b: float


def play_match(a, b, rounds: int = 200) -> MatchResult:
    """Play an iterated Prisoner's Dilemma match between two strategies."""
    a.reset()
    b.reset()

    history_a: list[bool] = []
    history_b: list[bool] = []
    score_a = 0
    score_b = 0

    for _ in range(rounds):
        # Each player sees the history so far (copies to prevent mutation)
        move_a = a.choose(list(history_a), list(history_b))
        move_b = b.choose(list(history_b), list(history_a))

        score_a += PAYOFFS[(move_a, move_b)]
        score_b += PAYOFFS[(move_b, move_a)]

        history_a.append(move_a)
        history_b.append(move_b)

    coop_a = sum(history_a) / rounds if rounds > 0 else 0
    coop_b = sum(history_b) / rounds if rounds > 0 else 0

    return MatchResult(
        a.name, b.name,
        score_a, score_b,
        rounds,
        coop_a, coop_b,
    )
