# Phos API — production image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Application code (flat layout: app.py imports sibling modules db, study, ...)
WORKDIR /srv/phos/api
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api/ .

# Corpora ship as <100MB chunks (GitHub single-file limit); reassemble here.
# The app resolves them as ../data/*.db relative to api/ (see db.py, study.py).
COPY data/dist/ /tmp/dist/
RUN mkdir -p ../data \
 && cat /tmp/dist/study.db.part-* > ../data/study.db \
 && cat /tmp/dist/scripture.db.part-* > ../data/scripture.db \
 && rm -rf /tmp/dist

# progress.db (reading-plan check-ins) is created at runtime under ./data/
# and is ephemeral unless the host mounts a volume there.

EXPOSE 8000

# PHOS_API_KEY must be set in the host environment.
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT} --proxy-headers"]
