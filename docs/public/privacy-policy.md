# Privacy Policy (Template)

**This is a template, not legal advice.** It was drafted from what the Phos API actually does as of 2026-09-20. [LEGAL REVIEW] It has not been reviewed by a lawyer. Do not publish it until it has been.

Phos is a free Bible-text API. This policy explains what information Phos handles when you use the API, and what it does not handle. If you are the operator deploying this API, [JEREMIAH: fill in the operator contact details below] you are responsible for telling your API users what extra logging your own deployment performs.

## What Phos does

Phos serves public-domain Bible text (BSB, KJV, WEB, ASV, and other public-domain translations) from a local SQLite corpus. Every response is scripture text or public-domain study material. No user accounts exist, no sign-up is possible, and no personal profiles are created.

## What is collected

**The API key.** Phos authenticates requests with a single shared key sent in the `X-API-Key` header. The key is compared in constant time against the `PHOS_API_KEY` environment variable on the server. Because one key is shared, a request cannot be tied to a specific person, account, or device. Phos has no way to know who you are from the key alone.

**Reading-plan check-ins.** The check-in endpoint (`POST /v1/reading-plans/{plan_id}/checkin`) records a checkmark in `data/progress.db` keyed only by plan ID and start date. A checkmark records that "day N of plan X starting on date Y was completed." It records no name, no email, no device identifier, and no scripture text.

**Request logs, if the operator keeps them.** The Phos application code itself does no request logging. The server process that runs Phos (for example, uvicorn) may write access logs that include the client's IP address and request path. Whether those logs exist, how long they are kept, and who can see them is entirely the operator's deployment choice - Phos does not set it. [JEREMIAH: decide whether your deployment keeps uvicorn access logs, and for how long; write that here.]

## What is NOT collected

- **No user accounts.** There is no registration, no login, no passwords, and no profile data of any kind.
- **No tracking cookies.** Phos is an API, not a website, and sets no cookies.
- **No analytics on users.** Phos does not track who you are, what you read, or how often you read it. Reading content - passages, searches, verse of the day, devotionals - leaves no record on the server at all. Only explicit check-ins create a record, and that record is just a checkmark.
- **No payment data.** Phos is free; no payment information is ever requested or stored.
- **No advertising.** No ads are served and no data is collected for advertising.

## Data retention

Checkmarks in `data/progress.db` persist until the operator deletes or resets the database file. [JEREMIAH: decide a retention policy for progress.db - e.g., deleted on request, rotated monthly, kept indefinitely - and write it here.] Access logs, if the operator keeps them, are governed by the operator's own log rotation policy.

## Security

The API key travels in the `X-API-Key` request header. [LEGAL REVIEW] Users of a hosted Phos instance should confirm with the operator that the API is served over HTTPS so the key is not transmitted in clear text. The server stores the expected key in the `PHOS_API_KEY` environment variable, never in the codebase or database.

## Children's privacy

Phos collects no personal information from anyone, including children. There are no accounts and no way to submit personal data through the API. [LEGAL REVIEW] If you embed Phos in a children's product (such as the Dexia Digi workbooks), the product's own privacy policy - not this one - governs what that product collects.

## International users

Because Phos collects no personal data, there is no personal data to transfer, store, or process across borders. [LEGAL REVIEW] If the operator keeps access logs containing IP addresses, note here which jurisdictions' rules apply.

## Changes to this policy

[LEGAL REVIEW] Decide where policy updates will be announced (e.g., a changelog in the docs) and how long before they take effect. Until that is decided, this section is a placeholder: material changes will be posted here with their effective date.

## Contact

Operator contact for privacy questions and data deletion requests:
dexiadigi@gmail.com

---

*Template prepared 2026-09-20 from the Phos v1 API source. Review date: [JEREMIAH: set a review date, e.g., annually].*
