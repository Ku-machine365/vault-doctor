# PREREG — vault-doctor v1

Fixed: 2026-10-11 12:00 KST (committed before the tool code and before measuring).

## Question
Does a read-only tool count broken wikilinks, orphan notes and ledger <-> card mismatches in a real vault accurately (few false positives)?

## Definitions (v1)
- Note: `*.md` in the vault (excluding `.obsidian/`, `.git/`, `.trash/`).
- Wikilink: `[[t]]`, `[[t|alias]]`, `[[t#h]]`, `![[t]]`; code blocks and inline code excluded. Resolved Obsidian-style; `[[#h]]` counts as resolved.
- Orphan: note with zero inbound wikilinks / markdown links. Excluded: `Templates/`, root `README.md`, `MOC*`.
- Card: `<projects-dir>/<name>/README.md`. Ledger entry linked to a card when the card folder name appears in it.
  - Mismatch A: active entry, card `updated` older than 7 days. Mismatch B: card status done but entry active.

## Success criteria
1. Synthetic-vault test (`tests/`): all three counts exactly match.
2. Real vault: 0 files changed by the tool (`find <vault> -newer <marker>`).
3. Real vault runtime < 30 s.
4. Precision (broken links): random 5 reported targets checked by hand, >= 4/5 really missing.
5. Precision (orphans): random 5 checked with `grep -rF`, >= 4/5 really unlinked.
6. Card count equals the count from an independent existing card checker.
7. No write calls in code (grep).

## Changes
- 2026-10-11 12:05 [correction] the first run excluded `node_modules/`, which was not in the definition; official numbers were recounted with the definition as written. Whether to exclude `node_modules` is a v2 decision (the published code excludes it).

## Result (2026-10-11 12:05 KST)
7 criteria: PASS 7 / FAIL 0 (one definition violation corrected, above). Run time 0.14 s.
Raw results were measured on the author's private vault and are **not published**.

### Out-of-rule notes
- Most "broken" unique targets were numeric citation markers like `[[1]](https://…)` — technically broken wikilinks, not real problems. v2 candidate: ignore `[[digits]](`.
- Most orphans were auto-generated notes; read the orphan count as "not linked from an index", not "needs fixing".
- Linking ledger entries to cards by folder name only links a minority of entries (known limitation).
