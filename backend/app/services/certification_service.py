"""
Certification Service Module.
Identifies BIS Product Certification (ISI Mark), Compulsory Registration Scheme (CRS),
Hallmarking, and Quality Control Orders (QCO) for recommended Indian Standards.
Enforces evidence-backed certification guidance and anti-hallucination notices.
"""

import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.core.models import IndianStandard, CertificationRequirement

logger = logging.getLogger(__name__)

from datetime import datetime, timezone
from app.services.recommendation_validator import UNSUPPORTED_QCO_EXPLANATION, get_safe_cert_explanation


def resolve_certification_requirements(db: Session, standard_number: str) -> List[Dict[str, Any]]:
    """
    Looks up official certification schemes (ISI, CRS, Hallmarking) associated with an Indian Standard.
    Returns structured certification evidence objects with traceable evidence sources and provenance fields.
    Defaults status to 'Verification Required' unless backed by verified Gazette QCO proof.
    """
    certifications = []

    std = db.query(IndianStandard).filter(IndianStandard.standard_number == standard_number).first()
    std_cat = std.category if std else "General Procurement"
    std_num = std.standard_number if std else standard_number
    safe_explanation = UNSUPPORTED_QCO_EXPLANATION

    db_certs = db.query(CertificationRequirement).filter(CertificationRequirement.standard_id == std.id).all() if std else []
    now_iso = datetime.now(timezone.utc).isoformat()
    
    if db_certs:
        for c in db_certs:
            has_full_qco = bool(
                getattr(c, "notification_number", None) and
                getattr(c, "issuing_authority", None) and
                getattr(c, "effective_date", None) and
                getattr(c, "scope_or_exclusions", None) and
                c.verification_status == "Verified"
            )
            status_label = "Confirmed Applicable" if has_full_qco else "Verification Required"
            explanation = c.explanation if (has_full_qco and c.explanation) else safe_explanation

            src_url = c.source_url if (has_full_qco and c.source_url) else None

            certifications.append({
                "certification_type": c.certification_type or "BIS Product Certification / ISI Mark",
                "applicability": status_label,
                "product_category": std.category or "General Procurement" if std else "General Procurement",
                "relevant_is_number": std.standard_number if std else standard_number,
                "regulatory_instrument": c.verification_status or "Quality Control Order (QCO) - Verification Required",
                "evidence_source": src_url,
                "evidence_date": "Verified in DB" if has_full_qco else "Unverified",
                "effective_date": getattr(c, "effective_date", "Unverified"),
                "verification_status": "Verified by Official Gazette" if has_full_qco else "Verification Required",
                "explanation": explanation,
                "evidence_text": explanation,
                "disclaimer": "Official Gazette notification and product scope verification required prior to tender publication.",
                "source": "Official Gazette Notification" if has_full_qco else "Local BIS Catalogue",
                "source_url": src_url,
                "source_document": getattr(c, "notification_number", None) or "Local Catalogue Record",
                "page_or_clause": "Clause verification required",
                "retrieved_at": now_iso,
                "provenance": {
                    "source": "Official Gazette Notification" if has_full_qco else "Local BIS Catalogue",
                    "source_url": src_url,
                    "source_document": getattr(c, "notification_number", None) or "Local Catalogue Record",
                    "page_or_clause": "Clause verification required",
                    "retrieved_at": now_iso,
                    "verification_status": "Verified by Official Gazette" if has_full_qco else "Verification Required"
                }
            })
    else:
        certifications.append({
            "certification_type": "BIS Product Certification / ISI Mark",
            "applicability": "Verification Required",
            "product_category": std.category if std else "General Procurement",
            "relevant_is_number": std.standard_number if std else standard_number,
            "regulatory_instrument": "Quality Control Order (QCO) - Verification Required",
            "evidence_source": None,
            "evidence_date": "Unverified",
            "effective_date": "Unverified",
            "verification_status": "Verification Required",
            "explanation": safe_explanation,
            "evidence_text": safe_explanation,
            "disclaimer": "Official Gazette verification required prior to tender publication.",
            "source": std.source if std else "Local BIS Catalogue",
            "source_url": None,
            "source_document": "Local Catalogue Record",
            "page_or_clause": "Clause verification required",
            "retrieved_at": now_iso,
            "provenance": {
                "source": std.source if std else "Local BIS Catalogue",
                "source_url": None,
                "source_document": "Local Catalogue Record",
                "page_or_clause": "Clause verification required",
                "retrieved_at": now_iso,
                "verification_status": "Verification Required"
            }
        })

    return certifications


