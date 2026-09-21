"""Regenerate api/openapi.json from the FastAPI app (OpenAPI 3.1).

Usage:
    PHOS_API_KEY=dummy python gen_openapi.py
"""

import json
from pathlib import Path

from app import app

out = Path(__file__).resolve().parent / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2) + "\n")
print(f"Wrote {out} ({app.openapi_version})")
