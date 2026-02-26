# Elementary Cellular Automata

Stephen Wolfram catalogued all 256 possible one-dimensional cellular automata
rules. Some produce nothing. Some produce repetition. And some — Rule 30,
Rule 110 — produce complexity indistinguishable from randomness, from rules
you can state in a single sentence.

Rule 110 is Turing complete. A line of cells, each looking only at itself and
its two neighbors, deciding to be on or off — and that's enough to compute
anything computable. The universe doesn't need much.

This is a tiny program that renders any of the 256 rules in your terminal.

## Usage

```
python automaton.py [rule_number] [width] [generations]
python automaton.py 30
python automaton.py 110 80 40
python automaton.py 90 120 60
```

## Favorites

- **Rule 30**: Chaos from order. Used by Mathematica for randomness.
- **Rule 90**: Sierpinski triangle. Fractal beauty from a trivial rule.
- **Rule 110**: Turing complete. Proof that complexity needs almost nothing.
- **Rule 184**: Traffic flow model. Cars and gaps, nothing more.
