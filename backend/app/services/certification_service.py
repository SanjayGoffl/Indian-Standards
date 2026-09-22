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

from app.services.recommendation_validator import get_safe_cert_explanation


def resolve_certification_requirements(db: Session, standard_number: str) -> List[Dict[str, Any]]:
    """
    Looks up official certification schemes (ISI, CRS, Hallmarking) associated with an Indian Standard.
    Returns structured 10-field certification evidence objects with traceable evidence sources.
    Defaults status to 'Verification Required' unless backed by verified Gazette QCO proof.
    """
    certifications = []

    std = db.query(IndianStandard).filter(IndianStandard.standard_number == standard_number).first()
    std_cat = std.category if std else "General Procurement"
    std_num = std.standard_number if std else standard_number
    safe_explanation = get_safe_cert_explanation(std_cat)

    if not std:
        return [
            {
                "certification_type": "BIS Product Certification / ISI Mark",
                "applicability": "Verification Required",
                "product_category": std_cat,
                "relevant_is_number": std_num,
                "regulatory_instrument": "Quality Control Order (QCO) - Verification Pending",
                "evidence_source": "https://www.bis.gov.in/",
                "evidence_date": "Unverified",
                "effective_date": "Unverified",
                "verification_status": "Verification Required",
                "explanation": safe_explanation,
                "evidence_text": safe_explanation,
                "disclaimer": "Official Gazette verification required prior to tender publication.",
                "source_url": "https://www.bis.gov.in/"
            }
        ]

    db_certs = db.query(CertificationRequirement).filter(CertificationRequirement.standard_id == std.id).all()
    
    if db_certs:
        for c in db_certs:
            has_gazette_proof = bool(c.verification_status and "Official Gazette QCO Notification" in c.verification_status)
            status_label = "Confirmed Applicable" if has_gazette_proof else "Verification Required"
            explanation = std.evidence_text if (std.evidence_text and has_gazette_proof) else safe_explanation

            certifications.append({
                "certification_type": c.certification_type or "BIS Product Certification / ISI Mark",
                "applicability": status_label,
                "product_category": std.category or "General Procurement",
                "relevant_is_number": std.standard_number,
                "regulatory_instrument": c.verification_status or "Quality Control Order (QCO) - Verification Required",
                "evidence_source": c.source_url or std.source_url or "https://www.bis.gov.in/",
                "evidence_date": "Verified in DB" if has_gazette_proof else "Unverified",
                "effective_date": "Verified in DB" if has_gazette_proof else "Unverified",
                "verification_status": "Verified by Official Gazette" if has_gazette_proof else "Verification Required",
                "explanation": explanation,
                "evidence_text": explanation,
                "disclaimer": "Official Gazette notification and product scope verification required prior to tender publication.",
                "source_url": c.source_url or std.source_url or "https://www.bis.gov.in/"
            })
    else:
        certifications.append({
            "certification_type": "BIS Product Certification / ISI Mark",
            "applicability": "Verification Required",
            "product_category": std.category or "General Procurement",
            "relevant_is_number": std.standard_number,
            "regulatory_instrument": "Quality Control Order (QCO) - Verification Required",
            "evidence_source": std.source_url or "https://www.bis.gov.in/",
            "evidence_date": "Unverified",
            "effective_date": "Unverified",
            "verification_status": "Verification Required",
            "explanation": safe_explanation,
            "evidence_text": safe_explanation,
            "disclaimer": "Official Gazette verification required prior to tender publication.",
            "source_url": std.source_url or "https://www.bis.gov.in/"
        })

    return certifications


