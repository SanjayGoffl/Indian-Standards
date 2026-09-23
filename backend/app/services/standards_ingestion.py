"""
Scalable BIS Standards Ingestion Pipeline & Audit Logger.
Handles incremental ingestion, SHA-256 change detection, PostgreSQL relational updates,
selective ChromaDB vector store re-indexing, invalid record error logging, and PostgreSQL audit persistence.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.core.models import IndianStandard, StandardRelationship, CertificationRequirement, IngestionAuditLog
from app.rag.chromadb_service import chroma_service
from app.services.bis_connector import BISConnectorInterface, compute_content_hash

logger = logging.getLogger(__name__)


def validate_standard_record(item: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validates mandatory fields on incoming BIS standard records.
    """
    std_num = item.get("standard_number")
    title = item.get("title")

    if not std_num or not isinstance(std_num, str) or len(std_num.strip()) == 0:
        return False, "Missing or empty standard_number"
    if not title or not isinstance(title, str) or len(title.strip()) == 0:
        return False, f"Missing or empty title for standard_number '{std_num}'"

    return True, ""


def ingest_standards(db: Session, connector: BISConnectorInterface) -> Dict[str, Any]:
    """
    Ingests standards using a connector interface.
    Applies change detection so only new or modified standards update DB & ChromaDB.
    Persists IngestionAuditLog in PostgreSQL for administrative governance.
    """
    ingestion_id = f"ingest-{uuid.uuid4().hex[:8]}"
    start_dt = datetime.now(timezone.utc)
    source_meta = connector.get_source_metadata()
    source_name = source_meta.get("source_type", "Unknown Source")

    records = connector.fetch_standards()

    new_count = 0
    updated_count = 0
    unchanged_count = 0
    failed_count = 0
    embeddings_created = 0
    embeddings_updated = 0
    error_logs: List[str] = []

    collection = None
    try:
        collection = chroma_service.get_or_create_collection("indian_standards_kb")
    except Exception as e:
        logger.warning(f"ChromaDB collection initialization warning: {str(e)}")

    standard_map: Dict[str, IndianStandard] = {}

    for item in records:
        is_valid, err_msg = validate_standard_record(item)
        if not is_valid:
            failed_count += 1
            error_logs.append(err_msg)
            logger.warning(f"Invalid BIS record rejected: {err_msg}")
            continue

        std_number = item["standard_number"].strip()
        new_hash = item.get("content_hash") or compute_content_hash(item)

        existing = db.query(IndianStandard).filter(IndianStandard.standard_number == std_number).first()

        needs_vector_update = False
        is_new = False

        if not existing:
            standard = IndianStandard(
                standard_number=std_number,
                title=item.get("title", "Untitled Standard"),
                scope=item.get("scope", ""),
                technical_requirements=item.get("technical_requirements", ""),
                category=item.get("product_category") or item.get("category") or "General",
                sector=item.get("sector", "General Sector"),
                publication_date=item.get("revision_year") or item.get("publication_date"),
                revision=item.get("revision_year") or item.get("revision") or "Active",
                amendment_details=item.get("amendment_information") or item.get("amendment_details"),
                status=item.get("status", "Active"),
                source=item.get("source", source_name),
                source_url=item.get("source_url"),
                retrieved_at=item.get("retrieved_at"),
                verification_status=item.get("verification_status", "Verification Required"),
                evidence_text=item.get("evidence_text") or item.get("scope", ""),
                content_hash=new_hash,
            )
            db.add(standard)
            db.flush()
            standard_map[std_number] = standard
            new_count += 1
            is_new = True
            needs_vector_update = True
        else:
            # Change detection using content_hash
            if existing.content_hash != new_hash:
                existing.title = item.get("title", existing.title)
                existing.scope = item.get("scope", existing.scope)
                existing.technical_requirements = item.get("technical_requirements", existing.technical_requirements)
                existing.category = item.get("product_category") or item.get("category", existing.category)
                existing.sector = item.get("sector", existing.sector)
                existing.publication_date = item.get("revision_year", existing.publication_date)
                existing.revision = item.get("revision_year", existing.revision)
                existing.amendment_details = item.get("amendment_information", existing.amendment_details)
                existing.status = item.get("status", existing.status)
                existing.source_url = item.get("source_url", existing.source_url)
                existing.retrieved_at = item.get("retrieved_at", existing.retrieved_at)
                existing.verification_status = item.get("verification_status", existing.verification_status)
                existing.evidence_text = item.get("evidence_text", existing.evidence_text)
                existing.content_hash = new_hash

                standard_map[std_number] = existing
                updated_count += 1
                needs_vector_update = True
            else:
                standard_map[std_number] = existing
                unchanged_count += 1

        db.commit()

        std_obj = standard_map[std_number]

        # Sync Certifications
        for cert in item.get("certifications", []):
            cert_type = cert.get("certification_type", "Standard Verification")
            existing_cert = db.query(CertificationRequirement).filter(
                CertificationRequirement.standard_id == std_obj.id,
                CertificationRequirement.certification_type == cert_type
            ).first()
            if not existing_cert:
                cert_obj = CertificationRequirement(
                    standard_id=std_obj.id,
                    certification_type=cert_type,
                    applicability=cert.get("applicability", "Mandatory"),
                    source_url=cert.get("source_url"),
                    verification_status=cert.get("verification_status", "Verification Required")
                )
                db.add(cert_obj)
        db.commit()

        # Update ChromaDB vector index strictly if new or updated
        if needs_vector_update and collection is not None:
            text_for_embedding = (
                f"Standard Number: {std_number}\n"
                f"Title: {item.get('title', '')}\n"
                f"Category: {item.get('product_category') or item.get('category', '')}\n"
                f"Sector: {item.get('sector', '')}\n"
                f"Scope: {item.get('scope', '')}\n"
                f"Technical Specifications: {item.get('technical_requirements', '')}"
            )
            doc_id = std_number.replace(" ", "_").replace("/", "_").replace(":", "_")
            try:
                collection.upsert(
                    documents=[text_for_embedding],
                    metadatas=[{
                        "standard_number": std_number,
                        "title": item.get("title", ""),
                        "category": item.get("product_category") or item.get("category", ""),
                        "sector": item.get("sector", ""),
                        "revision": item.get("revision_year") or item.get("revision", ""),
                        "status": item.get("status", "Active"),
                        "content_hash": new_hash
                    }],
                    ids=[doc_id]
                )
                if is_new:
                    embeddings_created += 1
                else:
                    embeddings_updated += 1
            except Exception as e:
                logger.warning(f"ChromaDB upsert failed for {std_number}: {str(e)}")

    # Sync Relationships
    for item in records:
        std_number = item.get("standard_number")
        parent_std = standard_map.get(std_number)
        if not parent_std:
            continue

        for rel in item.get("relationships", []):
            rel_std_number = rel.get("related_standard_number")
            rel_type = rel.get("relationship_type", "related_product")
            if not rel_std_number:
                continue

            rel_std = db.query(IndianStandard).filter(
                IndianStandard.standard_number.like(f"%{rel_std_number}%")
            ).first()

            if rel_std and rel_std.id != parent_std.id:
                existing_rel = db.query(StandardRelationship).filter(
                    StandardRelationship.standard_id == parent_std.id,
                    StandardRelationship.related_standard_id == rel_std.id,
                    StandardRelationship.relationship_type == rel_type
                ).first()

                if not existing_rel:
                    rel_obj = StandardRelationship(
                        standard_id=parent_std.id,
                        related_standard_id=rel_std.id,
                        relationship_type=rel_type,
                        description=rel.get("description"),
                        source_evidence=rel.get("source_evidence", "Derived from catalog metadata"),
                        verification_status=rel.get("verification_status", "Verification Required")
                    )
                    db.add(rel_obj)
    db.commit()

    end_dt = datetime.now(timezone.utc)
    audit_status = "completed" if failed_count == 0 else ("completed_with_errors" if new_count + updated_count > 0 else "failed")

    audit_log = IngestionAuditLog(
        ingestion_id=ingestion_id,
        source_name=source_name,
        start_time=start_dt,
        end_time=end_dt,
        total_records=len(records),
        new_records=new_count,
        updated_records=updated_count,
        unchanged_records=unchanged_count,
        failed_records=failed_count,
        embeddings_created=embeddings_created,
        embeddings_updated=embeddings_updated,
        status=audit_status,
        error_summary="; ".join(error_logs) if error_logs else None,
    )
    db.add(audit_log)
    db.commit()

    summary = {
        "ingestion_id": ingestion_id,
        "status": audit_status,
        "source": source_name,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "total_records": len(records),
        "new_records": new_count,
        "updated_records": updated_count,
        "unchanged_records": unchanged_count,
        "failed_records": failed_count,
        "embeddings_created": embeddings_created,
        "embeddings_updated": embeddings_updated,
        "error_summary": error_logs,
        "total_in_db": db.query(IndianStandard).count()
    }

    logger.info(f"Ingestion {ingestion_id} finished: {summary}")
    return summary


def get_ingestion_logs(db: Session) -> List[Dict[str, Any]]:
    """
    Retrieves ingestion audit logs from database.
    """
    logs = db.query(IngestionAuditLog).order_by(IngestionAuditLog.start_time.desc()).limit(50).all()
    results = []
    for l in logs:
        results.append({
            "id": l.id,
            "ingestion_id": l.ingestion_id,
            "source_name": l.source_name,
            "start_time": l.start_time.isoformat() if l.start_time else None,
            "end_time": l.end_time.isoformat() if l.end_time else None,
            "total_records": l.total_records,
            "new_records": l.new_records,
            "updated_records": l.updated_records,
            "unchanged_records": l.unchanged_records,
            "failed_records": l.failed_records,
            "embeddings_created": l.embeddings_created,
            "embeddings_updated": l.embeddings_updated,
            "status": l.status,
            "error_summary": l.error_summary,
        })
    return results
