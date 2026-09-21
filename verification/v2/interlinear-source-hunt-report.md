# Interlinear Source Hunt Report (2026-09-20)

Research only. Nothing was ingested; `data/scripture.db` and
`data/study.db` were not touched. Candidate downloads live under
`data/staging/interlinear/` with `sha256sums.txt`.

## Objective

Find a word-aligned Hebrew/Greek Bible text (each word tagged with a
Strong's number, morphology, and an English gloss) that clears the Phos
rights bar: public domain or CC BY 4.0 only. CC BY-SA and BY-NC-SA are
not approved. A work's age does not automatically clear a modern
transcription, compilation, or digital edition.

## Verdict summary

| Candidate | Rights verdict | Coverage |
|-----------|---------------|----------|
| STEPBible TAHOT + TAGNT (Tyndale House) | CLEAR, CC BY 4.0 | OT Hebrew + NT Greek, words + Strong's + morphology + glosses |
| Robinson's morphological parsings (byztxt) | CLEAR, public domain | NT Greek only, parsing + Strong's, no glosses (fallback) |
| Open Scriptures morphhb (OSHB) | CLEAR on rights, CC BY 4.0 | Hebrew only, morphology only, no glosses, no Strong's (weakest) |

Recommendation: build the interlinear on STEPBible TAHOT/TAGNT. It is
the only candidate with all four layers (word, Strong's, morphology,
gloss) for both testaments under an approved license.

---

## Candidate 1: STEPBible TAHOT + TAGNT — CLEAR (CC BY 4.0)

Source repository: https://github.com/STEPBible/STEPBible-Data
(Tyndale House, Cambridge; data created for www.STEPBible.org).

### Exact files examined

Under `Translators Amalgamated OT+NT/`:

- `TAGNT Mat-Jhn - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt` (14,189,032 bytes)
- `TAGNT Act-Rev - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt` (15,939,932 bytes)
- `TAHOT Gen-Deu - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt` (18,190,455 bytes)
- `TAHOT Jos-Est - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt` (24,500,317 bytes)
- `TAHOT Job-Sng - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt` (9,540,133 bytes)
- `TAHOT Isa-Mal - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt` (17,977,518 bytes)

SHA-256 for each file recorded in
`data/staging/interlinear/sha256sums.txt`. (An `Older Formats/`
directory holds superseded TAGNT copies; the files above are current.)

### License evidence (three independent layers)

1. Repository README, line 1: `# STEPBible Data Repository **CC BY 4.0**`
   (downloaded 2026-09-20 to `data/staging/interlinear/stepbible-readme.md`).
2. In-file header of every tagged-text file:
   `Data created by www.STEPBible.org based on work at Tyndale House
   Cambridge (CC BY 4.0)`, plus an explicit permissions block allowing
   inclusion of any part of the data in software or publications without
   requesting permission, and downloading/reformatting for applications.
3. The license is in the filenames themselves (`... STEPBible.org CC-BY.txt`).

This matches the license already verified in-file for the four STEPBible
lexicons merged earlier today.

### Rights nuances investigated

1. **TAGNT English gloss column and the Berean Study Bible.** The TAGNT
   header states the per-word English column is "Based on Berean Study
   Bible, with permission, as at 1-July-2019 and adapted for this work."
   This is not a blocker for Phos: the Berean Bible texts were dedicated
   to the public domain on 2023-04-30, and Phos already ingests BSB as a
   PD translation (see `api/translations.py`). Separately, the
   "Dictionary form = Gloss" column (`βίβλος=book`) is sourced from TBESG,
   which Phos already holds under CC BY 4.0. A future ingest can use the
   TBESG-derived gloss column as primary and treat the BSB-derived column
   as secondary; both clear.
2. **TAHOT English gloss column.** No Berean or other third-party
   attribution appears in any of the four TAHOT files (zero "Berean"
   mentions). The gloss mirrors the Hebrew word structure and is
   STEPBible's own work under the file's CC BY 4.0.
3. **"Please do not redistribute it yourself."** The header asks users to
   refer others to github.com/STEPBible rather than redistributing. This
   is a stated preference, not a license term; the binding license is
   CC BY 4.0, and the same header expressly permits including the data in
   software and publications. Independent downstream projects reached the
   same conclusion. Phos must still honor the real CC BY 4.0 duties:
   credit STEP Bible with a link to https://www.STEPBible.org, record
   modifications, and keep the attribution with the data.
4. **Morphology provenance.** TAGNT grammar builds on James Tauber's work
   with additions by Tyndale scholars; TAHOT morphology is from ETCBC
   with Ketiv forms parsed by Tyndale scholars. Both are covered by
   STEPBible's CC BY 4.0 assertion on the amalgamated files, which is the
   license Phos would take the data under (same posture as the lexicon
   merge).
5. **Columns to exclude.** The Spanish translation column (Marvel Bible
   Project / OpenGNT) and the sub-meaning column (CSG from Marvel Bible
   Project) have third-party provenance that was not verified. Neither is
   needed; exclude both from any ingest.

### Data format (verified from file headers and rows)

Verse-level rows: `# Mat.1.1` (full Greek/Hebrew verse text),
`#_Translation` (English), `#_Word=Grammar` (per-word tags).

Word rows are tab-separated with a reference key, the word (Greek with
transliteration in parentheses; Hebrew with `/` separating prefixes,
root, suffixes), an English gloss, disambiguated Strong's plus
morphology (`G0976=N-NSF`, `{H1254A}`), a lemma=gloss field, edition
markers, and `sStrong+Instance` (plain Strong's number with `_A`/`_B`
instance marks, e.g. `G5207_A`). The plain-Strong's column joins cleanly
to the lexicons Phos already holds (`/v1/word` normalizes number formats
at query time).

Word-type classes: TAGNT uses N/K/O (Nestle-Aland / KJV-TR / other
editions) so a single-edition reading can be selected (e.g. NKO words);
TAHOT uses L/Q/K/R/X (Leningrad / Qere / Ketiv / restored / LXX-derived),
with translators normally following L.

### Versification and verse alignment

References use NRSV versification. KJV differences are marked in square
brackets in the reference itself, e.g. `Mat.17.15[17.14]` means NRSV
17:15 equals KJV 17:14; TAHOT marks differing Hebrew refs in brackets.
A documented list of English-verse-start differences is in the TAHOT
header (Num.26.1; 1Sa.21.1; 1Ki.18.33, 20.3, 22.22, 22.43; 1Ch.12.4;
Isa.64.1; Psalm titles as v.0). Curly braces mark Majority-text
placements (e.g. `Rom.16.25{14.24}`); keep TAGNT identity there.

Book codes are 3-letter abbreviations (Mat, Mrk, Luk, Jhn, Act, Rom,
1Co ... Gen, Exo, Lev, Num, Deu, Jos, Jdg, Rut, 1Sa, 2Sa, 1Ki, 2Ki,
1Ch, 2Ch, Ezr, Neh, Est, Job, Psa, Pro, Ecc, Sng, Isa, Jer, Lam, Ezk,
Dan, Hos, Jol, Amo, Oba, Jon, Mic, Nam, Hab, Zep, Hag, Zec, Mal) and map
1:1 onto the book names in the verses table. All 66 books are present:
27 NT, 39 OT.

### Counts (measured from the downloaded files)

- TAGNT: 142,096 word rows; 7,958 distinct verse references; 27 books.
- TAHOT: 305,652 word rows; 23,261 distinct verse references; 39 books.
- Combined: 447,748 word rows across 31,219 verse references.

Row counts include amalgamated variant rows across editions; a
single-edition selection (NKO for TAGNT, L-type for TAHOT) yields fewer
words per verse. Gloss coverage is effectively 100% of word rows (every
row carries an English gloss and a lemma=gloss field).

---

## Candidate 2: Robinson's morphological parsings — CLEAR (public domain), NT only, no glosses

Maurice A. Robinson's Greek New Testament texts with morphological
parsing and Strong's numbers, distributed via the byztxt GitHub
organization (https://github.com/byztxt) and byzantinetext.com.

License evidence:

- `byztxt/byzantine-majority-text` README, Copyright section: "All the
  code and text contained in this folder is in the Public Domain."
- byzantinetext.com describes Robinson's Greek texts as public domain,
  most with morphological parsing and Strong's numbers.
- The Robinson-Pierpont 2005 printed edition's own notice releases all
  rights to everyone ("All rights to this text are released to everyone
  and no one can reduce these rights at any time").
- Independent downstream projects (HELFI corpus, OpenGNT) treat
  Robinson's lemmas and morphology as public domain.

Assessment: rights are clear, but the files carry parsing codes and
Strong's numbers only, no English glosses. Glosses would be joined from
Phos's own Strong's/TBESG lexicons. Robinson's custom storage format and
parsing codes are documented (byztxt/robinson-documentation,
byztxt/librobinson). NT only. Viable fallback for the New Testament if
STEPBible were ever unusable; strictly weaker than TAGNT.

## Candidate 3: Open Scriptures morphhb (OSHB) — CLEAR on rights, functionally weakest

Repository: https://github.com/openscriptures/morphhb.

License evidence (README, verified 2026-09-20): "Lemma and morphology
data are licensed under a Creative Commons Attribution 4.0
International license... The text of the WLC remains in the Public
Domain."

Assessment: rights clear, but word tags carry only `lemma`, `morph`,
and `id` attributes. There are no English glosses and no Strong's
numbers, so glosses would require lossy lemma matching against BDB.
Hebrew only. Weakest of the three; no reason to prefer it over TAHOT.

## Territorial note

CC BY 4.0 is an international license by design and applies worldwide.
The public-domain dedications (Berean Bible 2023, Robinson) were made by
the rights holders without territorial limitation. As with all Phos
sources, keep the standard territorial caveat in public documentation.

## Recommendation

Ingest the interlinear from STEPBible TAHOT/TAGNT under CC BY 4.0 when
Jeremiah approves the build. Suggested ingest shape for the future
build task (not done here):

- Select a single reading per verse: NKO-class words for TAGNT
  (document which edition selector, e.g. SBL-inclusive, is used);
  L-type words for TAHOT with Q/K variants recorded, not merged.
- Use the `sStrong+Instance` plain-Strong's column (strip `_A`/`_B`
  marks) as the join key to the existing lexicon tables.
- Use the TBESG-derived "Dictionary form = Gloss" column as the primary
  gloss; keep the BSB-derived English column as secondary text.
- Exclude the Spanish and sub-meaning columns (unverified provenance).
- Map references to KJV verse keys via the square-bracket notation;
  keep a 3-letter-code to book-name mapping table and record it.
- Carry the CC BY 4.0 attribution (credit STEP Bible, link
  https://www.STEPBible.org, modification log) in the sources table and
  public docs, consistent with the lexicon merge.
- Expected scale: on the order of 300k-450k word rows depending on
  edition filtering, keyed to the existing 31,102 verse keys.
