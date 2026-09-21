"""Shared fixtures: API key must be set before app import (app refuses to
import without PHOS_API_KEY)."""

import os
import sys

os.environ.setdefault("PHOS_API_KEY", "test-key-phos-m2")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import db  # noqa: E402
from app import app  # noqa: E402


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def auth():
    return {"X-API-Key": "test-key-phos-m2"}


@pytest.fixture()
def bounds():
    return db.get_bounds("KJV")
