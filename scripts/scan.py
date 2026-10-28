"""scan.py -- one scanner, every artifact.

Originally extracted from validate_strategy.py, which ran these checks on
strategy.json only. Three consecutive versions have shipped a bug of the same shape: a scan
that runs on one authored surface and not on the identical surface one field
away. v7 scanned rows[].claim and missed strategy.md. v8 fixed that and missed
deck.json's package_notes, deck[].note and bench[].reason. Patching surface by
surface is what produced the pattern; this file is the alternative.

Both validators import from here. Nothing below reads a file or knows which
artifact it is looking at, so adding an artifact costs an entry in ARTIFACTS
rather than a copy of the scanning code.

CLI:  python scan.py <path.json|path.md>     -- scan one file, exit 1 on violations
"""
import json
import os
import re
import sys
import unicodedata

# ---------------------------------------------------------------- vocabularies
ABSOLUTE = re.compile(
    r"(?<![\w-])(unconditionally|always|never|every|all|none|nothing|no\s+card|zero)(?![\w-])",
    re.I)
PRONOUN = re.compile(r"its controller|that player|target player|their library|they do", re.I)
DEADWORD = re.compile(r"\b(dead|absent)\b", re.I)
CARDREF = re.compile(r"\[\[([^\]]+)\]\]")
NONE_FOUND = re.compile(r"none found|found none", re.I)
SENT = re.compile(r"(?<=[.!?])\s+")
LABELS = ("MECHANICALLY DEAD", "OFF-PLAN", "CATEGORY ABSENT")
BASICS = {"plains", "island", "swamp", "mountain", "forest", "wastes",
          "snow-covered plains", "snow-covered island", "snow-covered swamp",
          "snow-covered mountain", "snow-covered forest"}


def norm(s):
    """NFKD, strip combining marks, casefold. Both sides of every name comparison."""
    return "".join(c for c in unicodedata.normalize("NFKD", str(s))
                   if not unicodedata.combining(c)).casefold().strip()


# ------------------------------------------------------------------- exemptions
# Enumerated sets, never patterns (a pattern wide enough to cover the false
# positives is an escape hatch a real failure can name itself into).
#
#   captured_output      machine stdout, not authorship
#   *.quote              rules_claims quotes must be verbatim
#   *.pattern/field/flags regexes, not prose
#   manifest*            filenames
#   data_fingerprint*    hashes
EXEMPT_KEYS = {"captured_output"}
QUERYFIELD = re.compile(r"\.(pattern|field|flags)$")


def _exempt_path(p):
    return (p.endswith(".quote") or p.startswith("manifest")
            or p.startswith("data_fingerprint") or QUERYFIELD.search(p) is not None)


# ---------------------------------------------------------------- ARTIFACTS
# One registry. Adding an artifact costs an entry here, not a copy of the
# scanning code -- which is the whole point of this file existing.
#
#   abs_exempt  paths exempt from the ABSOLUTE scan alone, with the reason
#   name_paths  where card names appear as bare strings rather than [[marked]]
ARTIFACTS = {
    "strategy": {
        # rows[].claim has its own check, which also runs the falsifying query;
        # rows[].contradicts must contain the sentence "none found" per 0b.
        "abs_exempt": lambda p: (p.startswith("rows[")
                                 and (p.endswith(".claim") or ".contradicts" in p)),
        "name_paths": [re.compile(r"^rows\[\d+\]\.pool_hits\[\d+\]$"),
                       re.compile(r"^rows\[\d+\]\.contradicts\.cards\[\d+\]$"),
                       re.compile(r"^weakness_answers\.[^.]+\.cards\[\d+\]$"),
                       re.compile(r"^kill_chain\[\d+\]\.cards\[\d+\]$")],
    },
    "candidates": {
        "abs_exempt": lambda p: False,
        "name_paths": [re.compile(r"^candidates\[\d+\]\.(name|beat)$"),
                       re.compile(r"^carried_from_strategy\[\d+\]\.name$"),
                       re.compile(r"^hand_added\[\d+\]\.name$")],
    },
    "deck": {
        "abs_exempt": lambda p: False,
        "name_paths": [re.compile(r"^deck\[\d+\]\.(name|beat)$"),
                       re.compile(r"^bench\[\d+\]\.(name|lost_to)$"),
                       re.compile(r"^weak_slots\[\d+\]$")],
    },
    "audit": {"abs_exempt": lambda p: False, "name_paths": []},
}


def _cfg(kind):
    return ARTIFACTS.get(kind, ARTIFACTS["audit"])


def walk(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in EXEMPT_KEYS:
                continue
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def authored(obj):
    """Every authored string in the artifact, with its path."""
    return [(p, t) for p, t in walk(obj) if not _exempt_path(p)]


def collect_names(obj, kind):
    """Every card name the artifact asserts: [[marked]] prose plus the enumerated
    bare-name paths. Returns {name: first path it appeared at}."""
    out = {}
    pats = _cfg(kind)["name_paths"]
    for p, t in walk(obj):
        if _exempt_path(p):
            continue
        for n in CARDREF.findall(t):
            out.setdefault(n, p)
        if any(rx.match(p) for rx in pats):
            out.setdefault(t, p)
    for r in (obj.get("rows", []) if isinstance(obj, dict) else []):
        for n in (r.get("referents") or {}):
            out.setdefault(n, f"rows/{r.get('id')}.referents")
    return out


# ------------------------------------------------------------------- the scans
def scan(obj, kind, *, pool_names=(), oracle_text=None, registered=(),
         referents=(), run_query=None):
    """Return {check_label: [violation strings]}. Empty lists mean the check passed.

    run_query(spec) -> DataFrame | None | str, supplied by the caller so this file
    never imports pandas or touches a CSV.
    """
    oracle_text = oracle_text or {}
    npool = {norm(n) for n in pool_names}
    abs_exempt = _cfg(kind)["abs_exempt"]
    A = authored(obj)
    v = {k: [] for k in
         ("card references resolve to the pool",
          "absolutes in prose are registered with a falsifying query",
          "every registered prose absolute survives its own falsifying query",
          "pronoun cards named in prose carry a referent enumeration",
          "every use of dead/absent carries a label")}

    # -- [[card]] resolves, accent-insensitively (v9: see 3.7 rule 6) ------------
    prose_cards = {}
    for p, t in A:
        for name in CARDREF.findall(t):
            prose_cards.setdefault(name, p)
            if norm(name) not in npool and norm(name) not in {norm(b) for b in BASICS}:
                v["card references resolve to the pool"].append(
                    f"{p}: [[{name}]] is not in the pool")

    # -- absolutes ---------------------------------------------------------------
    reg_text = [a.get("quote", "") for a in registered]
    for a in registered:
        fq = a.get("falsifying_query")
        q = (a.get("quote", "") or "")[:40]
        if not fq:
            v["every registered prose absolute survives its own falsifying query"].append(
                f"{q}...: no falsifying_query")
            continue
        if run_query is None:
            continue
        h = run_query(fq)
        if isinstance(h, str) or h is None:
            v["every registered prose absolute survives its own falsifying query"].append(
                f"{q}...: {h}")
        elif len(h):
            v["every registered prose absolute survives its own falsifying query"].append(
                f"{q}...: absolute is false -- {sorted(h['name'])[:5]} ({len(h)} total)")
    for p, t in A:
        if abs_exempt(p):
            continue
        for s in SENT.split(t):
            m = ABSOLUTE.search(s)
            if not m:
                continue
            if m.group(0).lower() == "none" and NONE_FOUND.search(s):
                continue
            if any(q and (q in s or s.strip() in q) for q in reg_text):
                continue
            v["absolutes in prose are registered with a falsifying query"].append(
                f"{p}: {m.group(0)!r} in {s.strip()[:70]!r}")

    # -- pronouns ----------------------------------------------------------------
    have = set(referents)
    for name, where in prose_cards.items():
        if name in oracle_text and PRONOUN.search(oracle_text[name]) and name not in have:
            v["pronoun cards named in prose carry a referent enumeration"].append(
                f"{where}: [[{name}]]")

    # -- dead / absent -----------------------------------------------------------
    for p, t in A:
        for s in SENT.split(t):
            if DEADWORD.search(s) and not any(l in s for l in LABELS):
                v["every use of dead/absent carries a label"].append(
                    f"{p}: {s.strip()[:70]!r}")
    return v


def scan_markdown(text, path_label="document"):
    """Same scans over an authored Markdown file (audit.md). Text-only checks."""
    return scan({"body": text}, "audit")


def _cli_context():
    """Wire the scans to the pool.

    scan() deliberately takes pool_names / oracle_text / run_query from its caller
    so the module never touches a CSV. The CLI never supplied them, which made the
    [[card]] check fail on every reference and the falsifying-query check vacuous.
    """
    import pandas as pd
    import config
    p = pd.read_csv(config.resolve(config.FILES["POOL"]), encoding=config.ENCODING)
    names = p["name"].fillna("").astype(str).tolist()
    oracle = {n: str(t) for n, t in zip(p["name"], p["oracle_text"].fillna(""))}

    def run_query(spec):
        """spec: {"column": "oracle_text"|"type_line", "regex": "..."} or a bare regex."""
        col, rx = "oracle_text", spec
        if isinstance(spec, dict):
            col, rx = spec.get("column", "oracle_text"), spec.get("regex", "")
        if col not in p.columns:
            return f"no such column {col!r}"
        try:
            return p[p[col].fillna("").astype(str).str.contains(rx, case=False, regex=True)]
        except Exception as e:                                    # a broken regex is
            return f"query failed: {e}"                           # a failed check, not a pass

    return names, oracle, run_query


if __name__ == "__main__":
    target = sys.argv[1]
    kind = ("strategy" if "strategy" in target else
            "deck" if "deck" in target else
            "candidates" if "candidates" in target else "audit")
    names, oracle, run_query = _cli_context()
    if target.endswith(".json"):
        obj = json.load(open(target, encoding="utf-8"))
        res = scan(obj, kind, pool_names=names, oracle_text=oracle, run_query=run_query,
                   registered=obj.get("prose_absolutes", []),
                   referents=obj.get("pronoun_referents", {}))
    else:
        # a markdown artifact carries its registrations in <target>.absolutes.json
        side = target.rsplit(".", 1)[0] + ".absolutes.json"
        reg, ref = [], {}
        if os.path.isfile(side):
            s = json.load(open(side, encoding="utf-8"))
            reg, ref = s.get("prose_absolutes", []), s.get("pronoun_referents", {})
        res = scan({"body": open(target, encoding="utf-8").read()}, "audit",
                   pool_names=names, oracle_text=oracle, run_query=run_query,
                   registered=reg, referents=ref)
    bad = 0
    for check, items in res.items():
        if items:
            bad += len(items)
            print(f"FAIL  {check}  ({len(items)})")
            for i in items[:8]:
                print(f"        {i}")
        else:
            print(f"pass  {check}")
    sys.exit(1 if bad else 0)
