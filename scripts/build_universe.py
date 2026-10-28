"""build_universe.py -- Scryfall oracle-cards bulk (.jsonl.gz or .json) -> scryfall_universe.csv
Same schema, encoding (UTF-8 BOM, CRLF) and conventions as the existing universe file.
Run: python build_universe.py <bulk file> <collection csv> <out csv>
"""
import gzip, json, sys, unicodedata
import pandas as pd

def norm(s):
    return "".join(c for c in unicodedata.normalize("NFKD", str(s))
                   if not unicodedata.combining(c)).casefold().strip()

def records(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        head = f.read(1); f.seek(0)
        if head == "[":
            yield from json.load(f)
        else:
            for line in f:
                line = line.strip().rstrip(",")
                if line and line not in "[]":
                    yield json.loads(line)

def txt(s):
    return (s or "").replace("\n", " | ")

def letters(xs):
    return "".join(sorted(xs or [])) or None

src, coll, out = sys.argv[1:4]
owned = set(pd.read_csv(coll)["name"].map(norm))
rows = []
for c in records(src):
    if c.get("legalities", {}).get("commander") != "legal":
        continue
    faces = c.get("card_faces") or []
    if faces:
        mana_cost = c.get("mana_cost") or faces[0].get("mana_cost") or None
        oracle = " | -- | ".join(txt(f.get("oracle_text")) for f in faces)
        ftypes = [f.get("type_line", "") for f in faces]
    else:
        mana_cost = c.get("mana_cost") or None
        oracle = txt(c.get("oracle_text"))
        ftypes = [c.get("type_line", "")]
    tl = c.get("type_line", "")
    usd = (c.get("prices") or {}).get("usd")
    rows.append({
        "name": c["name"], "mana_cost": mana_cost, "cmc": float(c.get("cmc") or 0),
        "type_line": tl, "color_identity": letters(c.get("color_identity")),
        "oracle_text": oracle or None, "produced_mana": letters(c.get("produced_mana")),
        "commander_legality": "legal", "game_changer": bool(c.get("game_changer")),
        "is_land": "Land" in tl, "is_instant": "Instant" in tl, "is_sorcery": "Sorcery" in tl,
        "mdfc_land_back": len(ftypes) > 1 and "Land" in ftypes[1] and "Land" not in ftypes[0],
        "owned": norm(c["name"]) in owned,
        "usd": float(usd) if usd else None,
        "edhrec_rank": float(c["edhrec_rank"]) if c.get("edhrec_rank") is not None else None,
    })
df = pd.DataFrame(rows).drop_duplicates("name").sort_values("name", key=lambda s: s.map(str))
df.to_csv(out, index=False, encoding="utf-8-sig", lineterminator="\r\n")
print(f"{len(df)} commander-legal cards -> {out}")
