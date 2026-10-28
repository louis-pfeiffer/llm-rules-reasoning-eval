"""config.py -- the only place a filename is declared.

Both validators and the renderer import from here. Repointing the whole build
at a different pool, collection, universe or rules file is an edit to the four
lines in FILES and nothing else.

Paths are resolved at import time across the locations a project file can land
in, so the same script runs unchanged whether the files sit in the project
mount, the uploads mount or the working directory.
"""
import hashlib
import os
import sys
import unicodedata
from datetime import datetime, timezone

# ------------------------------------------------------------------ SWAP HERE
# POOL is generated per commander and restriction by prep.py. It is not a fixed
# asset: a pool built for one commander is the wrong pool for the next. There is
# deliberately no fallback to an older named pool -- a missing pool.csv must
# halt the build, not quietly load a previous commander's cards.
POOL_CANDIDATES = ["pool.csv"]

FILES = {
    "POOL":     "pool.csv",                      # source of truth for the 99
    "PARENT":   "MTG_collection_annotated.csv",  # negative control; never a card source
    "UNIVERSE": "scryfall_universe.csv",         # every commander-legal card; Phase 9 + control
    "RULES":    "MagicCompRules_20260819.txt",   # authority for every rules interaction
}
# -----------------------------------------------------------------------------

SEARCH_PATH = [
    ".",
    "/mnt/project",
    "/mnt/user-data/uploads",
    os.path.dirname(os.path.abspath(__file__)),
]

ENCODING = "utf-8-sig"   # required for every CSV in this project


def resolve(filename):
    """First existing match across SEARCH_PATH, else None."""
    for d in SEARCH_PATH:
        p = os.path.join(d, filename)
        if os.path.isfile(p):
            return os.path.abspath(p)
    return None


def _resolve_pool():
    for cand in POOL_CANDIDATES:
        hit = resolve(cand)
        if hit:
            FILES["POOL"] = cand
            return hit
    return FILES["POOL"]


POOL     = _resolve_pool()
PARENT   = resolve(FILES["PARENT"])   or FILES["PARENT"]
UNIVERSE = resolve(FILES["UNIVERSE"]) or FILES["UNIVERSE"]
RULES    = resolve(FILES["RULES"])    or FILES["RULES"]

# UNIVERSE is optional for validation; prep.py needs it to resolve the commander
# and to enrich the pool.
REQUIRED = ("POOL", "PARENT", "RULES")


def check(verbose=True, halt=True):
    """Preflight. Run once at the top of every turn, before anything else.

    Returns the resolved-path dict. Halts on a missing required file, because a
    build that silently proceeds without its pool produces confident nonsense.
    """
    resolved = {k: resolve(v) for k, v in FILES.items()}
    missing = [k for k in REQUIRED if resolved[k] is None]

    if verbose:
        print(f"{'FILE':<10} {'STATUS':<8} {'SIZE':>10}  PATH")
        for k, name in FILES.items():
            p = resolved[k]
            if p:
                size = f"{os.path.getsize(p)/1e6:.2f} MB"
                print(f"{k:<10} {'ok':<8} {size:>10}  {p}")
            else:
                tag = "MISSING" if k in REQUIRED else "absent"
                print(f"{k:<10} {tag:<8} {'-':>10}  {name} not found on SEARCH_PATH")
        if resolved["UNIVERSE"] is None:
            print("\nNOTE: UNIVERSE absent. prep.py cannot run, and purchase "
                  "suggestions cannot be checked against card data.")

    if missing and halt:
        print(f"\nHALT: required file(s) missing: {missing}")
        sys.exit(1)
    return resolved


def load(key):
    """Load a declared CSV with the project's encoding. Rules file returns text."""
    import pandas as pd
    path = resolve(FILES[key])
    if path is None:
        raise FileNotFoundError(f"{key} ({FILES[key]}) not found on {SEARCH_PATH}")
    if path.lower().endswith(".txt"):
        return open(path, encoding=ENCODING).read()
    return pd.read_csv(path, encoding=ENCODING)


# ---------------------------------------------------------------------------
# v9 / 3.7.6 -- normalise before you compare.
# The collection export stores names as unaccented lowercase ASCII; Scryfall
# stores the canonical Unicode form. In the v8 build "Mists of Lorien" was in
# the pool and two independent queries agreed it was not, because the name is
# "Mists of Lorien" with an accented o and both patterns looked for "orien".
# 3.2's three-tier control cannot catch this: the card is in the pool, so every
# tier returns the same nothing and all three agree the absence is real.
# ---------------------------------------------------------------------------
def norm(s):
    """NFKD, strip combining marks, casefold. Both sides of every comparison."""
    return "".join(c for c in unicodedata.normalize("NFKD", str(s))
                   if not unicodedata.combining(c)).casefold().strip()


def find(df, name, column="name"):
    """Normalised lookup. Returns the matching rows, which may be empty."""
    return df[df[column].fillna("").astype(str).map(norm) == norm(name)]


# ---------------------------------------------------------------------------
# v9 / 3.0 -- inputs are dated snapshots, and every artifact is pinned to one.
# A pool that gains a row makes an artifact STALE, not WRONG. The remedy is
# re-running the turn, never patching the artifact: its recorded queries were
# run against the old pool, and reconciling by hand decouples every claim from
# the evidence that produced it.
# ---------------------------------------------------------------------------
def fingerprint(verbose=False):
    import pandas as pd
    h = hashlib.sha256()
    out = {}
    for key in ("POOL", "PARENT", "UNIVERSE", "RULES"):
        path = resolve(FILES[key])
        if not path:
            out[key.lower() + "_rows"] = None
            h.update(b"MISSING")
            continue
        st = os.stat(path)
        if key == "RULES":
            rows = sum(1 for _ in open(path, encoding=ENCODING))
        else:
            rows = int(len(pd.read_csv(path, encoding=ENCODING)))
        out[key.lower() + "_rows"] = rows
        h.update(f"{FILES[key]}|{rows}|{st.st_size}".encode())
    out["hash"] = h.hexdigest()[:8]
    out["captured"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if verbose:
        print("\nDATA FINGERPRINT  " + "  ".join(f"{k}={v}" for k, v in out.items()))
    return out


def fingerprint_matches(recorded):
    """True if the artifact was built on the files now on disk."""
    cur = fingerprint()
    if not recorded:
        return False, "artifact carries no data_fingerprint (v9 3.0)"
    diffs = [f"{k}: artifact {recorded.get(k)} -> files {cur[k]}"
             for k in ("pool_rows", "parent_rows", "universe_rows")
             if recorded.get(k) is not None and recorded.get(k) != cur[k]]
    if recorded.get("hash") == cur["hash"] and not diffs:
        return True, f"hash {cur['hash']}"
    return False, "; ".join(diffs) or f"hash {recorded.get('hash')} -> {cur['hash']}"


if __name__ == "__main__":
    check()
    fingerprint(verbose=True)
