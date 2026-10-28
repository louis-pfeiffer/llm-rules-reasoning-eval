"""theme_tag.py -- adds a `theme` column to pool_tagged.csv (pool.csv untouched,
so the data fingerprint is unchanged). Candidate filter; oracle text is the verdict.
  fd_entry     a card enters face down as a creature (manifest / manifest dread / cloak / face-down entry)
  fd_support   face-down payoffs, turn face up, morph / megamorph / disguise
  uncast_entry a nontoken creature enters without being cast (ninjutsu, reanimation, blink, unearth, put-from-zone; embalm/eternalize/encore excluded: tokens)
  free_cast    a spell cast without paying its mana cost (Satoru: no mana spent)
"""
import re, pandas as pd
T = {
 "fd_entry":     r"\bmanifest|\bcloak|onto the battlefield face[- ]down|face[- ]down onto the battlefield",
 "fd_support":   r"face[- ]down|turned face up|turn [^.]*face up|\bmorph\b|megamorph|\bdisguise\b",
 "uncast_entry": r"ninjutsu|put (a|an|any number of|up to \w+|target|that|it|those) [^.]*(creature|permanent) cards?[^.]*onto the battlefield|put [^.]*creature cards? [^.]*onto the battlefield|return [^.]*creature cards? [^.]*(?:to|onto) the battlefield|exile [^.]*(?:creature|permanent)[^.]*return (?:it|that card|them|those cards) to the battlefield|return (?:it|that card|them|those cards) to the battlefield under (?:its owner.s|your) control|\bunearth\b",
 "free_cast":    r"without paying (its|their) mana costs?",
}
p = pd.read_csv("pool_tagged.csv", encoding="utf-8-sig")
txt = p["oracle_text"].fillna("")
p["theme"] = [";".join(k for k, rx in T.items() if re.search(rx, t, re.I)) for t in txt]
p.to_csv("pool_tagged.csv", index=False, encoding="utf-8")
nl = ~p["type_line"].fillna("").str.contains("Land")
for k in T:
    print(f"  {k:<13} {int(p['theme'].str.contains(k)[nl].sum()):>4} nonland")
print(f"  any theme     {int((p['theme']!='')[nl].sum()):>4} nonland of {int(nl.sum())}")
