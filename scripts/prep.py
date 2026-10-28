"""prep.py -- one command between the intake answers and Turn 1.

Supersedes a bare `build_pool.py` run. Does four things the build would
otherwise spend model tokens on, and does them the same way every time:

  1. POOL      collection -> Commander-legal -> inside the commander's colour
               identity -> every face satisfies THE RESTRICTION. Restrictions
               are declared in restrictions.json, so a new one is a data edit,
               not a code edit, and the same declaration is re-checked against
               the finished 99 by check_restriction.py.
  2. ENRICH    joins edhrec_rank and usd from UNIVERSE onto the pool by
               NORMALISED name (3.7.6). The collection files carry neither, so
               without this step nothing in the pool encodes card quality and
               the model must rank a thousand rows from recall.
  3. TAG       deterministic function tags from oracle text and type line.
               Regex is not judgement; it is a candidate filter whose verdict
               is still the oracle text (3.7.1). Written to pool_tagged.csv.
  4. REPORT    the derivation, the commander's own card data from the file,
               function coverage counts, hybrid-type and multi-face notices,
               high-impact cards, and the colour-source count read from ORACLE
               TEXT rather than produced_mana.

Run:
    python prep.py --commander "<exact card name>" --restriction <key in restrictions.json>

Writes pool.csv, pool_tagged.csv, build_spec.json. Paste stdout into the build.
"""
import argparse
import json
import os
import re
import sys

import pandas as pd

import config

PERMANENT_TYPES = {"Artifact", "Creature", "Enchantment", "Planeswalker", "Battle"}
SUPERTYPES = {"Legendary", "Basic", "Snow", "World", "Ongoing", "Elite", "Host", "Token"}
# Kindred (formerly Tribal) is a card type that only carries subtypes onto another
# type. A "Kindred Instant" is an instant: ignoring it keeps it from failing an
# allow-list like ["Instant", "Sorcery", "Land"]. Subtype rules still see its subtypes.
SUPERTYPES |= {"Kindred", "Tribal"}
BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}

RESTRICTIONS_FILE = "restrictions.json"


# --------------------------------------------------------------------------
# face-level type test
# --------------------------------------------------------------------------
def face_types(face):
    head = str(face).split("\u2014")[0]
    return {w for w in re.split(r"\s+", head.strip()) if w and w not in SUPERTYPES}


def face_subtypes(face):
    parts = str(face).split("\u2014")
    if len(parts) < 2:
        return set()
    return {w for w in re.split(r"\s+", parts[1].strip()) if w}


def _spec_face_ok(spec, face):
    t = face_types(face)
    if not t:
        return False
    if spec.get("always_legal") and t & set(spec["always_legal"]):
        return True
    forbid = set(spec.get("forbid_types", []))
    if forbid and (t & forbid):
        return False
    allow = set(spec.get("allow_types", []))
    if allow and not (t <= allow):
        return False
    return True



# --- token-subtype axis -----------------------------------------------------
# A clause that creates a CREATURE token under your control must name the
# required subtype. Clauses whose tokens go to someone else are exempt, which is
# why the controller test comes first and is checked per clause, not per card.
_CLAUSE = re.compile(r"[.;]|(?<=\))\s")
_NOT_YOURS = re.compile(
    r"\b(each|target|an|that|the chosen)\s+(opponent|other player)\b|"
    r"\btarget player (creates|puts)\b|\bthat player creates\b|"
    # "its controller creates ..." can resolve to an opponent whenever you aim the
    # spell at an opponent's permanent, which is the only way you would aim it.
    r"\bits controller creates\b|\bthat permanent's controller creates\b|"
    r"\bits owner creates\b", re.I)
_CREATES = re.compile(r"\bcreates?\b", re.I)
_CRE_TOKEN = re.compile(r"creature tokens?", re.I)
_COPY = re.compile(r"token that's a copy|tokens that are copies", re.I)


def token_clauses(row):
    """(clause, verdict) for every clause that creates a creature token you keep.

    verdict: 'check' | 'copy' | 'foreign'
    """
    txt = str(row.get("oracle_text") or "").replace(" | ", ". ")
    out = []
    for cl in _CLAUSE.split(txt):
        if not cl or not _CREATES.search(cl):
            continue
        if not (_CRE_TOKEN.search(cl) or _COPY.search(cl)):
            continue
        if _NOT_YOURS.search(cl):
            out.append((cl.strip(), "foreign"))
        elif _COPY.search(cl) and not _CRE_TOKEN.search(cl):
            out.append((cl.strip(), "copy"))
        else:
            out.append((cl.strip(), "check"))
    return out


def token_subtype_ok(sub, row):
    bad = []
    for cl, verdict in token_clauses(row):
        if verdict == "foreign":
            continue
        if verdict == "copy":
            continue
        if not re.search(rf"\b{re.escape(sub)}\b", cl, re.I):
            bad.append(cl)
    return (not bad), bad


def row_ok(spec, row):
    """Every face must satisfy the type test; then any row-level predicates."""
    if not all(_spec_face_ok(spec, f) for f in str(row["type_line"]).split("//")):
        return False
    # exempt_types: a card carrying one of these on any face skips the row-level
    # predicates (a land is not priced or curved like a spell).
    ex = set(spec.get("exempt_types", []))
    if ex:
        faces = [face_types(f) for f in str(row["type_line"]).split("//")]
        if any(t & ex for t in faces):
            return True
    if spec.get("max_usd") is not None:
        v = row.get("usd")
        if v is None or (isinstance(v, float) and pd.isna(v)) or float(v) > spec["max_usd"]:
            return False
    if spec.get("max_cmc") is not None and float(row.get("cmc") or 0) > spec["max_cmc"]:
        return False
    if spec.get("min_cmc") is not None and float(row.get("cmc") or 0) < spec["min_cmc"]:
        return False
    # require_subtype_for_type: {"Creature": ["Cat"]} -- every FACE carrying that
    # card type must list at least one of those subtypes on its printed type line.
    # Subtypes are compared as whole tokens, so "Cathar" never satisfies "Cat".
    req = spec.get("require_subtype_for_type") or {}
    if req:
        for face in str(row["type_line"]).split("//"):
            ft, fs = face_types(face), face_subtypes(face)
            for ctype, subs in req.items():
                if ctype in ft and not (fs & set(subs)):
                    return False
    sub = spec.get("token_creature_subtype")
    if sub and not token_subtype_ok(sub, row)[0]:
        return False
    txt = str(row.get("oracle_text") or "")
    for pat in spec.get("forbid_text", []):
        if re.search(pat, txt, re.I):
            return False
    for pat in spec.get("require_text", []):
        if not re.search(pat, txt, re.I):
            return False
    return True


def load_restrictions():
    path = config.resolve(RESTRICTIONS_FILE)
    if not path:
        print(f"HALT: {RESTRICTIONS_FILE} not found. It declares every restriction "
              f"this project supports and is required.")
        sys.exit(1)
    return json.load(open(path, encoding="utf-8"))


# --------------------------------------------------------------------------
# function tags -- candidate filters, never verdicts (3.7.1, 3.7.3)
# Patterns describe OUTCOMES, not the noun a function usually goes by (3.7.3).
# --------------------------------------------------------------------------
# Grouped by what a deck uses them for, so no archetype is the default. Order is
# the order digest.py prints. Every tag is a CANDIDATE FILTER: the oracle text
# decides. Type-line tags (mana_creature, mana_rock, equipment_aura) read the
# type line as well as the text.
TAGS = {
    # --- mana ---
    "mana_land_drop":   r"put (a|that|target|up to \w+) (basic )?lands? (card )?(from[^.]*)?onto the battlefield|search your library for (a|up to \w+) [^.]*land[^.]*onto the battlefield|you may play an additional land",
    "mana_burst":       r"\badd \{|\badd (one|two|three|four|five|x|that much) mana|\badd an amount of|mana of any (one )?colou?r",
    "treasure":         r"\btreasure tokens?\b|\bpowerstone\b|\bgold token\b",
    "mana_untap":       r"untap target (land|permanent|artifact|creature)|untap (all|each|up to \w+) (lands|permanents|creatures)",
    "cost_reduction":   r"costs? \{\d+\} less|costs? \{\w\} less|cost \{\d+\} less",
    # --- cards ---
    "draw":             r"draws? (a card|\w+ cards|cards equal|that many cards)",
    "selection":        r"\bscry \d|\bsurveil \d|look at the top \w+ cards|exile the top \w+ cards?[^.]*you may (play|cast)|\bexplores?\b|\bconnive",
    "tutor":            r"search your library for",
    "recursion":        r"return [^.]*from your graveyard|cast [^.]*from your graveyard|\bunearth\b|\bescape\b|\bembalm\b|\beternalize\b",
    "buyback_flashback": r"\bbuyback\b|\bflashback\b|\bretrace\b|\brebound\b|\breplicate\b|\bstorm\b|\bjump-start\b",
    # --- interaction ---
    "counter":          r"counter target",
    "removal_spot":     r"(destroy|exile) target (?!land\b)|deals? (\d+|x|that much) damage to (target|any target|another target)|target (creature|permanent|planeswalker)[^.]*(gets? -|sacrifices?)|return target (creature|permanent|nonland permanent|artifact|enchantment) to its owner|fights? (target|another target|up to one target)",
    "removal_land":     r"(destroy|exile) target (nonbasic )?land|target land[^.]*(destroy|sacrifice)",
    "wipe":             r"(destroy|exile) (all|each)|(all|each) (creatures?|other creatures?) gets? -|each player sacrifices|return (all|each) (nonland permanents|creatures)",
    "protection":       r"hexproof|indestructible|shroud|protection from|phases? out|can't be (countered|targeted)|counter target spell that targets|\bward\b",
    "graveyard_hate":   r"exile (target player's graveyard|all cards from|all graveyards|each opponent's graveyard|target card from a graveyard|up to \w+ target cards? from)",
    "tax_stax":         r"costs? \{\d+\} more|players? can't|spells cost|don't untap|can't (attack|block|cast)",
    # --- board and bodies ---
    "makes_permanent":  r"\bcreates? (a|an|\w+|x|that many) [^.]*token|put (a|\w+) [^.]*onto the battlefield under your control",
    "token_doubler":    r"twice that many|that many plus|create (one|two) additional|an additional [^.]*token|tokens? that's a copy",
    "anthem":           r"(creatures|other creatures|[a-z]+s) you control get \+|creatures you control have|get \+\d+/\+\d+ (for each|until end of turn for each)",
    "keyword_grant":    r"(creatures|other creatures|[a-z]+s) you control (gain|have|get [^.]*and gain) [^.]*(haste|flying|trample|menace|double strike|first strike|vigilance|lifelink|can't be blocked)|target creature (gains|gets [^.]*and gains) [^.]*(haste|flying|trample|menace|can't be blocked)",
    "counters_plus":    r"\+1/\+1 counters?|\bproliferate\b",
    "sac_outlet":       r"sacrifice (a|another|an|x|any number of) (creature|permanent|artifact|token|land)[^:]*:",
    "etb_trigger":      r"when(ever)? [^.]*enters|\bblink\b|exile (target|another target|up to one target) [^.]*(creature|permanent)[^.]*(you control|you own)[^.]*return",
    "death_trigger":    r"whenever [^.]*(dies|is put into a graveyard from the battlefield)",
    "attack_trigger":   r"whenever [^.]*attacks|whenever [^.]*deals combat damage",
    "cast_trigger":     r"whenever you cast",
    "landfall":         r"\blandfall\b|whenever a land [^.]*enters",
    "equipment_aura":   r"\bequip\b|\benchant creature\b|\breconfigure\b",
    "lifegain":         r"gain \d+ life|gains? (x|that much) life|\blifelink\b|whenever you gain life",
    "mill":             r"\bmills?\b|put the top \w+ cards of [^.]*graveyard",
    # --- closing ---
    "damage_reach":     r"damage to each opponent|damage to target player|damage to any target|each opponent loses \d+ life|target player loses \d+ life|loses life equal",
    "extra_turn":       r"take an extra turn",
    "extra_combat":     r"additional combat phase",
    "alt_win":          r"wins? the game|loses? the game",
    "copy":             r"copy target|copy that spell|copies? of (target|that)",
}
TAG_ORDER = list(TAGS) + ["mana_creature", "mana_rock", "typal_payoff"]

# Typal payoffs need case: "Cats you control" is a payoff, "creatures you control"
# is an anthem. Compiled without re.I; the generic plurals are excluded.
_GENERIC_PLURALS = {"Creatures", "Artifacts", "Lands", "Permanents", "Tokens",
                    "Enchantments", "Planeswalkers", "Spells", "Cards", "Others",
                    "Nontoken", "Attacking", "Blocking", "Players", "Opponents",
                    "Plains", "Islands", "Swamps", "Mountains", "Forests", "Auras",
                    "Equipment", "Vehicles", "Treasures", "Clues", "Foods", "Sagas",
                    "White", "Blue", "Black", "Red", "Green", "Colorless", "Multicolored",
                    "Legendary", "Nonland", "Noncreature", "Instant", "Sorcery", "Historic",
                    "Snow", "Basic", "Artifact", "Enchantment", "Land", "Creature", "Token"}
_TYPAL = re.compile(r"\b(?:[Oo]ther )?([A-Z][a-z]+s|[A-Z][a-z]+ creatures|[A-Z][a-z]+ spells|[A-Z][a-z]+ cards)\b (?:you control|you cast|in your)|\bchosen (?:creature )?type\b|\bshare a creature type\b|\bof the chosen type\b")

COLOUR_SOURCE = {c: re.compile(r"add[^.]*\{" + c + r"\}", re.I) for c in "WUBRGC"}
# "Add one mana of any color" (Command Tower, City of Brass, fetch-alikes read by
# text) produces every colour; the {X}-pip patterns above cannot see it.
ANY_COLOUR = re.compile(r"mana of any (one )?colou?r|mana in any combination of colou?rs", re.I)


def tag_row(row):
    txt = str(row.get("oracle_text") or "")
    tl = str(row.get("type_line") or "")
    front = face_types(tl.split("//")[0])
    tags = [k for k, p in TAGS.items() if re.search(p, txt, re.I)]
    makes_mana = bool(re.search(TAGS["mana_burst"], txt, re.I))
    if "Land" in front:
        tags.append("land")
    elif "Creature" in front and (makes_mana or "treasure" in tags):
        tags.append("mana_creature")
    elif "Artifact" in front and makes_mana:
        tags.append("mana_rock")
    for m in _TYPAL.finditer(txt):
        g = m.group(1)
        if g is None or g.split()[0] not in _GENERIC_PLURALS:
            tags.append("typal_payoff")
            break
    if "Land" in front and "mana_burst" in tags:
        tags.remove("mana_burst")      # a land adding mana is the land tag, not ramp
    return ";".join(sorted(set(tags)))


def colour_sources(row):
    txt = str(row.get("oracle_text") or "")
    if ANY_COLOUR.search(txt):
        return "WUBRG"
    return "".join(c for c, p in COLOUR_SOURCE.items() if p.search(txt))


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commander", required=True)
    ap.add_argument("--restriction", required=True)
    ap.add_argument("--out", default="pool.csv")
    a = ap.parse_args()

    # POOL is this script's OUTPUT, not its input: on a first build for a new
    # commander there is no pool.csv yet. Requiring it here made prep.py
    # unrunnable except after a previous build had left one behind.
    config.REQUIRED = tuple(k for k in config.REQUIRED if k != "POOL")
    config.check()
    specs = load_restrictions()
    if a.restriction not in specs:
        print(f"HALT: restriction {a.restriction!r} is not declared in "
              f"{RESTRICTIONS_FILE}. Declared: {sorted(specs)}")
        print("Add it there (and nowhere else) before building. A restriction the "
              "pool filters on but the finished-deck check does not know about is "
              "a deck filtered by one rule and checked against another.")
        sys.exit(1)
    spec = specs[a.restriction]

    parent = config.load("PARENT")
    universe = config.load("UNIVERSE")
    universe.columns = [c.lstrip("\ufeff") for c in universe.columns]

    # ---- the commander's own card, from the file, never from memory (P6) ----
    crow = config.find(universe, a.commander)
    if not len(crow):
        print(f"\nHALT: commander {a.commander!r} not in UNIVERSE (compared normalised).")
        sys.exit(1)
    c = crow.iloc[0]
    cci = c["color_identity"]
    cci = "" if cci is None or (isinstance(cci, float) and pd.isna(cci)) else str(cci)
    commander_ci = set(cci.upper())

    print("\n=== COMMANDER (from UNIVERSE, not from memory) ===")
    print(f"{c['name']}  {c['mana_cost']}  {c['type_line']}")
    print(f"colour identity: {''.join(sorted(commander_ci)) or '<colourless>'}   "
          f"cmc {c['cmc']}   edhrec_rank {c['edhrec_rank']}")
    print("oracle_text:")
    print(str(c["oracle_text"]))

    # ---- three filters ----
    df = parent.copy()
    n0 = len(df)
    legal = df["commander_legality"].fillna("").astype(str).str.lower() == "legal"
    df1 = df[legal]

    def ident_ok(x):
        s = "" if x is None or (isinstance(x, float) and pd.isna(x)) else str(x)
        return set(s.upper()) <= commander_ci

    df2 = df1[df1["color_identity"].map(ident_ok)].copy()

    # enrichment happens BEFORE the restriction filter, because a price or a
    # mana-value predicate needs the enriched column to filter on.
    u = universe[["name", "edhrec_rank", "usd"]].copy()
    u["_k"] = u["name"].map(config.norm)
    u = u.drop_duplicates("_k").set_index("_k")
    df2["_k"] = df2["name"].map(config.norm)
    df2["edhrec_rank"] = df2["_k"].map(u["edhrec_rank"])
    df2["usd"] = df2["_k"].map(u["usd"])
    df3 = df2[df2.apply(lambda r: row_ok(spec, r), axis=1)]
    # the commander is never one of the 99, so it is never a candidate for them
    n_cmd = int((df3["name"].map(config.norm) == config.norm(c["name"])).sum())
    df3 = df3[df3["name"].map(config.norm) != config.norm(c["name"])]

    print(f"\n=== DERIVATION ({a.restriction}) ===")
    print(f"  {spec.get('statement','(no statement declared)')}")
    print(f"  collection rows                      {n0:>6}")
    print(f"  - not Commander-legal                {n0-len(df1):>6}   -> {len(df1)}")
    print(f"  - outside the commander's identity   {len(df1)-len(df2):>6}   -> {len(df2)}")
    print(f"  - fails THE RESTRICTION              {len(df2)-len(df3):>6}   -> {len(df3)}")
    print(f"  - the commander itself               {n_cmd:>6}   -> {len(df3)}")
    print(f"  POOL                                 {len(df3):>6}")

    # ---- enrichment report (the join itself ran before the filter) ----
    pool = df3.copy()
    unmatched = pool.loc[pool["edhrec_rank"].isna() & pool["usd"].isna(), "name"].tolist()
    pool = pool.drop(columns=["_k"])
    print(f"\n=== ENRICHMENT ===")
    print(f"  edhrec_rank present on {int(pool['edhrec_rank'].notna().sum())}/{len(pool)} rows")
    print(f"  no universe match (rank and price both absent): {len(unmatched)}")
    for n in unmatched[:15]:
        print(f"    {n}")
    if len(unmatched) > 15:
        print(f"    ... and {len(unmatched)-15} more")
    print("  edhrec_rank is a POPULARITY prior, not a power ranking, and it is "
          "commander-agnostic. Use it as the ordering key inside a function, "
          "never as the reason a card is in the deck.")

    # ---- tag ----
    pool["tags"] = pool.apply(tag_row, axis=1)
    pool["colour_sources_text"] = pool.apply(colour_sources, axis=1)
    pool.to_csv(a.out, index=False, encoding="utf-8")
    pool.to_csv("pool_tagged.csv", index=False, encoding="utf-8")

    print(f"\n=== FUNCTION COVERAGE (tag = candidate filter, oracle text = verdict) ===")
    allt = TAG_ORDER + ["land"]
    for t in allt:
        hits = pool[pool["tags"].str.contains(rf"(?:^|;){re.escape(t)}(?:;|$)", na=False)]
        flag = "  ** UNDER-SUPPLIED" if len(hits) <= 3 else ""
        print(f"  {t:<20} {len(hits):>4}{flag}")

    # ---- card types, counted from the type line (not boolean flags) ----
    print(f"\n=== CARD TYPES (a card with two types counts under both) ===")
    for ty in ["Creature", "Artifact", "Enchantment", "Planeswalker", "Battle",
               "Instant", "Sorcery", "Land"]:
        n = int(pool["type_line"].fillna("").map(
            lambda s: any(ty in face_types(f) for f in s.split("//"))).sum())
        print(f"  {ty:<14} {n:>5}")

    # ---- notices the census would otherwise have to be read for ----
    tl = pool["type_line"].fillna("").astype(str)
    PERM = ["Artifact", "Creature", "Enchantment", "Planeswalker", "Battle", "Land"]

    def types_in(s):
        head = s.split("//")[0].split("\u2014")[0]
        return [p for p in PERM if p in head]

    hybrid = pool[tl.apply(lambda s: len(types_in(s)) > 1)]
    print(f"\n=== HYBRID TYPE NOTICE: {len(hybrid)} card(s) carry two permanent types on one face ===")
    for _, r in hybrid.iterrows():
        print(f"  {r['name']:<30} {r['type_line']}")
    if len(hybrid):
        print("  Each carries every listed type in every zone: removal, tutors, "
              "sacrifice costs and payoffs aimed at ANY of its types apply to it.")

    mp = pool[pool["name"].str.contains("//", regex=False, na=False)]
    print(f"\n=== MULTI-PART NAMES: {len(mp)} (one card, one slot, P5) ===")
    for _, r in mp.iterrows():
        print(f"  {r['name']:<46} {r['type_line']}")

    gc = pool[pool["game_changer"].astype(bool)] if "game_changer" in pool.columns else pool.iloc[0:0]
    print(f"\n=== HIGH-IMPACT (game_changer): {len(gc)} ===")
    for _, r in gc.iterrows():
        print(f"  {r['name']:<30} {r['mana_cost']}  {r['type_line']}")

    print(f"\n=== COLOUR SOURCES, read from ORACLE TEXT not produced_mana (3.7.1) ===")
    lands = pool[pool["tags"].str.contains(r"(?:^|;)land(?:;|$)", na=False)]
    for col in sorted(commander_ci) or ["C"]:
        n = int(lands["colour_sources_text"].fillna("").str.contains(col).sum())
        print(f"  {col}: {n} land(s) in pool whose text adds {{{col}}}")

    raw = pool["name"].fillna("").astype(str)
    differs = sorted(pool.loc[raw.map(lambda n: config.norm(n) != n.lower()), "name"])
    print(f"\n=== NORMALISATION NOTICE: {len(differs)} name(s) fail a naive lowercase compare ===")
    for n in differs:
        print(f"  {n}  ->  {config.norm(n)}")

    fp = config.fingerprint()
    spec_out = {
        "commander": c["name"],
        "commander_mana_cost": c["mana_cost"],
        "commander_type_line": c["type_line"],
        "commander_oracle_text": str(c["oracle_text"]),
        "color_identity": "".join(sorted(commander_ci)),
        "restriction_key": a.restriction,
        "restriction": spec,
        "pool_rows": int(len(pool)),
        "hybrid_type_cards": sorted(hybrid["name"].tolist()),
        "multi_part_cards": sorted(mp["name"].tolist()),
        "high_impact_cards": sorted(gc["name"].tolist()),
        "nonascii_names": differs,
        "data_fingerprint": fp,
    }
    json.dump(spec_out, open("build_spec.json", "w", encoding="utf-8"), indent=1)
    print(f"\nDATA FINGERPRINT  " + "  ".join(f"{k}={v}" for k, v in fp.items()))
    print(f"\nwrote {a.out}, pool_tagged.csv, build_spec.json")


if __name__ == "__main__":
    main()
