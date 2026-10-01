# Phos - Dexia Bible API (Phos Intensive Verse Study)

☕ [Support on Ko-fi](https://ko-fi.com/dexiadigi)

Public-domain Scripture API: 17 translations, a verse-study endpoint
(text, cross-references, interlinear hooks, prayer matching), reading
plans, and a single API-key auth scheme.

## Deploy (Render, free tier)

1. Render dashboard: New -> Blueprint, connect this repo.
2. Enter `PHOS_API_KEY` when prompted (generate one: `openssl rand -hex 32`).
3. Deploy. Health check: `GET /v1/health`.

See `docs/deploy-guide.md` for details and alternatives.

## Local dev

```bash
cd api && PHOS_API_KEY=dev uvicorn app:app --reload
```

Tests: `cd api && python -m pytest` (220 passed as of 2026-09-21).

## Endpoints

- `GET /v1/verse-study/{book}/{chapter}/{verse}` - full study bundle
- `GET /v1/interlinear/{book}/{chapter}/{verse}` - interlinear data
- `GET /v1/health` - health check

Auth: `X-API-Key` header. Full spec: `docs/design/verse-study-spec.md`,
OpenAPI: `api/openapi.json`.

## License

CC0 1.0 Universal (public domain). See `LICENSE`.
Scripture data: public-domain translations; per-translation verification
in `verification/v2/translation-audit-20260920.md`.
