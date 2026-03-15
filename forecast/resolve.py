#!/usr/bin/env python3
"""
Resolution tool for predictions.
Usage: python3 forecast/resolve.py <id_suffix> <true|false> ["resolution note"]

Examples:
  python3 forecast/resolve.py 134 true "martyrdom framing confirmed in first 3 minutes"
  python3 forecast/resolve.py 097 false "China did not formally recognize by March 17"
  python3 forecast/resolve.py --list   (show all open predictions with upcoming deadlines)
  python3 forecast/resolve.py --batch  (interactive batch resolution)
"""

import json
import sys
import datetime

PREDICTIONS_FILE = "forecast/predictions.json"


def load():
    with open(PREDICTIONS_FILE) as f:
        return json.load(f)


def save(preds):
    with open(PREDICTIONS_FILE, "w") as f:
        json.dump(preds, f, indent=2)
    print(f"Saved {PREDICTIONS_FILE}")


def get_text(p):
    """Get the statement/text from a prediction regardless of schema variant."""
    return p.get("statement") or p.get("claim") or p.get("text") or p.get("title") or ""


def find_prediction(preds, suffix):
    """Find prediction by ID suffix (e.g. '134' matches '2026-03-14-134')."""
    suffix = suffix.lstrip("#").strip()
    matches = [p for p in preds if p["id"].endswith(f"-{suffix}")]
    if len(matches) == 0:
        matches = [p for p in preds if suffix in p["id"]]
    return matches


def brier_contribution(confidence, outcome):
    """Brier score contribution: (p - o)^2"""
    o = 1 if outcome else 0
    return round((confidence - o) ** 2, 4)


def resolve(preds, suffix, outcome: bool, note: str = ""):
    matches = find_prediction(preds, suffix)
    if not matches:
        print(f"ERROR: No prediction found matching '{suffix}'")
        return False
    if len(matches) > 1:
        print(f"ERROR: Multiple matches for '{suffix}':")
        for m in matches:
            print(f"  {m['id']}: {m['statement'][:60]}...")
        return False

    p = matches[0]
    if p.get("status") == "resolved":
        print(f"WARNING: {p['id']} is already resolved (outcome={p.get('outcome')})")
        resp = input("Re-resolve? (y/N): ").strip().lower()
        if resp != "y":
            return False

    today = datetime.date.today().isoformat()
    conf = p["confidence"]
    brier = brier_contribution(conf, outcome)
    outcome_str = "TRUE" if outcome else "FALSE"

    p["status"] = "resolved"
    p["resolved_date"] = today
    p["outcome"] = outcome
    if note:
        p["resolution_note"] = note
    else:
        p["resolution_note"] = f"Resolved {today}. Outcome: {outcome_str}."

    print(f"\n{'='*60}")
    print(f"Resolving: {p['id']}")
    print(f"Statement: {get_text(p)[:80]}...")
    print(f"Confidence: {int(conf*100)}%  |  Outcome: {outcome_str}")
    print(f"Brier contribution: {brier}  (lower is better)")
    print(f"Note: {p['resolution_note']}")
    print(f"{'='*60}\n")
    return True


def list_open(preds, deadline_before=None):
    """List open predictions, sorted by deadline."""
    open_preds = [p for p in preds if p.get("status", "open") == "open"]
    if deadline_before:
        open_preds = [p for p in open_preds if p.get("deadline", "9999") <= deadline_before]
    open_preds.sort(key=lambda p: p.get("deadline", "9999"))

    print(f"\n{'='*70}")
    print(f"OPEN PREDICTIONS{' (filtered by deadline)' if deadline_before else ''}: {len(open_preds)}")
    print(f"{'='*70}")
    for p in open_preds:
        suffix = p["id"].split("-")[-1]
        deadline = p.get("deadline", "??")
        conf = int(p["confidence"] * 100)
        stmt = get_text(p)[:55]
        print(f"  #{suffix:>3}  [{deadline}]  {conf:>3}%  {stmt}...")
    print()


def batch_resolve(preds):
    """Interactive batch resolution."""
    today = datetime.date.today().isoformat()
    deadline_cutoff = input(f"Resolve predictions with deadline <= (default {today}): ").strip() or today

    candidates = [
        p for p in preds
        if p.get("status", "open") == "open" and p.get("deadline", "9999") <= deadline_cutoff
    ]
    candidates.sort(key=lambda p: p.get("deadline", "9999"))

    if not candidates:
        print("No open predictions in that deadline range.")
        return

    print(f"\nFound {len(candidates)} open predictions to resolve:\n")
    resolved_count = 0

    for p in candidates:
        suffix = p["id"].split("-")[-1]
        conf = int(p["confidence"] * 100)
        print(f"#{suffix}  [{p.get('deadline','')}]  {conf}%")
        print(f"  {get_text(p)}")
        resp = input("  Outcome? (t=true / f=false / s=skip / q=quit): ").strip().lower()

        if resp == "q":
            break
        if resp == "s" or resp == "":
            print("  Skipped.\n")
            continue

        outcome = resp.startswith("t")
        note = input(f"  Resolution note (optional): ").strip()

        resolve(preds, suffix, outcome, note)
        resolved_count += 1
        print()

    if resolved_count > 0:
        save(preds)
        print(f"\nResolved {resolved_count} predictions.")
        print_summary(preds)
    else:
        print("No changes made.")


def print_summary(preds):
    resolved = [p for p in preds if p.get("status") == "resolved"]
    correct = [p for p in resolved if p.get("outcome") is not None]
    true_count = sum(1 for p in correct if p["outcome"])

    brier_scores = []
    for p in resolved:
        if p.get("outcome") is not None and p.get("confidence") is not None:
            o = 1 if p["outcome"] else 0
            brier_scores.append((p["confidence"] - o) ** 2)

    brier_mean = sum(brier_scores) / len(brier_scores) if brier_scores else 0

    print(f"\nSUMMARY: {len(resolved)} resolved | {true_count} correct | Brier: {brier_mean:.4f}")


def main():
    preds = load()

    if len(sys.argv) == 1 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return

    if sys.argv[1] == "--list":
        cutoff = sys.argv[2] if len(sys.argv) > 2 else None
        list_open(preds, cutoff)
        return

    if sys.argv[1] == "--batch":
        batch_resolve(preds)
        return

    # Single resolution: resolve.py <id> <true|false> [note]
    if len(sys.argv) < 3:
        print("Usage: python3 forecast/resolve.py <id_suffix> <true|false> [note]")
        print("       python3 forecast/resolve.py --list [deadline]")
        print("       python3 forecast/resolve.py --batch")
        sys.exit(1)

    suffix = sys.argv[1]
    outcome_str = sys.argv[2].lower()
    if outcome_str not in ("true", "false", "t", "f", "1", "0", "yes", "no"):
        print(f"ERROR: outcome must be true/false, got '{outcome_str}'")
        sys.exit(1)
    outcome = outcome_str in ("true", "t", "1", "yes")
    note = sys.argv[3] if len(sys.argv) > 3 else ""

    if resolve(preds, suffix, outcome, note):
        save(preds)
        print_summary(preds)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
