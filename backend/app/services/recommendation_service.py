"""
Master Recommendation Service.
Orchestrates procurement requirement extraction, hybrid standards retrieval, applicability scoring,
technical Field Comparison Matrix validation, excluded standards filtering, certification guidance, and PostgreSQL persistence.
"""

import json
import logging
import time
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.models import ProcurementRequest, Recommendation, IndianStandard
from app.services.requirement_analyzer import extract_procurement_requirements
from app.services.standards_retrieval import retrieve_candidate_standards
from app.services.applicability_engine import evaluate_standards_applicability
from app.services.certification_service import resolve_certification_requirements
from app.services.version_verification import verify_standard_version_details
from app.services.standards_knowledge_base import seed_indian_standards
from app.services.recommendation_validator import (
    OFFICIAL_SCORE_DISCLAIMER,
    normalize_standard_number,
    sanitize_and_validate_report,
    finalize_recommendation_buckets,
    filter_unrelated_standards,
)
from app.services.compliance_engine import (
    detect_profile,
    extract_schema,
    schema_to_extracted_data,
    retrieve_candidates,
    evaluate_candidates,
    residual_requirements,
)
from app.core.llm import llm_service

logger = logging.getLogger(__name__)

LIVE_CATALOGUE_SOURCE = "BIS Know Your Standards (Live API)"


def _newer_active_revision(db: Session, std_obj: IndianStandard) -> Optional[str]:
    """Newest active standard with the same base number and part, if later than std_obj."""
    if not std_obj or not std_obj.base_standard_number:
        return None
    q = db.query(IndianStandard).filter(
        IndianStandard.base_standard_number == std_obj.base_standard_number,
        IndianStandard.status != "Withdrawn",
        IndianStandard.id != std_obj.id,
    )
    q = q.filter(IndianStandard.part_number == std_obj.part_number) if std_obj.part_number else q.filter(IndianStandard.part_number.is_(None))
    latest = q.order_by(IndianStandard.revision_year.desc()).first()
    if latest and (latest.revision_year or "") > (std_obj.revision_year or ""):
        return latest.standard_number
    return None


def _public_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-safe view of the per-run requirement schema (explicit vs derived, verbatim source text)."""
    return {
        "profile": schema["profile"],
        "attributes": {k: {"values": v["values"], "source_text": v["source_text"], "derived": v["derived"],
                           **({"basis": v["basis"]} if v.get("basis") else {})}
                       for k, v in schema["attributes"].items()},
        "requested_domains": schema["requested_domains"],
        "installation_intent": schema["installation_intent"],
    }


def _annotate_lifecycle(db: Session, item: Dict[str, Any], warnings: list) -> None:
    """Revision / withdrawal verification for allied (related, test, installation) standards."""
    std_obj = db.query(IndianStandard).filter(IndianStandard.standard_number == item["standard_number"]).first()
    if not std_obj:
        return
    has_sync = std_obj.source == LIVE_CATALOGUE_SOURCE
    ver = verify_standard_version_details(
        standard_number=std_obj.standard_number,
        raw_revision=std_obj.revision,
        amendment_details=std_obj.amendment_details or "",
        has_catalog_sync=has_sync,
        catalogue_status=std_obj.status,
        newer_active_revision=_newer_active_revision(db, std_obj) if has_sync else None,
        catalogue_retrieved_at=std_obj.retrieved_at,
    )
    item["latest_revision"] = ver["latest_revision"]
    item["revision_verification_status"] = ver["revision_verification_status"]
    item["catalogue_status"] = std_obj.status
    warnings.extend(w for w in ver.get("version_warnings", []) if "withdrawn" in w or "newer revision" in w)


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

    t_start = time.perf_counter()
    llm_calls_before = llm_service.call_count

    # 2-4. Understand -> extract -> retrieve -> gate -> bucket. A recognised domain profile runs the
    # deterministic, LLM-free engine; an unrecognised (or ambiguous) domain is the genuine-ambiguity
    # case and falls back to LLM extraction + hybrid retrieval. Nothing is cached between runs.
    profile = detect_profile(combined_text, product_category or "")
    schema = None
    engine_result = None

    raw_retrieved = []
    if profile:
        extraction_path = f"deterministic_profile:{profile['id']}"
        schema = extract_schema(profile, combined_text)
        extracted_data = schema_to_extracted_data(profile, schema)
        inferred_category = product_category or extracted_data["product_category"]
        pool = retrieve_candidates(db, profile, schema, combined_text)
        engine_result = evaluate_candidates(profile, schema, pool)
        evaluated_recommendations = engine_result["products"]
        excluded_standards = engine_result["excluded"]
        raw_retrieved = list(pool)

        # Cross-domain exclusion fallback:
        # If the targeted domain profile pool yielded 0 recommendations and 0 exclusions
        # (e.g. database has standards from other domains like cables/pipes, but query was for protective gloves):
        if not evaluated_recommendations and not excluded_standards:
            fallback_candidates = retrieve_candidate_standards(
                db=db,
                query_text=combined_text,
                product_category=inferred_category,
                top_k=6
            )
            if not fallback_candidates:
                fallback_candidates = db.query(IndianStandard).limit(10).all()

            _, fallback_excluded = filter_unrelated_standards(
                candidate_standards=fallback_candidates,
                extracted_data={"product_category": inferred_category}
            )
            excluded_standards.extend(fallback_excluded)
            raw_retrieved = list(fallback_candidates)
    else:
        extraction_path = "llm_extraction_hybrid_retrieval"
        extracted_data = extract_procurement_requirements(
            input_text=combined_text,
            user_category=product_category,
            user_purpose=procurement_purpose
        )

        inferred_category = extracted_data.get("product_category") or product_category or "General Procurement"
        # Keep every explicit quantity / cited standard the extraction did not capture, verbatim.
        known = {str(r.get("value_spec", "")).lower() for r in extracted_data.get("extracted_requirements", [])}
        for extra in residual_requirements(combined_text):
            if extra["value_spec"].lower() not in known:
                extracted_data.setdefault("extracted_requirements", []).append(extra)

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

        # Cross-domain exclusion fallback if candidate search returned 0 items
        if not unique_candidates:
            fallback_candidates = db.query(IndianStandard).limit(10).all()
            _, fallback_excluded = filter_unrelated_standards(
                candidate_standards=fallback_candidates,
                extracted_data=extracted_data
            )
            excluded_standards = fallback_excluded
            evaluated_recommendations = []
            raw_retrieved = list(fallback_candidates)
        else:
            raw_retrieved = list(unique_candidates)
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
    version_warning_list = []
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
        has_catalog_sync = bool(std_obj and std_obj.source == LIVE_CATALOGUE_SOURCE)
        newer_revision = _newer_active_revision(db, std_obj) if has_catalog_sync else None

        ver_info = verify_standard_version_details(
            standard_number=std_num,
            raw_revision=item.get("latest_revision"),
            amendment_details=",".join(item.get("amendments", [])),
            has_catalog_sync=has_catalog_sync,
            catalogue_status=std_obj.status if std_obj else None,
            newer_active_revision=newer_revision,
            catalogue_retrieved_at=std_obj.retrieved_at if std_obj else None,
        )
        version_warning_list.extend(w for w in ver_info.get("version_warnings", []) if "withdrawn" in w or "newer revision" in w)
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

    test_installation_list = []
    if engine_result:
        for bucket, target in ((engine_result["related"], related_standards_list),
                               (engine_result["test_installation"], test_installation_list)):
            for rel in bucket:
                rel_norm = normalize_standard_number(rel["standard_number"])
                if rel_norm not in seen_rel_nums and rel_norm not in seen_applicable_nums:
                    seen_rel_nums.add(rel_norm)
                    _annotate_lifecycle(db, rel, version_warning_list)
                    target.append(rel)

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

    # Ensure missing_requirements contains ONLY technical details and flags "Insufficient requirements"
    raw_missing = [
        item for item in warnings_list
        if "VERIFICATION REQUIRED" not in item.upper() and "STANDARD IS " not in item.upper() and "REVISION" not in item.upper()
    ]
    clean_missing_requirements = []
    for item in raw_missing:
        c_item = item.strip()
        if not c_item.lower().startswith("insufficient requirements"):
            c_item = f"Insufficient requirements: {c_item}"
        clean_missing_requirements.append(c_item)

    # 6b. Populate decoupled candidate pipelines: retrieved -> validated -> excluded -> final
    retrieved_candidates_list = []
    seen_ret_nums = set()
    for cand in raw_retrieved:
        c_num = getattr(cand, "standard_number", None) or (cand.get("standard_number") if isinstance(cand, dict) else None)
        if not c_num:
            continue
        c_norm = normalize_standard_number(c_num)
        if c_norm in seen_ret_nums:
            continue
        seen_ret_nums.add(c_norm)
        c_title = getattr(cand, "title", None) or (cand.get("title", "") if isinstance(cand, dict) else "")
        c_cat = getattr(cand, "category", None) or (cand.get("category", inferred_category) if isinstance(cand, dict) else inferred_category)
        r_score = getattr(cand, "_retrieval_score", None)
        if r_score is None:
            r_score = 0.85 if profile else 0.70
        r_source = getattr(cand, "_retrieval_source", None) or ("Catalogue Domain Pool" if profile else "Hybrid Retrieval")
        retrieved_candidates_list.append({
            "standard_number": c_num,
            "title": c_title,
            "category": c_cat,
            "retrieval_score": round(float(r_score), 2),
            "retrieval_source": r_source
        })

    validated_candidates_list = []
    seen_val_nums = set()
    for item in evaluated_recommendations:
        std_num = item["standard_number"]
        norm_std_num = normalize_standard_number(std_num)
        if norm_std_num in seen_val_nums:
            continue
        seen_val_nums.add(norm_std_num)
        validated_candidates_list.append({
            "standard_number": std_num,
            "title": item.get("title", ""),
            "category": item.get("category", inferred_category),
            "validation_score": round(float(item.get("internal_match_score", 0.0)), 2),
            "match_strength": item.get("match_strength", "Low"),
            "applicability_status": item.get("applicability_status", "Potentially Applicable"),
            "field_comparison_matrix": item.get("field_comparison_matrix", []),
            "reasoning": item.get("reasoning", ""),
            "evidence": item.get("evidence", []),
            "recommendation_role": item.get("recommendation_role", "PRIMARY" if item.get("applicability_status") == "Recommended" else "SECONDARY_CONDITIONAL")
        })

    excluded_candidates_list = []
    seen_ex_cand_nums = set()
    for ex in deduped_excluded:
        ex_num = ex.get("standard_number", "")
        norm_ex_num = normalize_standard_number(ex_num)
        if norm_ex_num in seen_ex_cand_nums:
            continue
        seen_ex_cand_nums.add(norm_ex_num)
        gate = ex.get("gate") or ("Product Scope Gate" if "scope" in ex.get("exclusion_reason", "").lower() or "not" in ex.get("exclusion_reason", "").lower() else "Technical Gate")
        mismatch = ex.get("mismatch_type") or ("Domain Mismatch" if "scope" in ex.get("exclusion_reason", "").lower() else "Parameter Conflict")
        excluded_candidates_list.append({
            "standard_number": ex_num,
            "title": ex.get("title", ""),
            "category": ex.get("category", "Unspecified"),
            "gate": gate,
            "mismatch_type": mismatch,
            "exclusion_reason": ex.get("exclusion_reason", "Candidate did not satisfy procurement requirements."),
            "evidence": ex.get("evidence") or ex.get("exclusion_reason", "")
        })

    final_recommendations_dict = {
        "primary_recommended": recommended_list,
        "secondary_conditional": potentially_applicable_list,
        "test_installation": test_installation_list,
        "related": related_standards_list,
        "excluded": deduped_excluded
    }

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
        "test_installation_standards": test_installation_list,
        "excluded_standards": deduped_excluded,
        "retrieved_candidates": retrieved_candidates_list,
        "validated_candidates": validated_candidates_list,
        "excluded_candidates": excluded_candidates_list,
        "final_recommendations": final_recommendations_dict,
        "certification_guidance": certification_guidance_list,
        "warnings": version_warning_list + [
            "Always verify standard versions and active amendments with official BIS gazette publications prior to tender publication."
        ],
        "sources": list(sources_set),
        "requirements_schema": _public_schema(schema) if schema else None,
        "disclaimer": OFFICIAL_SCORE_DISCLAIMER,
        "created_at": str(proc_request.created_at) if proc_request.created_at else None
    }

    # Final validation & sanitization guard before storing/returning
    final_report = sanitize_and_validate_report(final_report)
    final_report = finalize_recommendation_buckets(final_report)
    final_report["processing_metrics"] = {
        "extraction_path": extraction_path,
        "llm_calls": llm_service.call_count - llm_calls_before,
        "latency_ms": round((time.perf_counter() - t_start) * 1000, 2),
    }

    # Store full JSON result on ProcurementRequest
    proc_request.result_json = json.dumps(final_report)
    db.commit()

    return final_report
