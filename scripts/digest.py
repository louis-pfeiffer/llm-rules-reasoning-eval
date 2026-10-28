"""digest.py -- the pool, small enough to read.

Reading the whole pool into the model is most of the cost of a build and
little of the quality: the model needs the best N in each function, and the
lands.

This writes digest.md: for each function tag, the top N rows ordered by
edhrec_rank (a popularity prior, used as an ORDERING key, never as a reason),
with cost, type and trimmed oracle text; then the lands. Lands are listed in
full only when the commander's own text mentions lands or the pool's land count
is small; otherwise the top --lands-cap by rank, plus every land that produces
two or more of the commander's colours, since fixing is what a multicolour
mana base is judged on. Cards outside the digest are still legal picks -- pool_tagged.csv is
one grep away and the prompt tells the model to go there when a package's
criterion is not satisfied by what the digest shows.

Run:   python digest.py [--per-tag 15] [--oracle-chars 170] [--lands-cap 40] [--all-lands]
"""
import argparse
import re

import pandas as pd

import config

import json
import os

from prep import TAG_ORDER   # one tag list, declared in prep.py


def trim(t, n):
    t = re.sub(r"\s+", " ", str(t or "")).strip()
    return t if len(t) <= n else t[: n - 1] + "\u2026"


def row_line(r, n):
    rank = "" if pd.isna(r.get("edhrec_rank")) else f"#{int(r['edhrec_rank'])}"
    gc = " [HIGH-IMPACT]" if bool(r.get("game_changer")) else ""
    return (f"- {r['name']} | {r['mana_cost'] if isinstance(r['mana_cost'], str) else '-'} "
            f"| {r['type_line']} | {rank}{gc} | {trim(r['oracle_text'], n)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-tag", type=int, default=15)
    ap.add_argument("--oracle-chars", type=int, default=170)
    ap.add_argument("--lands-cap", type=int, default=40)
    ap.add_argument("--all-lands", action="store_true")
    ap.add_argument("--out", default="digest.md")
    a = ap.parse_args()

    pool = pd.read_csv(config.resolve("pool_tagged.csv"), encoding="utf-8-sig")
    pool["edhrec_rank"] = pd.to_numeric(pool.get("edhrec_rank"), errors="coerce")
    o = []
    w = o.append

    w(f"# digest.md — {len(pool)} pool rows, top {a.per_tag} per function")
    w("Ordering key: edhrec_rank ascending (popularity prior, NOT a power ranking "
      "and NOT commander-aware). Rank orders candidates inside a function; the "
      "oracle text decides. Anything not shown here is still legal: grep "
      "pool_tagged.csv by tag before concluding a function is short.")

    def has(tag):
        return pool[pool["tags"].fillna("").str.contains(rf"(?:^|;){re.escape(tag)}(?:;|$)")]

    w("\n## Function counts (whole pool, not just the digest)")
    for t in TAG_ORDER + ["land"]:
        w(f"- {t}: {len(has(t))}")

    # --- index: names only, in rank order. ~3 tokens a card. ---
    keep = {}
    w("\n## Function index — top candidates per function, rank order, names only")
    for t in TAG_ORDER:
        sub = has(t)
        if not len(sub):
            w(f"- **{t}: 0 rows.** A zero is a hypothesis about the query before it "
              f"is a fact about the pool (P2) — re-query the bare outcome over "
              f"pool_tagged.csv before labelling it.")
            continue
        sub = sub.sort_values("edhrec_rank", na_position="last").head(a.per_tag)
        for n in sub["name"]:
            keep.setdefault(n, set()).add(t)
        w(f"- **{t}** ({len(has(t))} in pool): " + ", ".join(sub["name"]))

    # --- detail: each card ONCE, with every tag it carries ---
    det = pool[pool["name"].isin(keep)].copy()
    det = det[~det["tags"].fillna("").str.contains("(?:^|;)land(?:;|$)")]
    det = det.sort_values("edhrec_rank", na_position="last")
    w(f"\n## Spell detail — {len(det)} distinct non-land cards, each listed once")
    w("name | cost | type | rank | tags | oracle")
    for _, r in det.iterrows():
        w(row_line(r, a.oracle_chars) + f" | tags: {r['tags']}")

    lands = has("land").sort_values("edhrec_rank", na_position="last")
    spec_path = config.resolve("build_spec.json")
    spec = json.load(open(spec_path, encoding="utf-8")) if spec_path else {}
    cmd_text = str(spec.get("commander_oracle_text", ""))
    ci = set(str(spec.get("color_identity", "")))
    cares = bool(re.search(r"\blands?\b|landfall", cmd_text, re.I))
    if a.all_lands or cares or len(lands) <= a.lands_cap:
        shown, why = lands, ("commander text mentions lands" if cares else
                             "--all-lands" if a.all_lands else "pool land count is small")
    else:
        srcs = lands.get("colour_sources_text", pd.Series("", index=lands.index)).fillna("")
        fixers = lands[srcs.map(lambda s: len(set(str(s)) & ci) >= 2)].head(a.lands_cap)
        top = lands.head(a.lands_cap)
        shown = lands[lands["name"].isin(set(top["name"]) | set(fixers["name"]))]
        why = (f"top {a.lands_cap} by rank plus the top {len(fixers)} land(s) producing two "
               f"or more of the commander's colours; grep pool_tagged.csv for the rest")
    w(f"\n## Lands — showing {len(shown)} of {len(lands)} ({why})")
    for _, r in shown.iterrows():
        extra = f" | tags: {r['tags']}" if r["tags"] != "land" else ""
        w(row_line(r, min(a.oracle_chars, 130)) + extra)

    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(o))
    size = os.path.getsize(a.out)
    print(f"wrote {a.out}  {size/1000:.0f} KB  (~{size//4} tokens)  "
          f"pool.csv is {os.path.getsize(config.resolve('pool.csv'))/1000:.0f} KB")


if __name__ == "__main__":
    main()
