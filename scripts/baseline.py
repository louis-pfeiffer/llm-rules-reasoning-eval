"""baseline.py -- the deck a popularity prior builds on its own.

The point of an LLM deckbuilder is the judgement it adds on top of what ranking
the pool by EDHREC popularity already gives you. Without a baseline there is
nothing to add it to, and a build that is 90% the rank-greedy list reads as
expert work while being a sort.

Greedy: take the N best-ranked lands, then fill to 99 - basics with the best-
ranked non-lands, obeying nothing else. No commander awareness, no curve, no
function coverage. That is the point: it is the null hypothesis.

Run:  python baseline.py --lands 34 --basics 12   ->  baseline.txt
"""
import argparse
import json
import os

import pandas as pd

import config


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lands", type=int, default=34)
    ap.add_argument("--basics", type=int, default=10)
    ap.add_argument("--out", default="baseline.txt")
    a = ap.parse_args()
    pool = config.load("POOL")
    pool["edhrec_rank"] = pd.to_numeric(pool.get("edhrec_rank"), errors="coerce")
    pool = pool.sort_values("edhrec_rank", na_position="last")
    if os.path.isfile("build_spec.json"):                 # the commander is not one of the 99
        cmd = config.norm(json.load(open("build_spec.json", encoding="utf-8")).get("commander", ""))
        pool = pool[pool["name"].map(config.norm) != cmd]
    lands = pool[pool["is_land"] == True].head(max(0, a.lands - a.basics))
    nonland = pool[pool["is_land"] != True].head(99 - a.lands)
    names = list(lands["name"]) + list(nonland["name"])
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(names))
    print(f"wrote {a.out}: {len(names)} named cards + {a.basics} basics "
          f"= {len(names) + a.basics}")
    print("This is the null hypothesis, not a deck. Compare a build against it "
          "with compare.py; overlap is how much of the build was a sort.")


if __name__ == "__main__":
    main()
