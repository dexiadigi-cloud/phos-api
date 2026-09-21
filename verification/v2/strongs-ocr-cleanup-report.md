# Strong's OCR Cleanup Report

**Date:** 2026-09-21
**Database:** `data/study.db`
**Backup:** `data/study.db.bak-strongs-ocr-20260920` (462,344,192 bytes, created before any changes)
**Source rows:** 13,260 (Strong's lexicon entries)

## Pre-clean condition

The Strong's `definition` field contained extensive OCR damage at entry heads:
- Mangled Latin transliterations of Greek/Hebrew headwords (e.g. `PoXVj` for βολή, `dSworlu` for ἀδυνατέω, `"APioilS` for Ἀβιούδ)
- Broken number prefixes (e.g. `709.2.` for G1092, `11.54-` for G1154, `104-` for G104)
- Spurious commas on heads (e.g. `'APpadp,` for Ἀβραάμ)
- Fragmented multi-token heads (e.g. `'  ApiaBap` for Ἀβιαθάρ)

## Method

Two-tier conservative repair, dry-run verified before apply:

**Head repair (primary):** Structural anchor detection. The first `,`- or `;`-terminated token identifies the head span (head + transliteration + pronunciation is the Strong's format). The span is replaced with the correct lemma from STEPBible (CC BY 4.0) or BDB, keyed by normalized Strong's number (padded `G0025` → unpadded `G25`). Guards: span ≤4 tokens, no English stopwords, no parens, single-word candidate only, accent/pointing variants allowed (1,217 picks), real textual variants left untouched.

**Prefix repair (strict mechanical only):** Punctuation-only (`104-` → `104.`) or single-character OCR confusion (`709.2.` → `1092.`, `104S.` → `1043.`). Multi-confusion prefixes left as-is to avoid masking misalignments.

**Explicitly excluded:** A first-token fallback was tried and DISABLED after audit found it replacing English words (`name`, `resident`, `usage:`, `HEBREW`, `Hittites.`) and punctuation (`;`, `:—`). One blocklisted candidate (G1679: STEP says ἐλπίζω, Strong's definition is about Elmodam).

## Results

**Entries changed:** 11,568 (87.2%)
- Head via comma anchor: 11,115
- Head via semicolon anchor: 409
- Head with spurious comma: 44
- Prefix punctuation-only fixes: 176
- Prefix single-confusion fixes: 76
- (10,450 entries had head fixed with prefix already correct)

**Entries untouched:** 1,692 (12.8%), logged with reasons in `data/staging/strongs_ocr_skipped.jsonl`:
- Head span contains parens (definition text, not a head): 728
- Real textual variant, ambiguous which lemma: 460
- No clean candidate in STEP/BDB: 243
- Head span contains English: 80
- Empty definition (no tokens): 45
- Pronunciation first (head missing): 38
- No structural anchor found: 36
- Ambiguous comma (may be transliteration): 16
- Head span too long (>4 tokens): 18
- Other: 27

**Machine-readable logs:**
- `data/staging/strongs_ocr_changes.jsonl` (11,568 entries, before/after)
- `data/staging/strongs_ocr_skipped.jsonl` (1,936 entries with reasons; some entries logged for both head and prefix)

## Verification

- Row count: 13,260 (unchanged) ✓
- `PRAGMA integrity_check`: ok ✓
- Spot checks: G1000 (`PoXVj` → `βολή`), G11 (`'APpadp,` → `Ἀβραάμ`), H1049 (3-token fragmented head → `בֵּית־צוּר`), G1092 (`709.2.` → `1092.`), G1154 (`11.54-` → `1154.`) ✓
- Zero remaining instances of sampled mangled heads (`PoXVj`, `dSworlu`, `"APioilS`) ✓
- Zero remaining instances of sampled broken prefixes (`104-`) ✓
- API suite: 185 passed, 3 warnings (same as pre-clean) ✓
- `/v1/word` tests: pass (included in suite) ✓

## Notes for composite endpoint

The Strong's definitions are now substantially cleaner at entry heads. The 1,692 untouched entries retain their original (damaged) heads; the endpoint truncates to 250 chars, so the most visible improvement is in the first 1-3 tokens. Transliterations and pronunciations were NOT modified (they remain OCR-damaged in many entries); only the headword and number prefix were repaired.
