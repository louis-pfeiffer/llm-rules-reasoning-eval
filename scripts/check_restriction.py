"""check_restriction.py -- the restriction gate on its own.

Re-reads restrictions.json (the same declaration prep.py filtered the pool with)
and re-applies it to the 99 in deck.json, card by card, from the pool file.
validate_deck.py runs the same predicate as one of its checks; this script exists
so the restriction can be confirmed in isolation -- after a red-team swap, or in
a build that skips the full validator -- and so its output names each axis the
declaration uses.

Run:   python check_restriction.py
Exit 0 clean, 1 on any violation.
"""
import json
import sys

import pandas as pd

import config
import prep

BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}


def main():
    spec_all = prep.load_restrictions()
    build = json.load(open("build_spec.json", encoding="utf-8"))
    key = build["restriction_key"]
    spec = spec_all[key]
    deck = json.load(open("deck.json", encoding="utf-8"))
    pool = config.load("POOL")

    print(f"RESTRICTION  {key}")
    print(f"  {spec.get('statement','(no statement declared)')}")

    axes = [k for k in ("allow_types", "forbid_types", "always_legal", "exempt_types",
                        "max_cmc", "min_cmc", "max_usd", "forbid_text", "require_text",
                        "require_subtype_for_type", "token_creature_subtype")
            if spec.get(k)]
    print(f"  axes checked: {axes or ['none declared']}")

    lookup = {config.norm(n): r for n, r in zip(pool["name"], pool.to_dict("records"))}
    bad, unknown = [], []
    for c in deck["deck"]:
        n = c["name"]
        if n in BASICS:
            continue
        r = lookup.get(config.norm(n))
        if r is None:
            unknown.append(n)
            continue
        if not prep.row_ok(spec, r):
            bad.append(f"{n} :: {r['type_line']} :: cmc {r.get('cmc')} :: usd {r.get('usd')}")

    basics = deck.get("basics", {})
    if spec.get("always_legal") == [] and spec.get("allow_types") and \
            "Land" not in spec.get("allow_types", []) and sum(basics.values()):
        bad.append(f"basics included ({sum(basics.values())}) but no land type is legal "
                   f"under {key}")

    print(f"\nchecked {len(deck['deck'])} entries + {sum(basics.values())} basics")
    if unknown:
        print(f"NOT IN POOL ({len(unknown)}): {unknown}")
    if bad:
        print(f"RESTRICTION VIOLATIONS ({len(bad)}):")
        for b in bad:
            print(f"  {b}")
    if not bad and not unknown:
        print("PASS -- every card in the 99 satisfies the declared restriction, "
              "re-derived from restrictions.json rather than from the pool's membership.")
    sys.exit(1 if (bad or unknown) else 0)


if __name__ == "__main__":
    main()
