# Provenance + Commercial-Use Verification — Phos (Dexia Bible API)
**Research date:** 2026-09-20 (PDT)
**Method:** Public-web research only. Official publisher pages fetched as text (browser.open); GitHub repo pages/readmes/license files read directly. No accounts, no contact, no signups. Nothing is legal advice.

**Corpora ingested 2026-09-20:** BSB (GitHub BSB-publishing/bsb2usfm v5.2 USFM zip), KJV (github.com/renniemaharaj/kjv-bible @ commit 88723a4), WEB (getBible v2 web.json), ASV (getBible v2 asv.json), served behind an API from a SQLite DB.

---

## 1. BSB (Berean Standard Bible) — source: BSB-publishing/bsb2usfm, v5.2 USFM release zip

### Sources checked (primary)
- Official Berean Bible Terms and Conditions: http://berean.bible/terms.htm (fetched 2026-09-20; page dated April 30, 2023)
- Official Berean Bible licensing page: https://berean.bible/licensing.htm (quoted verbatim in multiple secondary sources, consistent with terms.htm)
- Repo UNLICENSE: https://github.com/BSB-publishing/bsb2usfm/blob/main/UNLICENSE (fetched 2026-09-20)
- Repo LICENSING_INFO.md: https://github.com/bsb-publishing/bsb2usfm/blob/HEAD/LICENSING_INFO.md (search-indexed)
- v5.2 release notes: https://github.com/BSB-publishing/bsb2usfm/releases/tag/v5.2 (search-indexed)
- Repo README: https://github.com/bsb-publishing/bsb2usfm/blob/HEAD/README.md (search-indexed)

### Operative terms (exact quotes)

**berean.bible/terms.htm (official, current):**
> "The Berean Bible and Majority Bible texts are officially dedicated to the public domain as of April 30, 2023."
> "All uses are freely permitted."
> "Attribution Notice (appreciated but not required): The Holy Bible, Berean Standard Bible, BSB is produced in cooperation with Bible Hub, Discovery Bible, OpenBible.com, and the Berean Bible Translation Committee. This text of God's Word has been dedicated to the public domain."
> "By definition all public domain materials may be freely reproduced, integrated, and adapted for both free and commercial resources."
> "Developers and Publishers are now free to produce and sell the full Berean Bible in any print format."
> "For derivative works that vary from the official text, we respectfully request that the Berean name is not used."

**Repo UNLICENSE:**
> "The Berean Standard Bible (BSB) text contained in this repository is dedicated to the public domain."
> "Anyone is free to copy, modify, publish, use, compile, sell, or distribute the BSB text, either in source code form or as compiled/converted files, for any purpose, commercial or non-commercial, and by any means."

**v5.2 release notes:**
> "Public Domain - Both Bible texts are completely free to use: Copy and distribute freely; Modify and adapt as needed; Use commercially without restriction; No attribution required (though appreciated)"

### Answers to the task's questions
- (a) **Who may use:** anyone; the text is public domain.
- (b) **Commercial use:** explicitly permitted ("free to produce and sell the full Berean Bible in any print format"; "for any purpose, commercial or non-commercial").
- (c) **Attribution:** appreciated but NOT required.
- (d) **Limits:** none legal. One non-binding request: altered derivative texts should not use the "Berean" name (a courtesy request, not a license condition).

### IMPORTANT — premise correction
The task premise ("BSB is NOT public domain; it has its own license") is **outdated**. Pre-2023 BSB materials (e.g. the bereanbible.com front matter "Copyright © 2016, 2020 by Bible Hub. All Rights Reserved... up to 2,000 verses without written permission") reflect the OLD license. On April 30, 2023 the publisher officially dedicated the Berean Bible and Majority Bible texts to the public domain. The current official terms page, the repo UNLICENSE, LICENSING_INFO.md, and the v5.2 release notes all agree: public domain, commercial use allowed, no attribution required. Serving verbatim BSB text labeled "BSB" is within the grant. Only altered derivatives are asked (not required) to drop the Berean name.

### Verdict: **PASS** — (a) free for commercial use: YES; (b) attribution: appreciated, not required; (c) redistribution limits: none (one courtesy naming request for altered derivatives).

---

## 2. KJV (King James Version) — source: github.com/renniemaharaj/kjv-bible @ 88723a4

### Sources checked (primary)
- Repo README at commit 88723a4: https://github.com/renniemaharaj/kjv-bible/blob/HEAD/README.md (fetched 2026-09-20; resolved to commit 88723a44bb3e3f229a34f9cf11ce1b7acf971eee, matching the ingested commit 88723a4)
- Repo root: https://github.com/renniemaharaj/kjv-bible (fetched 2026-09-20)
- UK National Archives, "Centenary of Statutory Crown Copyright": https://cdn.nationalarchives.gov.uk/documents/centenary-crown-copyright-timeline.pdf (search-indexed)

### Operative terms (exact quotes)

**Repo README, "License" section:**
> "This repository is available under the MIT License."

**Repo README, "Acknowledgments":**
> "The King James Version text is in the public domain in many jurisdictions."

**UK National Archives (on Crown copyright):**
> "Book of Common Prayer and King James Bible: These are subject to perpetual protection in the UK (only) under the Royal prerogative. ... These works are out of copyright elsewhere in the world."

### Answers
- (a) **Who may use:** anyone (MIT covers the repo; the KJV text itself is public domain — first published 1611).
- (b) **Commercial use:** permitted. MIT expressly grants "use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies"; the PD text needs no license at all.
- (c) **Attribution:** none legally required for the PD KJV text. If redistributing the repo's files under its MIT grant, standard MIT practice is to include the copyright/permission notice (the README asserts MIT; a standalone LICENSE file was NOT independently viewed — its content was not confirmed).
- (d) **Limits:** none in the US. **UK caveat:** within the UK only, the Authorized (King James) Version remains under perpetual Crown copyright administered by Cambridge University Press (letters patent); commercial publication/distribution aimed at the UK would need their license. Serving from the US: no restriction. The KJV is out of copyright everywhere else in the world (per the UK National Archives source).

### Verdict: **PASS** — (a) free for commercial use: YES (US-served API; text is public domain); (b) attribution: none legally required (MIT notice recommended for the repo files); (c) redistribution limits: none in the US; UK-only perpetual Crown-copyright caveat applies to UK-directed distribution.

---

## 3. WEB (World English Bible) — source: getBible v2 web.json

### Sources checked (primary)
- Official WEB copyright page: https://ebible.org/engwebp/copyright.htm (fetched 2026-09-20; "2020 stable text edition", generated 12 Sep 2026 from source dated 12 Sep 2026)
- Official WEB preface PDF: https://eBible.org/pdf/engwebp/engwebp_FRT.pdf (search-indexed, consistent wording)

### Operative terms (exact quotes)

**ebible.org/engwebp/copyright.htm (official):**
> "The World English Bible is in the Public Domain. That means that it is not copyrighted. However, 'World English Bible' is a Trademark of eBible.org."
> "You may copy, publish, proclaim, distribute, redistribute, sell, give away, quote, memorize, read publicly, broadcast, transmit, share, back up, post on the Internet, print, reproduce, preach, teach from, and use the World English Bible as much as you want, and others may also do so. All we ask is that if you CHANGE the actual text of the World English Bible in any way, you not call the result the World English Bible any more."
> "The Holy Bible is God's Word. It belongs to God. He gave it to us freely, and we who have worked on this translation freely give it to you by dedicating it to the Public Domain."

### Answers
- (a) **Who may use:** anyone — public domain, "not copyrighted".
- (b) **Commercial use:** explicitly permitted ("sell... as much as you want").
- (c) **Attribution:** none required.
- (d) **Limits:** none legal. One condition framed as a request: do not label a CHANGED text "World English Bible" (trademark of eBible.org; serving verbatim WEB as WEB is fine).

### Verdict: **PASS** — (a) free for commercial use: YES; (b) attribution: none required; (c) redistribution limits: none (trademark note: don't call altered text "World English Bible").

---

## 4. ASV (American Standard Version, 1901) — source: getBible v2 asv.json

### Sources checked (primary)
- Official eBible.org ASV copyright page: https://ebible.org/asv/copyright.htm (fetched 2026-09-20; generated 8 Aug 2026 from source dated 8 Aug 2026)

### Operative terms (exact quotes)

**ebible.org/asv/copyright.htm (official):**
> "The American Standard Version of the Holy Bible, first published in 1901."
> "This public domain Bible translation is brought to you courtesy of eBible.org."
> "The American Standard Version of the Holy Bible is in the Public Domain. Copy freely."

### Answers
- (a) **Who may use:** anyone — public domain (first published 1901; US copyright long expired).
- (b) **Commercial use:** permitted ("Copy freely"; PD status carries no commercial restriction).
- (c) **Attribution:** none required.
- (d) **Limits:** none.

### Verdict: **PASS** — (a) free for commercial use: YES; (b) attribution: none required; (c) redistribution limits: none.

---

## 5. getBible v2 (the API/JSON delivery channel) — source of web.json and asv.json

### Sources checked (primary)
- getBible v2 repo README: https://github.com/getbible/v2/blob/HEAD/README.md (fetched 2026-09-20; API documentation, no license/terms section)
- getBible MCP repo README, "Public API access and translation rights": https://github.com/getbible/mcp (search-indexed)

### Operative terms (exact quotes)

**getbible/mcp README (official getBible org):**
> "GetBible API V2 is open worldwide. It requires no registration, account, API key, authentication, subscription, payment, or request quota."
> "Each translation's return data includes its applicable copyright information, including in the translation catalog. Applications must preserve and honor that metadata. GetBible does not add a second copyright layer to scripture text, and this repository's GPL license applies only to the MCP software—it does not relicense translations or override publisher terms."
> "Correct API use is conditioned on honoring the hash-validation cycle described below. An integration that keeps cached scripture without revalidating its hashes is not complying with the GetBible API usage agreement."

### Answers
- getBible imposes **no copyright layer of its own** on the scripture text and **no commercial restriction, fee, registration, or quota**.
- It does require that applications **preserve and honor each translation's own copyright metadata** (for WEB/ASV: public domain — nothing restrictive to honor).
- Usage is conditioned on honoring the documented **hash-validation cycle** for cached scripture. Note: this is a live-API caching condition; for a one-time-downloaded, locally-ingested snapshot, the practical reading is (1) keep the per-translation copyright metadata with the data, and (2) this is a usage agreement, not a copyright restriction. A downstream compliance note should be recorded (see Caveats).
- The GPL license mentioned applies only to the getBible MCP server software, NOT to the translations or JSON payloads.

### Verdict: **PASS (with conditions noted)** — getBible adds no commercial or redistribution restriction of its own. Condition: preserve/honor each translation's copyright metadata; the v2 usage agreement expects hash-validation for cached copies.

---

## Cross-cutting caveats

1. **BSB premise corrected (material):** The "BSB is not public domain" premise predates the April 30, 2023 official public-domain dedication by the publisher. Current official sources are unanimous (PD, commercial OK, attribution optional). Stale front-matter copies with "All Rights Reserved" still circulate; the authoritative current page is berean.bible/terms.htm.
2. **KJV UK Crown copyright:** Perpetual Crown copyright in the UK only (administered by Cambridge University Press). The API serves from the US where the KJV is public domain; no impact on US serving. If Phos ever markets/distributes specifically into the UK, Cambridge's license terms should be checked.
3. **KJV repo MIT file not independently viewed:** The README at the exact ingested commit (88723a4) states "This repository is available under the MIT License," but I did not view a standalone LICENSE file. This is moot for the text itself (PD regardless) but worth a one-line confirmation if the repo's arrangement/markers are redistributed under MIT.
4. **WEB trademark:** "World English Bible" is a trademark of eBible.org. Serving verbatim text as WEB is fine; do not label modified text "World English Bible."
5. **BSB naming request:** Altered derivatives are "respectfully requested" not to use the Berean name. Serving verbatim BSB as BSB complies.
6. **getBible usage agreement:** Recommend the API's translation metadata endpoint carry each translation's copyright/attribution info (per getBible's "preserve and honor that metadata" term), and record that the snapshot was taken from getBible v2 (dates: BSB 2026-09-20, WEB/ASV 2026-09-20).

## Bottom line

All four corpora are clear for a free, commercially-served API from the US:
- **BSB: PASS** — public domain (dedicated 2023-04-30), commercial use allowed, attribution optional.
- **KJV: PASS** — public domain text; repo MIT per README; UK-only Crown-copyright caveat.
- **WEB: PASS** — public domain, sell/redistribute freely; trademark name caveat only.
- **ASV: PASS** — public domain (1901), copy freely.
- **getBible channel: PASS with conditions** — no fees/quotas/copyright layer; must preserve per-translation copyright metadata; hash-validation usage condition for cached copies.

Nothing marked UNVERIFIED. No failures found. Nothing in this research is legal advice.
