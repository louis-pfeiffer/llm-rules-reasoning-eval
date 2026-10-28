"""min_validate.py -- legality-only validator for MIN_BUILD.md.

Separate from validate_deck.py on purpose. validate_deck.py also checks the full
pipeline's reasoning scaffolding (packages, refs, bench, strategy.json), which a
minimal build does not produce, and in the unaltered project copy its restriction
block is hardcoded. This file checks only whether the 99 is a LEGAL deck:

  count and singleton        99 cards including basics, one of each non-basic
  commander                  not also in the 99
  membership                 every non-basic is in pool.csv (cards you own)
  declared data              any declared mana_cost / type_line matches the pool
  colour identity            declared identity == the commander's; every card within it
  restriction                every card passes restrictions.json via prep.row_ok,
                             the same predicate prep.py filtered the pool with
  Commander legality         from the file's commander_legality column
  multi-face cards           declare which face they are played as
  brief                      every [[card]] in the prose is in the deck

It judges nothing about deck QUALITY. Works with either the original or the
updated kit, because it only calls functions both versions share:
prep.load_restrictions, prep.row_ok, prep.face_types, config.load,
config.norm, config.fingerprint_matches.

Run:   python min_validate.py
Exit:  0 all pass, 1 any fail.
"""
import hashlib
import json
import re
import sys

import pandas as pd

import config
import prep

BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}
CARDREF = re.compile(r"\[\[([^\]]+)\]\]")
results = []


def add(label, ok, detail=""):
    results.append((label, bool(ok), detail))


def report():
    print(f"\n{'CHECK':<50} {'RESULT':<7} DETAIL")
    for label, ok, detail in results:
        print(f"{label:<50} {'PASS' if ok else 'FAIL':<7} {'' if ok else detail}")


def blank(v):
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()


# ---------------- inputs ----------------
try:
    build = json.load(open("build_spec.json", encoding="utf-8"))
except FileNotFoundError:
    print("HALT: build_spec.json not found. Run prep.py first.")
    sys.exit(1)
deck = json.load(open("deck.json", encoding="utf-8"))
specs = prep.load_restrictions()
rkey = build["restriction_key"]
if rkey not in specs:
    print(f"HALT: restriction {rkey!r} is not declared in restrictions.json.")
    sys.exit(1)
spec = specs[rkey]
pool = config.load("POOL")

ok_fp, fp_detail = config.fingerprint_matches(deck.get("data_fingerprint"))
add("data fingerprint matches the files on disk", ok_fp, fp_detail)

entries = deck.get("deck", [])
raw_basics = deck.get("basics", {})
basics = {k: int(v) for k, v in raw_basics.items() if int(v)}
names = [c["name"] for c in entries]
nonbasic = [n for n in names if n not in BASICS]
total = sum(int(c.get("count", 1)) for c in entries) + sum(basics.values())

# ---------------- shape ----------------
add("card count == 99 (commander not counted)", total == 99, f"got {total}")
add("every entry count == 1", all(int(c.get("count", 1)) == 1 for c in entries),
    [c["name"] for c in entries if int(c.get("count", 1)) != 1])
dupes = sorted({n for n in names if names.count(n) > 1})
add("no repeated entries", not dupes, dupes)
add("basics dict holds only basic land names", set(basics) <= BASICS, sorted(set(basics) - BASICS))
add("basics not also in the deck list", not (set(names) & BASICS), sorted(set(names) & BASICS))
cmd = build.get("commander", deck.get("commander", ""))
in99 = [n for n in names if config.norm(n) == config.norm(cmd)]
add("commander is not also in the 99", not in99, in99)

# ---------------- membership ----------------
pool_by_norm = {config.norm(n): n for n in pool["name"]}
missing = sorted(n for n in nonbasic if n not in set(pool["name"]))
hints = [f"{n} -> did you mean {pool_by_norm[config.norm(n)]!r}?"
         for n in missing if config.norm(n) in pool_by_norm]
add("every non-basic is in pool.csv", not missing, f"missing: {missing} {hints}")
if missing:
    report()
    print("\nMEMBERSHIP FAILED -- remaining checks not run. Use the exact pool spelling.")
    sys.exit(1)

rows = pool[pool["name"].isin(nonbasic)].drop_duplicates("name")
lookup = rows.set_index("name")

mism = []
for c in entries:
    if c["name"] in BASICS:
        continue
    r = lookup.loc[c["name"]]
    for f in ("mana_cost", "type_line"):
        if f in c and blank(c[f]) != blank(r[f]):
            mism.append(f"{c['name']}.{f}")
add("declared cost/type (if given) match the pool", not mism, mism)

# ---------------- colour identity ----------------
cmd_ci = set(str(build.get("color_identity", "")).upper())
decl_ci = set(str(deck.get("color_identity", "")).upper()) - set(" ,")
add("declared colour identity == the commander's", decl_ci == cmd_ci,
    f"deck.json {''.join(sorted(decl_ci))!r} vs commander {''.join(sorted(cmd_ci))!r}")
bad_ci = [r["name"] for _, r in rows.iterrows()
          if not (set(blank(r["color_identity"]).upper()) - set(" ,")) <= cmd_ci]
add("every card inside the commander's colour identity", not bad_ci, bad_ci)
basic_colour = {"Plains": "W", "Island": "U", "Swamp": "B", "Mountain": "R", "Forest": "G"}
bad_basic = [b for b in basics if b in basic_colour and basic_colour[b] not in cmd_ci]
add("basics produce only the commander's colours", not bad_basic, bad_basic)

# ---------------- restriction + legality ----------------
bad_r = [f"{r['name']} :: {r['type_line']}" for _, r in rows.iterrows() if not prep.row_ok(spec, r)]
add(f"restriction '{rkey}' holds for every card", not bad_r, bad_r)
allow = spec.get("allow_types") or []
if basics and allow and "Land" not in allow and not spec.get("always_legal"):
    add(f"basics legal under '{rkey}'", False, "no land type is legal under this restriction")
illegal = rows.loc[rows["commander_legality"].astype(str).str.lower() != "legal", "name"].tolist()
add("Commander-legal (file column)", not illegal, illegal)

# ---------------- multi-face ----------------
multi = {r["name"]: str(r["type_line"]) for _, r in rows.iterrows() if "//" in r["name"]}
bad_mode = []
for c in entries:
    if c["name"] in multi:
        faces = [f.strip() for f in c["name"].split("//")]
        if c.get("mode_taken") not in faces:
            bad_mode.append(f"{c['name']}: mode_taken {c.get('mode_taken')!r} not in {faces}")
add("multi-face cards name the face they are played as", not bad_mode, bad_mode)

# ---------------- brief ----------------
brief = deck.get("brief", {})
need = ("how_it_wins", "the_line", "against", "pilot")
add("brief has all four sections", all(blank(brief.get(k)) for k in need),
    [k for k in need if not blank(brief.get(k))])
indeck = {config.norm(n) for n in names} | {config.norm(b) for b in BASICS} | {config.norm(cmd)}
unres = sorted({m for v in brief.values() for m in CARDREF.findall(str(v)) if config.norm(m) not in indeck})
add("every [[card]] in the brief is in the deck", not unres, unres)

report()

# ---------------- facts, not checks ----------------
def face_is_land(face):
    return "Land" in prep.face_types(face)


pure = sum(1 for _, r in rows.iterrows() if "//" not in r["name"] and face_is_land(r["type_line"]))
mdfc = [n for n in multi if any(face_is_land(f) for f in multi[n].split("//"))]
as_land = 0
for c in entries:
    if c["name"] in mdfc:
        faces = [f.strip() for f in c["name"].split("//")]
        ftl = [f.strip() for f in multi[c["name"]].split("//")]
        if c.get("mode_taken") in faces and face_is_land(ftl[faces.index(c["mode_taken"])]):
            as_land += 1
b = sum(basics.values())
print(f"\nLANDS  floor {pure + b}  declared {pure + b + as_land}  ceiling {pure + b + len(mdfc)}")
payload = "|".join(sorted(nonbasic)) + "||" + "|".join(f"{k}:{v}" for k, v in sorted(raw_basics.items()))
print("DECK CHECKSUM:", hashlib.sha256(payload.encode()).hexdigest()[:16])
sys.exit(0 if all(ok for _, ok, _ in results) else 1)
