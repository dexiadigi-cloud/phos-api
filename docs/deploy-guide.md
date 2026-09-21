# Phos deployment guide

## What the service is

- FastAPI app (`api/app.py`), served by uvicorn.
- Two read-only SQLite corpora baked into the image:
  - `data/study.db` (~442 MB): commentaries, devotionals, lexicons,
    interlinear, liturgy, cross-refs.
  - `data/scripture.db` (~133 MB): verse text for 18 translations.
- One writable SQLite file created at runtime: `api/data/progress.db`
  (reading-plan check-ins). Ephemeral unless the host mounts a volume.
- Auth: single API key in the `X-API-Key` header, read from the
  `PHOS_API_KEY` environment variable. Set it in the host dashboard,
  never in the image.

## HTTPS expectations

HTTPS is required, not optional: the API key travels in a request header
and would be visible on plain HTTP. Both recommended hosts below terminate
TLS automatically with a managed certificate. Do not deploy Phos on a
bare-VM HTTP setup without a reverse proxy providing TLS.

## Hosting options (free tier, no Mac needed)

### Option A: Render (recommended for $0)

- Free tier is permanent: web service from this repo's Dockerfile, $0.
- Set `PHOS_API_KEY` in the dashboard environment variables.
- Automatic HTTPS on `*.onrender.com`.
- Tradeoff: the service sleeps after 15 minutes idle; the first request
  after sleep takes ~30-60 s to wake (cold start with a 650 MB image).
  Fine for personal use; noticeable if the connector is called often.
- Free tier has no persistent disk: progress.db check-ins reset on each
  deploy/restart. Check-ins are anonymous per-device conveniences, so this
  is acceptable.
- Caveat: needs a Render account (Jeremiah's call to create).

### Option B: Fly.io (paid, ~$5/mo minimum)

- Fly.io ended its free tier for new accounts in 2026: new signups get a
  2-hour/7-day trial, then pay-as-you-go from the first machine.
- Better than Render in every technical respect (no cold sleeps, volumes
  for progress.db), but it is not free. Only choose this if the $5/mo is
  approved.

### Not recommended

- Bare VPS without TLS termination (violates the HTTPS requirement).
- Hosts without Docker support (the 575 MB of SQLite corpora must ship
  with the app; object-storage surgery is not worth it).

## Deploy checklist

1. `docker build -t phos .` and smoke-test locally with
   `PHOS_API_KEY=test-key` (expect `/health` green and one verse-study
   call to return).
2. Create the host account (Jeremiah).
3. `fly secrets set PHOS_API_KEY=<long random key>` (or Render dashboard).
   Generate with `openssl rand -hex 32`.
4. Deploy; verify `https://<host>/health` and one authenticated
   `/v1/verse-study/John/3/16` call.
5. Fill in the operator contact + retention decisions in
   `docs/public/privacy-policy.md`, set the terms effective date, and
   complete legal review before announcing the endpoint.
6. Only then mint the Muse custom-connector link
   (`credentials.request_api_access`, provider `phos`, api_hosts
   `[<your host>]`, placement `custom_header:X-API-Key`).

## Retention policy (recommended defaults — Jeremiah approves)

- **Access logs** (uvicorn/host): keep 30 days, then rotate/delete.
  The Phos app itself logs nothing; whatever the host records is the
  operator's responsibility to disclose.
- **progress.db check-ins**: kept until the operator resets the file.
  A check-in is only "day N of plan X from date Y" — no identity attached.
  Recommended: document "deleted on operator reset; no per-user deletion
  possible because check-ins are anonymous."
- No analytics, no cookies, no accounts, no payment data — nothing else
  to retain.
