"""validate_deck.py -- the verification of record for the finished 99.

Commander- and restriction-agnostic. The restriction is read from
restrictions.json via the key prep.py recorded in build_spec.json, and applied
with prep.row_ok -- the same predicate that filtered the pool -- so no edit to
this file is ever needed for a new commander or restriction. Do not modify the
checks; a failing check is fixed in deck.json.

Run:  python validate_deck.py             full pipeline checks
      python validate_deck.py --minimal   legality only: count, membership,
                                          declared data, colour identity,
                                          restriction, Commander legality,
                                          multi-face modes. Skips packages,
                                          refs, bench and cross-turn checks,
                                          for builds that do not produce them.
Exit: 0 all pass, 1 any fail.
"""
import hashlib
import json
import sys

import pandas as pd

import config
import scan

import prep

DECK = "deck.json"
FLEX_CAP = 8
MINIMAL = "--minimal" in sys.argv

# ---------- the restriction, from its single declaration ----------
try:
    BUILD = json.load(open("build_spec.json", encoding="utf-8"))
except FileNotFoundError:
    print("HALT: build_spec.json not found. Run prep.py first; it records which "
          "restriction this deck is checked against.")
    sys.exit(1)
RKEY = BUILD["restriction_key"]
_all = prep.load_restrictions()
if RKEY not in _all:
    print(f"HALT: restriction {RKEY!r} from build_spec.json is not in restrictions.json.")
    sys.exit(1)
SPEC = _all[RKEY]
ALWAYS_LEGAL = set(SPEC.get("always_legal", []))

config.check()
pool = config.load("POOL")
deck = json.load(open(DECK, encoding="utf-8"))

# ---------- v9 / 3.0: fingerprint before anything else ----------
_fp_ok, _fp_detail = config.fingerprint_matches(deck.get("data_fingerprint"))
if not _fp_ok:
    print(f"\n{'CHECK':<48} {'RESULT':<7} DETAIL")
    print(f"{'data fingerprint matches the files on disk':<48} {'FAIL':<7} {_fp_detail}")
    print("\nThe inputs moved under this artifact. Re-run the build turn. Do not edit "
          "deck.json to match.")
    sys.exit(1)

BASICS = {"Island", "Plains", "Swamp", "Mountain", "Forest", "Wastes"}

entries   = deck["deck"]
names     = [c["name"] for c in entries]
nameset   = set(names)
basics    = deck.get("basics", {})
budget    = deck.get("budget", {})
wrows     = deck.get("weakness_rows", {})
plines    = deck.get("play_lines", {})
bench     = deck.get("bench", [])
pnotes    = deck.get("package_notes", {})
total     = sum(c.get("count", 1) for c in entries) + sum(basics.values())
nonbasic  = [n for n in names if n not in BASICS]
rows      = pool[pool["name"].isin(nonbasic)]
poolnames = set(pool["name"])
results   = []


def add(label, ok, detail=""):
    results.append((label, ok, detail))


def report():
    print(f"\n{'CHECK':<48} {'RESULT':<7} DETAIL")
    for label, ok, detail in results:
        print(f"{label:<48} {'PASS' if ok else 'FAIL':<7} {'' if ok else detail}")


# ---------- structural ----------
add("card count == 99", total == 99, f"got {total}")
bad_count = [c["name"] for c in entries if c.get("count", 1) != 1]
add("every entry count == 1", not bad_count, f"count!=1: {bad_count}")
dupes = sorted({n for n in names if names.count(n) > 1})
add("no repeated entries", not dupes, f"repeats: {dupes}")
bad_basic_key = sorted(set(basics) - BASICS)
add("basics dict holds only basics", not bad_basic_key, f"illegal keys: {bad_basic_key}")
cmd_in_99 = [n for n in names if config.norm(n) == config.norm(BUILD.get("commander", ""))]
add("commander is not also in the 99", not cmd_in_99, f"{cmd_in_99}")
basic_in_list = sorted(nameset & BASICS)
add("basics not also in deck list", not basic_in_list, f"in both: {basic_in_list}")

# ---------- membership gate ----------
# Every check below inspects `rows`, which holds only cards that matched the pool.
# An unmatched name produces no row and would be silently exempt from all of them.
missing = sorted(n for n in nonbasic if n not in poolnames)
add("all names in pool", not missing, f"missing: {missing}")
if missing:
    report()
    print("\nMEMBERSHIP FAILED -- content checks below not run.")
    sys.exit(1)

# ---------- declared data must match the file ----------
def norm(v):
    return "" if (v is None or (isinstance(v, float) and pd.isna(v))) else str(v).strip()


lookup = pool.set_index("name")
mismatch = []
for c in entries:
    r = lookup.loc[c["name"]]
    if isinstance(r, pd.DataFrame):
        r = r.iloc[0]
    for f in ("mana_cost", "type_line"):
        if f in c and norm(c[f]) != norm(r[f]):
            mismatch.append(f"{c['name']}.{f}: declared {norm(c[f])!r} vs pool {norm(r[f])!r}")
add("declared cost/type match pool", not mismatch, f"{mismatch}")

# ---------- colour identity ----------
# No default: a missing declaration must fail loudly, not silently pass under an
# assumed identity carried over from a previous build.
ci_declared = deck.get("color_identity")
add("deck declares its colour identity", bool(ci_declared),
    "deck.json has no color_identity field -- cannot check without it")
ci = rows["color_identity"].fillna("")
allowed = set(str(ci_declared or "").upper()) | set(" ,")
bad_ci = rows.loc[~ci.apply(lambda s: set(str(s).upper()) <= allowed), "name"].tolist()
add("colour identity within commander's", not bad_ci, f"violations: {bad_ci}")
spec_ci = str(BUILD.get("color_identity", ""))
_bcol = {"Plains": "W", "Island": "U", "Swamp": "B", "Mountain": "R", "Forest": "G"}
_offb = [k for k, v in basics.items() if v and k in _bcol and _bcol[k] not in spec_ci.upper()]
add("basics produce only the commander's colours", not _offb, f"{_offb}")
add("declared identity matches the commander's",
    set(str(ci_declared or "").upper()) - set(" ,") == set(spec_ci.upper()),
    f"deck.json {ci_declared!r} vs build_spec.json {spec_ci!r}")

# ---------- restriction, every face and every declared axis ----------
face_types = prep.face_types
bad_restr = [f"{r['name']} :: {r['type_line']}" for _, r in rows.iterrows()
             if not prep.row_ok(SPEC, r)]
add(f"restriction '{RKEY}' holds for every card", not bad_restr, f"violations: {bad_restr}")
if (SPEC.get("allow_types") and "Land" not in SPEC["allow_types"]
        and not ALWAYS_LEGAL and sum(basics.values())):
    add(f"basics legal under '{RKEY}'", False,
        f"{sum(basics.values())} basics but no land type is legal")

# ---------- legality (the file's commander_legality column is the ban list) ----------
illegal = rows[rows["commander_legality"] != "legal"]["name"].tolist()
add("commander_legality", not illegal, f"illegal: {illegal}")

# ---------- multi-face: one card, one mode ----------
multi = {r["name"]: str(r["type_line"]) for _, r in
         pool[pool["name"].str.contains("//", regex=False)].iterrows()}
missing_mode, bad_mode = [], []
for c in entries:
    if c["name"] in multi:
        faces = [f.strip() for f in c["name"].split("//")]
        mt = c.get("mode_taken")
        if not mt:
            missing_mode.append(c["name"])
        elif mt not in faces:
            bad_mode.append(f"{c['name']}: mode_taken {mt!r} not in {faces}")
add("multi-face cards declare mode_taken", not missing_mode, f"missing: {missing_mode}")
add("mode_taken names a real face", not bad_mode, f"{bad_mode}")

if not MINIMAL:
    # ---------- budget ----------
    pkg_of = {c["name"]: c.get("package") for c in entries}
    unknown_pkg = sorted({p for p in pkg_of.values() if p not in budget})
    add("every card sits in a declared package", not unknown_pkg, f"unknown: {unknown_pkg}")

    counts = {}
    for p in pkg_of.values():
        counts[p] = counts.get(p, 0) + 1
    deltas = [f"{p}: target {budget[p]['target']} actual {counts.get(p, 0)}"
              for p in budget if counts.get(p, 0) != budget[p]["target"]]
    add("package counts match budget", not deltas, f"{deltas}")

    budget_total = sum(b["target"] for b in budget.values()) + sum(basics.values())
    add("budget total + basics == 99", budget_total == 99, f"got {budget_total}")

    nocrit = [p for p, b in budget.items() if not str(b.get("criterion", "")).strip()]
    add("every package states a criterion", not nocrit, f"missing: {nocrit}")
    nonote = [p for p in budget if not str(pnotes.get(p, "")).strip()]
    add("every package has a written note", not nonote, f"missing: {nonote}")

    flex_total = sum(b["target"] for b in budget.values() if b.get("flex"))
    add(f"flex packages <= {FLEX_CAP} slots", flex_total <= FLEX_CAP, f"flex slots: {flex_total}")

    bad_sec = sorted({r for c in entries for r in c.get("roles_secondary", []) if r not in budget})
    add("secondary roles use package names", not bad_sec, f"unknown: {bad_sec}")
    self_sec = [c["name"] for c in entries if c.get("package") in c.get("roles_secondary", [])]
    add("secondary role != primary package", not self_sec, f"{self_sec}")

    # ---------- refs ----------
    refkeys = set(wrows) | set(plines)
    noref = [c["name"] for c in entries if not c.get("refs")]
    badref = sorted({r for c in entries for r in c.get("refs", []) if r not in refkeys})
    add("every card carries >=1 ref", not noref, f"no refs: {noref}")
    add("every ref resolves", not badref, f"dangling: {badref}")

    # ---------- comparative selection ----------
    bad_beat = [f"{c['name']} beat {c['beat']!r}" for c in entries
                if c.get("beat") and (c["beat"] not in poolnames or c["beat"] in nameset)]
    add("beat names a real, excluded card", not bad_beat, f"{bad_beat}")

    notes = [str(c.get("note", "")).strip().lower() for c in entries]
    notes = [n for n in notes if n]
    reused = sorted({n for n in notes if notes.count(n) > 1})
    add("no card note reused verbatim", not reused, f"reused: {reused}")

    # ---------- bench ----------
    bad_bench = []
    for b in bench:
        if b["name"] not in poolnames:
            bad_bench.append(f"{b['name']}: not in pool")
        elif b["name"] in nameset:
            bad_bench.append(f"{b['name']}: also in deck")
        elif b.get("package") not in budget:
            bad_bench.append(f"{b['name']}: bad package")
        elif b.get("lost_to") not in nameset:
            bad_bench.append(f"{b['name']}: lost_to not in deck")
    add("bench entries valid", not bad_bench, f"{bad_bench}")
    thin = sorted({p for p in budget if sum(1 for b in bench if b.get("package") == p) == 0})
    add("every package benched >=1 loser", not thin, f"no bench: {thin}")

    bad_weak = sorted(set(deck.get("weak_slots", [])) - nameset)
    add("weak_slots are deck cards", not bad_weak, f"not in deck: {bad_weak}")

    # ---------- cross-artifact: Turn 1 IDs must survive into Turn 3 ----------
    try:
        S = json.load(open("strategy.json", encoding="utf-8"))
        drift = sorted(set(S.get("weaknesses", {})) - set(wrows))
        add("no weakness silently dropped since Turn 1", not drift, f"missing: {drift}")

        # v9 / 3.9: a card Turn 1 named as an ANSWER is a commitment Turn 2 disposes of.
        asserted = set()
        for _w in S.get("weakness_answers", {}).values():
            asserted |= set(_w.get("cards", []))
        for _l in S.get("kill_chain", []):
            asserted |= set(_l.get("cards", []))
        try:
            C = json.load(open("candidates.json", encoding="utf-8"))
            disposed = {config.norm(e["name"]) for e in C.get("carried_from_strategy", [])}
            undecided = sorted(n for n in asserted if config.norm(n) not in disposed)
            add("every card named as an answer in Turn 1 reached a verdict in Turn 2",
                not undecided,
                f"{len(undecided)} with no shortlisted/benched/dropped entry: {undecided[:8]}")
        except FileNotFoundError:
            add("candidates.json readable", False, "candidates artifact absent (use --minimal for builds that do not produce one)")
    except FileNotFoundError:
        add("strategy.json readable", False, "plan artifact absent (use --minimal for builds that do not produce one)")

    # ---------- v9: the same scans that run on strategy.json run here ----------
    # budget[].criterion, package_notes, deck[].note and bench[].reason are authored
    # prose and went unscanned in v8, where thirteen unregistered absolutes accrued.
    _otext = dict(zip(pool["name"], pool["oracle_text"].fillna("").astype(str)))
    for _label, _items in scan.scan(deck, "deck",
                                    pool_names=poolnames, oracle_text=_otext).items():
        add(_label, not _items, f"{_items[:5]}")


if MINIMAL:
    _refs = [m for v in deck.get("brief", {}).values() for m in scan.CARDREF.findall(str(v))]
    _nin = sorted({m for m in _refs if config.norm(m) not in
                   {config.norm(n) for n in nameset} | {config.norm(b) for b in BASICS}})
    add("[[card]] references in brief are deck cards", not _nin, f"{_nin}")

report()

# ---------- adjudication notice, not a check ----------
def land_plus_other(type_line):
    for f in [x.strip() for x in str(type_line).split("//")]:
        t = face_types(f)
        if (t & ALWAYS_LEGAL) and (t - ALWAYS_LEGAL):
            return True
    return False


hybrids = rows.loc[rows["type_line"].apply(land_plus_other), ["name", "type_line"]]
if ALWAYS_LEGAL and len(hybrids):
    print(f"\nADJUDICATION NOTICE -- legal only because a face carries "
          f"{sorted(ALWAYS_LEGAL)} alongside another type. Confirm each is intended.")
    for _, r in hybrids.iterrows():
        print(f"  {r['name']} :: {r['type_line']}")

nobeat = [c["name"] for c in entries if not c.get("beat")]
if nobeat and not MINIMAL:
    print(f"\nUNCONTESTED SLOTS ({len(nobeat)}) -- nothing in the pool competed for these.")
    for n in nobeat:
        print(f"  {n}")

# ---------- land census: a range, not a number ----------
def mode_is_land(cardname, mode):
    fn = [f.strip() for f in cardname.split("//")]
    ft = [f.strip() for f in multi[cardname].split("//")]
    return "Land" in face_types(ft[fn.index(mode)])


pure    = int(((rows["is_land"]) & (rows["mdfc_land_back"] != True)).sum())
mdfc_n  = int((rows["mdfc_land_back"] == True).sum())
b       = sum(basics.values())
as_land = sum(1 for c in entries if c["name"] in multi
              and c.get("mode_taken") and mode_is_land(c["name"], c["mode_taken"]))
print("\nLAND CENSUS -- argue the mana base against the FLOOR, never the ceiling.")
print(f"  floor   {pure + b:>3}  (every multi-face cast as a spell)")
print(f"  declared{pure + b + as_land:>3}  (played per mode_taken)")
print(f"  ceiling {pure + b + mdfc_n:>3}  (every multi-face played as a land)")

gc = rows[rows["game_changer"] == True]["name"].tolist()
print(f"\nspells: {99 - (pure + b + mdfc_n)} to {99 - (pure + b)}")
print(f"high-impact cards ({len(gc)}): {gc}")
print("curve (non-land):", rows[~rows["is_land"]].groupby("cmc").size().to_dict())
if not MINIMAL:
    print("\nDEDICATED vs FUNCTIONAL count per package:")
    for p in sorted(budget):
        ded = counts.get(p, 0)
        fun = ded + sum(1 for c in entries if p in c.get("roles_secondary", []))
        print(f"  {p:<28} dedicated {ded:>2}   functional {fun:>2}")
    print("\nweak slots:", deck.get("weak_slots", []))

payload = "|".join(sorted(nonbasic)) + "||" + "|".join(f"{k}:{v}" for k, v in sorted(basics.items()))
print("DECK CHECKSUM:", hashlib.sha256(payload.encode()).hexdigest()[:16])

sys.exit(0 if all(r[1] for r in results) else 1)
