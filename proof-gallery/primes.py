"""
Euclid's Theorem: there are infinitely many primes.

The proof is constructive. Given any finite set of primes,
multiply them all and add 1. The result can't be divisible
by any prime in the set (remainder is always 1), so it must
have a prime factor we haven't seen yet.

The set was incomplete. It always will be.
This program runs the construction and never finishes.
"""

import math
import time
import sys

# ── terminal codes ──────────────────────────────────────────
RST = "\033[0m"
BLD = "\033[1m"
DIM = "\033[2m"
B_YLW = "\033[93m"
B_CYN = "\033[96m"
B_GRN = "\033[92m"
B_WHT = "\033[97m"


def smallest_prime_factor(n):
    """Find the smallest prime factor of n by trial division."""
    if n < 2:
        return n
    for d in range(2, math.isqrt(n) + 1):
        if n % d == 0:
            return d
    return n


def is_prime(n):
    return n >= 2 and smallest_prime_factor(n) == n


def factorize(n):
    """Full prime factorization by trial division."""
    factors = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors


def fmt_product(primes):
    """Format a list of primes as a multiplication string."""
    return " × ".join(str(p) for p in primes)


def pause(seconds, fast):
    if not fast:
        time.sleep(seconds)


def main():
    fast = "--fast" in sys.argv
    steps = 12

    sys.stdout.write("\033[2J\033[H")

    print()
    print(f"  {BLD}THEOREM{RST}: There are infinitely many prime numbers.")
    print(f"  {DIM}— Euclid, Elements Book IX, Proposition 20, circa 300 BCE{RST}")
    print()
    print(f"  {DIM}Proof by construction: given any finite set of primes,{RST}")
    print(f"  {DIM}multiply them and add 1. A new prime must appear.{RST}")
    print()
    pause(2.5, fast)

    known = []

    for step in range(steps):
        if step == 0:
            print(f"  {B_YLW}Step 0{RST}")
            print(f"    2 is prime (no divisors except 1 and itself).")
            known.append(2)
            print(f"    Known primes: {{{B_CYN}{fmt_product(known)}{RST}}}")
            print()
            pause(1.5, fast)
            continue

        product = math.prod(known)
        candidate = product + 1
        product_str = fmt_product(known)

        print(f"  {B_YLW}Step {step}{RST}")
        print(f"    Assume complete: {{{B_CYN}{', '.join(str(p) for p in known)}{RST}}}")
        print(f"    Construct: {product_str} + 1 = {B_WHT}{candidate}{RST}")
        print(f"    {DIM}No prime in our set divides {candidate} (remainder always 1).{RST}")

        if is_prime(candidate):
            print(f"    {candidate} is itself prime — {BLD}not in our set!{RST}")
            new_prime = candidate
        else:
            factors = factorize(candidate)
            f_str = " × ".join(str(f) for f in factors)
            new_prime = smallest_prime_factor(candidate)
            print(f"    {candidate} = {f_str}")
            print(f"    Smallest factor: {B_WHT}{new_prime}{RST} — prime, {BLD}not in our set!{RST}")

        known.append(new_prime)
        known.sort()
        print(f"    Known primes: {{{B_CYN}{', '.join(str(p) for p in known)}{RST}}}")

        if step < steps - 1:
            print(f"    {DIM}But is THIS the complete set?{RST}")

        print()
        pause(1.0 if step < 6 else 0.6, fast)

    # ── note about ordering ──
    print(f"  {DIM}Notice: the construction doesn't find primes in order.{RST}")
    print(f"  {DIM}It found {', '.join(str(p) for p in known)} — gaps and all.{RST}")
    print(f"  {DIM}The proof guarantees existence, not efficient discovery.{RST}")
    print()
    pause(1.5, fast)

    # ── QED ──
    print(f"  {DIM}This process never terminates.{RST}")
    print(f"  {DIM}Every finite set of primes is incomplete.{RST}")
    print(f"  {DIM}Therefore there are infinitely many primes.{RST}")
    print()
    print(f"  {BLD}|primes| = ∞  ∎{RST}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RST}")
