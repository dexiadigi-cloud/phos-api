# M1 Provenance Record — Phos (Dexia Bible API)

**Verification date:** 2026-09-20 (America/Los_Angeles)
**Corpus snapshot date:** 2026-09-20 (raw file mtimes 14:23-14:25 PDT)
**Database:** `data/scripture.db` (SQLite, FTS5), built by `scripts/ingest_m1.py`

Research detail with license quotes: `verification/m1/raw/provenance_research.md`.
Raw hashes: `verification/m1/raw/raw_hashes.txt`. getBible metadata: `verification/m1/raw/getbible_metadata.txt`.

## 1. BSB (Berean Standard Bible)
- **Source:** GitHub repo `BSB-publishing/bsb2usfm`, v5.2 USFM release zip.
- **Release URL:** https://github.com/BSB-publishing/bsb2usfm/releases/tag/v5.2
- **Exact asset download URL:** NOT RECORDED (ingest session did not log it). Content is pinned by hash below.
- **Raw files on disk:** `data/raw/BSB_usfm.zip` + extracted `data/raw/bsb_usfm/` (66 `.usfm` files, byte-identical to zip entries, verified).
- **SHA-256 (BSB_usfm.zip):** `0a5782349b81e261c17a77cdf776214dc3cf2adf4ff44232d1aabf76b5303ba1`
- **Version:** v5.2 (publisher release tag).
- **Retrieval date:** 2026-09-20.
- **Rights metadata:** Publisher public-domain dedication. Official page http://berean.bible/terms.htm (dated 2023-04-30, fetched 2026-09-20): "The Berean Bible and Majority Bible texts are officially dedicated to the public domain as of April 30, 2023." / "All uses are freely permitted." / "By definition all public domain materials may be freely reproduced, integrated, and adapted for both free and commercial resources." / "Developers and Publishers are now free to produce and sell the full Berean Bible in any print format." Attribution appreciated but not required. Repo UNLICENSE and v5.2 release notes agree ("Use commercially without restriction; No attribution required").
- **Commercial use:** PASS — public domain since 2023-04-30; commercial use explicitly permitted.
- **Caveats:** Courtesy request (not a license condition): altered derivatives should not use the "Berean" name. Serving verbatim text labeled "BSB" is within the grant.

## 2. KJV (King James Version)
- **Source:** GitHub repo `renniemaharaj/kjv-bible` (git remote: https://github.com/renniemaharaj/kjv-bible).
- **Commit:** `88723a44bb3e3f229a34f9cf11ce1b7acf971eee` ("feat: align KJV corpus and add rendering metadata", 2026-07-30 15:15:57 -0400). Verified from the local git checkout (`data/raw/kjv_src/.git`).
- **Raw files on disk:** `data/raw/kjv_src/` — 66 per-book JSON files + `kjv.json` (aggregate, unused by ingest) + tooling.
- **License metadata in source:** Repo README (at ingested commit) "License" section: "This repository is available under the MIT License." / "The King James Version text is in the public domain in many jurisdictions." NOTE: no standalone LICENSE file exists in the checkout; README assertion only (moot for the PD text itself).
- **Retrieval date:** 2026-09-20.
- **Rights:** KJV text is public domain (first published 1611). MIT (per README) permits commercial redistribution of the repo files.
- **Commercial use:** PASS — no restriction for a US-served API.
- **Caveat:** Within the UK only, the Authorized (King James) Version is under perpetual Crown copyright administered by Cambridge University Press (UK National Archives source). No impact on US serving; revisit only if distributing specifically into the UK.

## 3. WEB (World English Bible)
- **Source:** getBible v2 whole-translation JSON (`web.json`).
- **Exact download URL:** NOT RECORDED (ingest session did not log it). Content pinned by hash; `distribution_version`/`distribution_source` recorded below.
- **Raw file:** `data/raw/web.json` (8,839,233 bytes).
- **SHA-256:** `731ddc05b7570ac0c525a74e4a49d6da4f922aec18e7e982514a4f88432ad1ac`
- **getBible metadata in file:** `translation`="World English Bible", `distribution_license`="Public Domain", `distribution_version`="3.1", `distribution_version_date`="2012-01-25", `distribution_source`="http://ebible.org/web/".
- **Retrieval date:** 2026-09-20.
- **Rights metadata:** Official ebible.org/engwebp/copyright.htm: "The World English Bible is in the Public Domain... You may copy, publish, proclaim, distribute, redistribute, sell, give away... and use the World English Bible as much as you want." (fetched 2026-09-20).
- **Commercial use:** PASS. No attribution required.
- **Caveat:** "World English Bible" is an eBible.org trademark; do not label altered text "World English Bible." Serving verbatim as WEB is fine.

## 4. ASV (American Standard Version, 1901)
- **Source:** getBible v2 whole-translation JSON (`asv.json`).
- **Exact download URL:** NOT RECORDED (same gap as WEB).
- **Raw file:** `data/raw/asv.json` (8,887,731 bytes).
- **SHA-256:** `58c2413d5813d960b7a088825724abb473f39ea320a4be725cf42424357e98c8`
- **getBible metadata in file:** `translation`="American Standard Version", `distribution_license`="Public Domain", `distribution_version`="2.0", `distribution_version_date`="2021-02-18", `distribution_source`="http://www.ebible.org/bible/asv/", `distribution_versification`="KJV".
- **Retrieval date:** 2026-09-20.
- **Rights metadata:** Official ebible.org/asv/copyright.htm: "The American Standard Version of the Holy Bible is in the Public Domain. Copy freely." (fetched 2026-09-20). First published 1901; US copyright long expired.
- **Commercial use:** PASS. No attribution required; no limits.

## 5. getBible v2 (delivery channel for WEB/ASV)
- **Terms:** No registration, API key, payment, or quota. "GetBible does not add a second copyright layer to scripture text." GPL applies only to getBible's MCP server software, not JSON payloads.
- **Conditions:** Applications must preserve/honor each translation's own copyright metadata (WEB/ASV = public domain, nothing restrictive). API use is conditioned on honoring the hash-validation cycle for cached scripture. RECOMMENDATION for M2: serve each translation's copyright metadata from the API (e.g. `GET /v1/translations` includes rights info).

## Gaps (honest)
- Exact download URLs for the BSB v5.2 release asset and the getBible v2 JSON files were not recorded by the ingest session. Content is pinned by SHA-256 hashes above. Record exact URLs on any future re-download.
- KJV repo has no standalone LICENSE file in the checkout; MIT asserted by README at the ingested commit.
- BSB v5.2 is the ingested release; Jeremiah's Dexia Digi BSB was verified against publisher v5.9 — the two have NOT been diffed. Recorded as an open comparison, not a blocker.

*This is research, not legal advice.*
