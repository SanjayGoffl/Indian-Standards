"""
Master Recommendation Service.
Orchestrates procurement requirement extraction, hybrid standards retrieval, applicability scoring,
technical Field Comparison Matrix validation, excluded standards filtering, certification guidance, and PostgreSQL persistence.
"""

import json
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.models import ProcurementRequest, Recommendation, IndianStandard
from app.services.requirement_analyzer import extract_procurement_requirements
from app.services.standards_retrieval import retrieve_candidate_standards
from app.services.applicability_engine import evaluate_standards_applicability
from app.services.certification_service import resolve_certification_requirements
from app.services.version_verification import verify_standard_version_details
from app.services.standards_knowledge_base import seed_indian_standards
from app.services.recommendation_validator import OFFICIAL_SCORE_DISCLAIMER, normalize_standard_number, sanitize_and_validate_report

logger = logging.getLogger(__name__)


def process_procurement_recommendation(
    db: Session,
    user_id: str,
    input_text: str = None,
    uploaded_file_path: str = None,
    extracted_doc_text: str = None,
    product_category: str = None,
    procurement_purpose: str = None
) -> Dict[str, Any]:
    """
    Executes the full AI recommendation workflow for procurement specifications.
    Assembles complete 10-part report structure with Field Comparison Matrix, Excluded Standards, and 0 duplicates.
    """
    # Seed knowledge base if empty
    existing_count = db.query(IndianStandard).count()
    if existing_count == 0:
        seed_indian_standards(db)

    # 1. Combine specification text
    combined_text = ""
    if input_text:
        combined_text += input_text.strip() + "\n"
    if extracted_doc_text:
        combined_text += extracted_doc_text.strip() + "\n"

    if not combined_text.strip():
        combined_text = f"Procurement request for product category: {product_category or 'General Product'}"

    # 2. Extract structured technical parameters
    extracted_data = extract_procurement_requirements(
        input_text=combined_text,
        user_category=product_category,
        user_purpose=procurement_purpose
    )

    inferred_category = extracted_data.get("product_category") or product_category or "Electrical Wires & Power Cables"

    # 3. Retrieve candidate Indian Standards
    candidates = retrieve_candidate_standards(
        db=db,
        query_text=combined_text,
        product_category=inferred_category,
        top_k=6
    )

    # Deduplicate candidates by normalized standard number
    unique_candidates = []
    seen_cand_nums = set()
    for cand in candidates:
        norm = normalize_standard_number(cand.standard_number)
        if norm not in seen_cand_nums:
            seen_cand_nums.add(norm)
            unique_candidates.append(cand)

    # 4. Evaluate applicability & filter excluded standards using Field Comparison Matrix
    evaluated_recommendations, excluded_standards = evaluate_standards_applicability(
        db=db,
        candidate_standards=unique_candidates,
        extracted_data=extracted_data,
        procurement_purpose=procurement_purpose
    )

    # 5. Separate standards into recommended vs. potentially applicable & collect certifications/allied
    recommended_list = []
    potentially_applicable_list = []
    seen_applicable_nums = set()

    related_standards_list = []
    seen_rel_nums = set()

    certification_guidance_list = []
    seen_cert_keys = set()

    warnings_list = extracted_data.get("missing_or_ambiguous_specs", [])
    sources_set = set()

    for item in evaluated_recommendations:
        std_num = item["standard_number"]
        norm_std_num = normalize_standard_number(std_num)

        if norm_std_num in seen_applicable_nums:
            continue
        seen_applicable_nums.add(norm_std_num)

        # Resolve certifications
        certs = resolve_certification_requirements(db, std_num)
        item["certification_requirements"] = certs
        for c in certs:
            cert_type = c.get("certification_type", "BIS Product Certification / ISI Mark")
            if cert_type not in seen_cert_keys:
                seen_cert_keys.add(cert_type)
                certification_guidance_list.append(c)

        # Collect allied standards
        for rel in item.get("related_standards", []):
            rel_norm = normalize_standard_number(rel["standard_number"])
            if rel_norm not in seen_rel_nums and rel_norm not in seen_applicable_nums:
                seen_rel_nums.add(rel_norm)
                related_standards_list.append(rel)

        # Version verification
        std_obj = db.query(IndianStandard).filter(IndianStandard.standard_number == std_num).first()
        has_catalog_sync = False  # Set to False until official live API sync is available

        ver_info = verify_standard_version_details(
            standard_number=std_num,
            raw_revision=item.get("latest_revision"),
            amendment_details=",".join(item.get("amendments", [])),
            has_catalog_sync=has_catalog_sync
        )
        item["latest_revision"] = ver_info["latest_revision"]
        item["revision_verification_status"] = ver_info["revision_verification_status"]
        if ver_info["verification_required"]:
            item["verification_required"] = True

        if std_obj and std_obj.source_url:
            sources_set.add(f"{std_num}: {std_obj.source_url}")

        # Separate Recommended from Potentially Applicable / Related
        if item["applicability_status"] == "Recommended":
            recommended_list.append(item)
        else:
            potentially_applicable_list.append(item)

    # Clean deduplication of excluded standards
    deduped_excluded = []
    seen_ex_nums = set()
    for ex in excluded_standards:
        ex_norm = normalize_standard_number(ex["standard_number"])
        if ex_norm not in seen_ex_nums and ex_norm not in seen_applicable_nums:
            seen_ex_nums.add(ex_norm)
            deduped_excluded.append(ex)

    # 6. Build dedicated Standards Requiring Official Verification section
    standards_requiring_verification = []
    seen_ver_nums = set()
    for item in (recommended_list + potentially_applicable_list):
        std_num = item["standard_number"]
        norm_std_num = normalize_standard_number(std_num)

        # Do not include standards that are excluded due to category mismatch
        if any(normalize_standard_number(ex["standard_number"]) == norm_std_num for ex in deduped_excluded):
            continue

        if norm_std_num not in seen_ver_nums:
            seen_ver_nums.add(norm_std_num)
            std_obj = db.query(IndianStandard).filter(IndianStandard.standard_number == std_num).first()
            src_url = std_obj.source_url if (std_obj and std_obj.source_url) else f"https://www.bis.gov.in/index.php/standard-search/?std_no={std_num}"
            
            standards_requiring_verification.append({
                "standard_number": std_num,
                "title": item["title"],
                "verification_status": "Verification required from the official BIS standard document.",
                "source_url": src_url
            })

    # Ensure missing_requirements contains ONLY technical details (no standard numbers or verification warnings)
    clean_missing_requirements = [
        item for item in warnings_list
        if "VERIFICATION REQUIRED" not in item.upper() and "STANDARD IS " not in item.upper() and "REVISION" not in item.upper()
    ]

    # Create ProcurementRequest in PostgreSQL
    proc_request = ProcurementRequest(
        user_id=user_id,
        input_text=input_text,
        uploaded_file_path=uploaded_file_path,
        extracted_text=extracted_doc_text or combined_text,
        product_category=inferred_category,
        procurement_purpose=procurement_purpose,
        processing_status="completed"
    )
    db.add(proc_request)
    db.flush()

    # Save individual recommendation entries in DB
    for rec_item in evaluated_recommendations:
        std_obj = db.query(IndianStandard).filter(IndianStandard.standard_number == rec_item["standard_number"]).first()
        if std_obj:
            rec_entity = Recommendation(
                procurement_request_id=proc_request.id,
                standard_id=std_obj.id,
                applicability_status=rec_item["applicability_status"],
                relevance_score=int(rec_item["internal_match_score"] * 100),
                reasoning=rec_item["reasoning"],
                evidence="; ".join(rec_item.get("evidence", [])),
                verification_required=rec_item.get("verification_required", False)
            )
            db.add(rec_entity)

    has_matches = bool(recommended_list or potentially_applicable_list)
    overall_status = "Applicable Standard Confirmed" if recommended_list else ("Potential Standards Identified - Verification Required" if potentially_applicable_list else "No Directly Applicable Standard Confirmed - Manual Verification Required")
    notice = None if has_matches else "No directly applicable BIS standard was confirmed for the provided product description. Manual verification with BIS or the relevant technical authority is required."

    if not has_matches:
        certification_guidance_list = [{
            "certification_type": "BIS Product Certification / ISI Mark",
            "applicability": "Verification Required",
            "product_category": inferred_category,
            "verification_status": "Verification Required",
            "evidence_text": "No mandatory Quality Control Order (QCO) or BIS product certification scheme could be confirmed for this product description in the local database. Manual verification with BIS or the relevant technical authority is required."
        }]

    # Assemble complete final JSON report matching exact structure
    final_report = {
        "request_id": proc_request.id,
        "procurement_summary": extracted_data.get("procurement_summary", "Procurement specification analysis complete."),
        "product_category": inferred_category,
        "product_type": extracted_data.get("product_type") or inferred_category,
        "overall_status": overall_status,
        "notice": notice,
        "extracted_requirements": extracted_data.get("extracted_requirements", []),
        "missing_requirements": clean_missing_requirements,
        "recommended_standards": recommended_list,
        "potentially_applicable_standards": potentially_applicable_list,
        "standards_requiring_verification": standards_requiring_verification,
        "related_standards": related_standards_list,
        "excluded_standards": deduped_excluded,
        "certification_guidance": certification_guidance_list,
        "warnings": [
            "Always verify standard versions and active amendments with official BIS gazette publications prior to tender publication."
        ],
        "sources": list(sources_set),
        "disclaimer": OFFICIAL_SCORE_DISCLAIMER,
        "created_at": str(proc_request.created_at) if proc_request.created_at else None
    }

    # Final validation & sanitization guard before storing/returning
    final_report = sanitize_and_validate_report(final_report)

    # Store full JSON result on ProcurementRequest
    proc_request.result_json = json.dumps(final_report)
    db.commit()

    return final_report
