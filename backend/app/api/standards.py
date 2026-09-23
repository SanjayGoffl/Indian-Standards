"""
Standards API Router.
Provides catalog browsing, search, detail view, and admin seed triggers for Indian Standards.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.models import IndianStandard, CertificationRequirement, StandardRelationship, User
from app.services.standards_knowledge_base import seed_indian_standards
from app.dependencies.auth import get_current_user, get_admin_user

router = APIRouter(prefix="/api/standards", tags=["standards"])


@router.get("")
def list_indian_standards(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Search and filter Indian Standards catalog.
    """
    query = db.query(IndianStandard)

    if category:
        query = query.filter(IndianStandard.category.ilike(f"%{category}%"))

    if sector:
        query = query.filter(IndianStandard.sector.ilike(f"%{sector}%"))

    if search:
        query = query.filter(
            or_(
                IndianStandard.standard_number.ilike(f"%{search}%"),
                IndianStandard.title.ilike(f"%{search}%"),
                IndianStandard.scope.ilike(f"%{search}%")
            )
        )

    standards = query.order_by(IndianStandard.standard_number.asc()).all()

    results = []
    for s in standards:
        results.append({
            "id": s.id,
            "standard_number": s.standard_number,
            "title": s.title,
            "category": s.category,
            "sector": s.sector,
            "revision": s.revision or "Verification required",
            "status": s.status,
            "scope": s.scope[:200] + "..." if s.scope and len(s.scope) > 200 else s.scope
        })

    return {"standards": results, "total": len(results)}


@router.post("/seed")
def trigger_seed_standards(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """
    Admin trigger to seed default Indian Standards catalog.
    Enforces JWT authentication and Admin role.
    """
    res = seed_indian_standards(db)
    return {"message": "Knowledge base seeded successfully.", "details": res}


@router.post("/sync")
def sync_standards_ingestion(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """
    Triggers incremental standards sync via the BIS connector ingestion pipeline.
    Enforces JWT authentication and Admin role.
    """
    from app.services.bis_connector import MockBISConnector
    from app.services.standards_knowledge_base import INITIAL_INDIAN_STANDARDS_SEED
    from app.services.standards_ingestion import ingest_standards

    connector = MockBISConnector(INITIAL_INDIAN_STANDARDS_SEED)
    result = ingest_standards(db, connector)
    return {"message": "Standards sync executed successfully.", "summary": result}


@router.get("/ingest-logs")
def view_ingestion_logs(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """
    Retrieves ingestion pipeline execution history and change detection logs.
    Enforces JWT authentication and Admin role.
    """
    from app.services.standards_ingestion import get_ingestion_logs
    logs = get_ingestion_logs(db)
    return {"logs": logs, "total_runs": len(logs)}


@router.post("/reindex-failed")
def trigger_reindex_failed(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """
    Triggers retry re-indexing of standards with failed/pending vector embeddings in ChromaDB.
    Enforces JWT authentication and Admin role.
    """
    from app.services.standards_ingestion import reindex_pending_embeddings
    res = reindex_pending_embeddings(db)
    return {"message": "Re-index operation completed.", "details": res}


@router.get("/{standard_number:path}")
def get_standard_detail(
    standard_number: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves complete metadata, certifications, and relationships for an Indian Standard.
    """
    std = db.query(IndianStandard).filter(IndianStandard.standard_number == standard_number).first()
    if not std:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Standard {standard_number} not found in knowledge base."
        )

    certs = db.query(CertificationRequirement).filter(CertificationRequirement.standard_id == std.id).all()
    rels = db.query(StandardRelationship).filter(StandardRelationship.standard_id == std.id).all()

    related_list = []
    for r in rels:
        rel_std = db.query(IndianStandard).filter(IndianStandard.id == r.related_standard_id).first()
        if rel_std:
            related_list.append({
                "standard_number": rel_std.standard_number,
                "title": rel_std.title,
                "relationship_type": r.relationship_type,
                "description": r.description
            })

    cert_list = []
    for c in certs:
        cert_list.append({
            "certification_type": c.certification_type,
            "applicability": c.applicability,
            "source_url": c.source_url,
            "verification_status": c.verification_status
        })

    return {
        "id": std.id,
        "standard_number": std.standard_number,
        "title": std.title,
        "scope": std.scope,
        "category": std.category,
        "sector": std.sector,
        "publication_date": std.publication_date,
        "revision": std.revision,
        "amendment_details": std.amendment_details,
        "status": std.status,
        "source_url": std.source_url,
        "evidence_text": std.evidence_text,
        "certifications": cert_list,
        "related_standards": related_list
    }

