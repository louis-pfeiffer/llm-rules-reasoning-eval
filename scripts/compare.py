"""compare.py -- overlap between two builds of the same pool.

Two uses:
  1. EVALUATION. Build the same commander and restriction twice, in two chats
     that cannot see each other, and measure agreement. High overlap means the
     pool and the constraint determined the deck; low overlap means the slots
     were underdetermined and the build's confidence was not warranted by it.
  2. BASELINE. Compare a build against baseline.txt (rank-greedy). Overlap
     there is the fraction of the deck that popularity alone produced.

Accepts deck.json files or plain lists of card names, one per line.

Run:  python compare.py deck.json baseline.txt
"""
import json
import os
import sys

import config

BASICS = {"plains", "island", "swamp", "mountain", "forest", "wastes"}


def load(path):
    if path.endswith(".json"):
        d = json.load(open(path, encoding="utf-8"))
        names = [c["name"] for c in d["deck"]]
        names += [b for b, n in d.get("basics", {}).items() for _ in range(n)]
        return names
    lines = [l.strip() for l in open(path, encoding="utf-8") if l.strip()]
    out = []
    for l in lines:
        if l.startswith("```") or l.startswith("#"):
            continue
        parts = l.split(None, 1)
        if parts[0].isdigit() and len(parts) > 1:
            out += [parts[1]] * int(parts[0])
        else:
            out.append(l)
    return out


def main():
    a, b = sys.argv[1], sys.argv[2]
    A, B = load(a), load(b)
    # Basics and the commander are excluded from both sides: basics are not choices
    # a popularity sort can make (baseline.txt lists none), and counting them made
    # two builds look more alike, and a build look less like the baseline, than
    # their card choices were.
    skip = set(BASICS)
    if os.path.isfile("build_spec.json"):
        skip.add(config.norm(json.load(open("build_spec.json", encoding="utf-8")).get("commander", "")))
    A = [x for x in A if config.norm(x) not in skip]
    B = [x for x in B if config.norm(x) not in skip]
    na = {config.norm(x) for x in A}
    nb = {config.norm(x) for x in B}
    inter = na & nb
    print(f"{a}: {len(A)} non-basic cards, commander excluded ({len(na)} distinct names)")
    print(f"{b}: {len(B)} cards ({len(nb)} distinct names)")
    print(f"shared: {len(inter)}   jaccard: {len(inter)/len(na|nb):.2f}   "
          f"overlap of {a}: {len(inter)/len(na):.0%}")
    only_a = sorted(x for x in A if config.norm(x) not in nb)
    only_b = sorted(x for x in B if config.norm(x) not in na)
    print(f"\nonly in {a} ({len(set(only_a))}):")
    print("  " + ", ".join(sorted(set(only_a))))
    print(f"\nonly in {b} ({len(set(only_b))}):")
    print("  " + ", ".join(sorted(set(only_b))))


if __name__ == "__main__":
    main()
