"""
Automated Security, Role Authorization, and Ingestion Hardening Test Suite.
Verifies:
1. Unauthenticated requests to admin endpoints return 401.
2. Authenticated non-admin requests return 403 Forbidden.
3. Authenticated admin requests are allowed.
4. Blocked/disabled users are rejected with 403 Forbidden.
5. Canonical standard identifier normalization.
6. Re-indexing retry endpoint functionality.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal, engine, Base
from app.core.models import User, IndianStandard
from app.core.auth import create_access_token
from app.services.bis_connector import parse_standard_number, normalize_bis_record
from app.services.standards_ingestion import reindex_pending_embeddings

client = TestClient(app)


def test_canonical_standard_identifier_parsing():
    """Verify standard number normalization and canonical parsing logic."""
    p1 = parse_standard_number("IS 4984")
    assert p1["base_standard_number"] == "IS 4984"
    assert p1["canonical_standard_number"] == "IS 4984"

    p2 = parse_standard_number("IS 7098 (Part 1):1988")
    assert p2["base_standard_number"] == "IS 7098"
    assert p2["part_number"] == "Part 1"
    assert p2["revision_year"] == "1988"
    assert p2["canonical_standard_number"] == "IS 7098 (Part 1):1988"

    rec = normalize_bis_record({"standard_number": "IS 4984:2016", "title": "HDPE Pipe Spec"})
    assert rec["canonical_standard_number"] == "IS 4984:2016"
    assert rec["base_standard_number"] == "IS 4984"


def test_unauthenticated_admin_endpoints_rejected():
    """Verify 401 Unauthorized for unauthenticated requests to admin routes."""
    res_sync = client.post("/api/standards/sync")
    assert res_sync.status_code == 401

    res_seed = client.post("/api/standards/seed")
    assert res_seed.status_code == 401

    res_logs = client.get("/api/standards/ingest-logs")
    assert res_logs.status_code == 401

    res_reindex = client.post("/api/standards/reindex-failed")
    assert res_reindex.status_code == 401


def test_non_admin_user_admin_endpoints_forbidden():
    """Verify 403 Forbidden for non-admin users attempting admin routes."""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "normal_user@example.com").first()
        if not user:
            user = User(
                email="normal_user@example.com",
                full_name="Normal User",
                password_hash="hashed_pw",
                role="User",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        token = create_access_token(str(user.id))
        headers = {"Authorization": f"Bearer {token}"}

        res_sync = client.post("/api/standards/sync", headers=headers)
        assert res_sync.status_code == 403
        assert "Administrative privileges" in res_sync.json()["detail"]

        res_seed = client.post("/api/standards/seed", headers=headers)
        assert res_seed.status_code == 403

        res_logs = client.get("/api/standards/ingest-logs", headers=headers)
        assert res_logs.status_code == 403

        res_reindex = client.post("/api/standards/reindex-failed", headers=headers)
        assert res_reindex.status_code == 403
    finally:
        db.close()


def test_admin_user_admin_endpoints_allowed():
    """Verify 200 OK for authenticated admin users on admin routes."""
    db: Session = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin_user@example.com").first()
        if not admin:
            admin = User(
                email="admin_user@example.com",
                full_name="Admin User",
                password_hash="hashed_pw",
                role="Admin",
                is_active=True
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        token = create_access_token(str(admin.id))
        headers = {"Authorization": f"Bearer {token}"}

        res_logs = client.get("/api/standards/ingest-logs", headers=headers)
        assert res_logs.status_code == 200
        assert "logs" in res_logs.json()

        res_reindex = client.post("/api/standards/reindex-failed", headers=headers)
        assert res_reindex.status_code == 200
        assert "Re-index operation completed." in res_reindex.json()["message"]
    finally:
        db.close()


def test_disabled_user_rejected():
    """Verify 403 Forbidden for disabled users on protected endpoints."""
    db: Session = SessionLocal()
    try:
        disabled_user = db.query(User).filter(User.email == "disabled_user@example.com").first()
        if not disabled_user:
            disabled_user = User(
                email="disabled_user@example.com",
                full_name="Disabled User",
                password_hash="hashed_pw",
                role="User",
                is_active=False
            )
            db.add(disabled_user)
            db.commit()
            db.refresh(disabled_user)

        token = create_access_token(str(disabled_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        res = client.get("/api/standards/ingest-logs", headers=headers)
        assert res.status_code == 403
        assert "blocked" in res.json()["detail"]
    finally:
        db.close()

