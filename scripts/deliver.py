"""deliver.py -- the only two files the user ever reads.

Everything else in this kit is scaffolding. This renders, from deck.json:

  DECKLIST.md   commander line, a plain import block (paste into Moxfield or
                Archidekt), then the same 99 grouped by package with cost and
                type.
  REPORT.md     a brief strategy report: how the deck wins, the line, the
                packages, the mana base, the known weak points -- with card
                names resolved against the deck so the report cannot reference
                a card the deck does not contain.

Neither is typed by hand. A hand-typed decklist drifts from the validated
artifact, and the drift is invisible.

deck.json supplies the prose in a `brief` object:
  {"how_it_wins": "...", "the_line": "...", "against": "...", "pilot": "..."}
Card names in prose are written [[Like This]]; the renderer strips the brackets
and reports any that are not in the 99.

Run:  python deliver.py
"""
import json
import re
import sys

import config

CARDREF = re.compile(r"\[\[([^\]]+)\]\]")
BASICS = ("Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes")
WORD_BUDGET = 900


def main():
    deck = json.load(open("deck.json", encoding="utf-8"))
    pool = config.load("POOL")
    costs = dict(zip(pool["name"], pool["mana_cost"].fillna("")))
    types = dict(zip(pool["name"], pool["type_line"].fillna("")))

    entries = deck["deck"]
    basics = deck.get("basics", {})
    innames = {config.norm(c["name"]) for c in entries} | {config.norm(b) for b in basics}
    brief = deck.get("brief", {})
    notes = deck.get("package_notes", {})

    # ---- card references in prose must resolve to the 99 ----
    unresolved = []
    for src in list(brief.values()) + list(notes.values()):
        for m in CARDREF.findall(str(src)):
            if config.norm(m) not in innames:
                unresolved.append(m)

    def plain(s):
        return CARDREF.sub(lambda m: m.group(1), str(s or ""))

    # ---------------- DECKLIST.md ----------------
    o = ["# " + deck["commander"] + " — decklist",
         f"Commander: **{deck['commander']}**  ·  colour identity {deck.get('color_identity','?')}"
         f"  ·  restriction: {deck.get('restriction', '(declared in build_spec.json)')}",
         "",
         "## Import list (paste into Moxfield / Archidekt / Tappedout)",
         "```",
         f"1 {deck['commander']}"]
    for c in entries:
        o.append(f"1 {c['name']}")
    for b, n in basics.items():
        if n:
            o.append(f"{n} {b}")
    o += ["```", ""]

    o.append("## By package")
    bypkg = {}
    for c in entries:
        bypkg.setdefault(c.get("package", "unassigned"), []).append(c)
    for pkg in sorted(bypkg):
        o.append(f"\n### {pkg.replace('_',' ')} ({len(bypkg[pkg])})")
        for c in sorted(bypkg[pkg], key=lambda x: (str(types.get(x['name'],'')), x['name'])):
            cost = costs.get(c["name"], "") or "—"
            mode = f"  · as {c['mode_taken']}" if c.get("mode_taken") else ""
            note = f"  — {plain(c['note'])}" if c.get("note") else ""
            o.append(f"- **{c['name']}** {cost} · {types.get(c['name'],'?')}{mode}{note}")
    if basics:
        o.append(f"\n### basics ({sum(basics.values())})")
        for b, n in basics.items():
            if n:
                o.append(f"- {n} × {b}")
    open("DECKLIST.md", "w", encoding="utf-8").write("\n".join(o))

    # ---------------- REPORT.md ----------------
    r = [f"# {deck['commander']} — how this deck works",
         f"*{deck.get('restriction','')}*  ·  {len(entries)} cards + "
         f"{sum(basics.values())} basics + commander",
         "",
         "## How it wins",
         plain(brief.get("how_it_wins", "(missing)")),
         "",
         "## The line",
         plain(brief.get("the_line", "(missing)")),
         "",
         "## What the deck is made of"]
    for pkg in sorted(bypkg):
        tgt = deck.get("budget", {}).get(pkg, {})
        r.append(f"\n**{pkg.replace('_',' ')}** ({len(bypkg[pkg])} cards"
                 + (f", answers {tgt.get('weakness_ref')}" if tgt.get("weakness_ref") else "")
                 + f"). {plain(notes.get(pkg, ''))}")
    r += ["", "## Against the table", plain(brief.get("against", "(missing)")),
          "", "## Piloting it", plain(brief.get("pilot", "(missing)"))]
    if deck.get("weak_slots"):
        r += ["", "## Known weak slots",
              ", ".join(deck["weak_slots"])
              + ". These are the first cards to swap when the collection grows."]
    open("REPORT.md", "w", encoding="utf-8").write("\n".join(r))

    words = len(" ".join(r).split())
    print(f"wrote DECKLIST.md ({len(entries)} entries + {sum(basics.values())} basics) "
          f"and REPORT.md ({words} words)")
    if words > WORD_BUDGET:
        print(f"NOTE: REPORT.md is {words} words, over the {WORD_BUDGET}-word brief. "
              f"Shorten deck.json's brief and re-render; do not edit REPORT.md.")
    if unresolved:
        print(f"FAIL: prose references {len(unresolved)} card(s) not in the 99: "
              f"{sorted(set(unresolved))}")
        sys.exit(1)
    print("every [[card]] reference in the prose resolves to a card in the 99")


if __name__ == "__main__":
    main()
