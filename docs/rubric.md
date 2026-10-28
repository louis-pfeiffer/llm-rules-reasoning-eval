# Ranking rubric — the single declaration

Read by P2 (to rank shortlists) and P3 (to rebuild a package blind). Edit it
here and nowhere else.

Compare two cards on criterion 1; move to the next criterion only if they are
level on it. A comparison decided by a criterion's judgement, not its
definition, says what the judgement was. Record the deciding criterion's number
as `decided_by` on the survivor and on the benched card.

1. **Floor.** The card's worst realistic use in this deck on an average turn it
   is drawn — not its best case. A card that often sits in hand unplayed, or is
   played for little, has a low floor however high its ceiling. The higher
   floor wins.
2. **Deployability.** Can it be cast on the turn it matters without giving up
   mana held for interaction? Instant speed, or a use at the end of the turn
   before yours, beats sorcery speed. A sorcery names the effect that justifies
   the reactive turn it costs.
3. **Mana flexibility.** Modal, scalable or multi-use cards that turn otherwise
   unspent mana into value beat fixed single-use effects at a similar cost. Mana
   left unspent at the end of a turn cycle is a loss.
4. **Overlap.** A card that also meets another package's criterion beats one
   that meets only its own. Record the second package in `roles_secondary`.
5. **Castability.** Lower demand on the scarcer colour wins: count pips against
   the colour sources counted from oracle text.
6. **Popularity.** `edhrec_rank`, and only when 1–5 are level.

**Finisher exemption.** A card supplying a `kill_chain` link may be ranked on
its ceiling instead of its floor, provided its `note` states its fallback use
when the win is not set up (for an extra turn: untap everything and draw a
card). The exemption covers kill-chain links only, never a card that is merely
powerful.

**Pet cards.** A card in `meta.pet_cards` is not ranked out. It goes in the
deck, or into `test_slots` with the case for and against it and the card it
would replace.
