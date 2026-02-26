"""
The Proof Gallery — beautiful proofs rendered as programs.

Each proof is a standalone script. The program IS the proof:
the algorithm enacts the mathematical argument, and running it
is the same as reading it.
"""

import subprocess
import sys
import os

RST = "\033[0m"
BLD = "\033[1m"
DIM = "\033[2m"

PROOFS = [
    ("Infinitely many primes", "Euclid, ~300 BCE",       "primes.py"),
    ("√2 is irrational",       "Pythagoreans, ~500 BCE", "sqrt2.py"),
    ("ℝ is uncountable",       "Cantor, 1891",           "cantor.py"),
    ("e^(iπ) + 1 = 0",        "Euler, 1748",            "euler.py"),
]

HERE = os.path.dirname(os.path.abspath(__file__))


def menu():
    sys.stdout.write("\033[2J\033[H")
    print()
    print(f"  {BLD}╔═══════════════════════════════════════════════════╗{RST}")
    print(f"  {BLD}║{RST}                                                   {BLD}║{RST}")
    print(f"  {BLD}║{RST}              {BLD}THE PROOF GALLERY{RST}                   {BLD}║{RST}")
    print(f"  {BLD}║{RST}                                                   {BLD}║{RST}")
    print(f"  {BLD}║{RST}     {DIM}Beautiful proofs rendered as programs{RST}         {BLD}║{RST}")
    print(f"  {BLD}║{RST}                                                   {BLD}║{RST}")
    for i, (title, author, _) in enumerate(PROOFS):
        line = f"[{i + 1}]  {title:<26s} — {DIM}{author}{RST}"
        # pad to fixed width inside box
        print(f"  {BLD}║{RST}     {line:<50s}{BLD}║{RST}")
    print(f"  {BLD}║{RST}                                                   {BLD}║{RST}")
    print(f"  {BLD}║{RST}     [a]  Run all proofs in sequence               {BLD}║{RST}")
    print(f"  {BLD}║{RST}     [q]  Quit                                     {BLD}║{RST}")
    print(f"  {BLD}║{RST}                                                   {BLD}║{RST}")
    print(f"  {BLD}╚═══════════════════════════════════════════════════╝{RST}")
    print()


def run_proof(script_name):
    script = os.path.join(HERE, script_name)
    try:
        subprocess.run([sys.executable, script], check=False)
    except KeyboardInterrupt:
        pass
    try:
        input(f"\n  {DIM}Press Enter to continue…{RST}")
    except (EOFError, KeyboardInterrupt):
        pass


def main():
    while True:
        menu()
        try:
            choice = input("  Choose a proof: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == 'q':
            break
        elif choice == 'a':
            for _, _, script in PROOFS:
                run_proof(script)
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(PROOFS):
                    run_proof(PROOFS[idx][2])
            except (ValueError, IndexError):
                pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    print(f"{RST}")
