"""
Applicability Engine.
Evaluates candidate Indian Standards against extracted procurement requirements.
Generates Field Comparison Matrix, dynamic technical reasoning, explainable scores, and excluded standards.
"""

import json
import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.core.models import IndianStandard, StandardRelationship
from app.services.recommendation_validator import (
    generate_field_comparison_matrix,
    calculate_technical_match_score,
    classify_standard_applicability,
    filter_unrelated_standards,
    OFFICIAL_SCORE_DISCLAIMER
)

logger = logging.getLogger(__name__)


from datetime import datetime, timezone


def evaluate_standards_applicability(
    db: Session,
    candidate_standards: List[IndianStandard],
    extracted_data: Dict[str, Any],
    procurement_purpose: str = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Evaluates candidate Indian Standards using Field Comparison Matrix and recommendation_validator.
    Returns (evaluated_applicable_standards, excluded_standards).
    """
    # 1. Filter out domain/category mismatched candidates (e.g. Solar, IT, Pipes, Steel, Concrete, Water, Helmets, Respirators vs Cables)
    applicable_candidates, excluded_standards = filter_unrelated_standards(
        candidate_standards=candidate_standards,
        extracted_data=extracted_data
    )

    results = []
    extracted_reqs = extracted_data.get("extracted_requirements", [])
    target_category = extracted_data.get("product_category", "General Procurement")
    now_iso = datetime.now(timezone.utc).isoformat()

    for std in applicable_candidates:
        # Check standard relationships (normative references, test methods)
        relationships = db.query(StandardRelationship).filter(StandardRelationship.standard_id == std.id).all()
        rel_list = []
        for r in relationships:
            rel_std = db.query(IndianStandard).filter(IndianStandard.id == r.related_standard_id).first()
            if rel_std:
                has_rel_ver = (r.verification_status == "Verified")
                rel_list.append({
                    "standard_number": rel_std.standard_number,
                    "title": rel_std.title,
                    "relationship_type": r.relationship_type,
                    "description": r.description or f"Related {r.relationship_type} standard",
                    "verification_status": r.verification_status or "Verification Required",
                    "scope_label": "Scope summary from local catalogue — official document verification required.",
                    "source": rel_std.source or "Local BIS Catalogue",
                    "source_url": rel_std.source_url if (has_rel_ver and rel_std.source_url) else None,
                    "source_document": r.source_document or "Local Catalogue Record",
                    "page_or_clause": r.page_or_clause_reference or "Clause verification required",
                    "retrieved_at": now_iso,
                    "provenance": {
                        "source": rel_std.source or "Local BIS Catalogue",
                        "source_url": rel_std.source_url if (has_rel_ver and rel_std.source_url) else None,
                        "source_document": r.source_document or "Local Catalogue Record",
                        "page_or_clause": r.page_or_clause_reference or "Clause verification required",
                        "retrieved_at": now_iso,
                        "verification_status": r.verification_status or "Verification Required"
                    }
                })

        # Generate 6-parameter Field Comparison Matrix
        matrix = generate_field_comparison_matrix(std, extracted_reqs, target_category)

        # Calculate explainable score & match strength
        score, match_strength = calculate_technical_match_score(matrix)

        has_qco = bool(std.evidence_text and len(std.evidence_text) > 10)

        # Classify applicability status
        classification = classify_standard_applicability(
            standard_number=std.standard_number,
            title=std.title,
            internal_score=score,
            match_strength=match_strength,
            matrix=matrix,
            has_verified_qco=has_qco
        )

        is_4984 = "4984" in std.standard_number
        is_pipe_target = any(w in (target_category or "").lower() for w in ["pipe", "pipes", "piping", "hdpe", "water supply", "effluent", "sewage", "conveyance", "plumbing", "fluid transport", "water distribution"])

        if is_4984 and is_pipe_target:
            classification["applicability_status"] = "Potentially Applicable"
            dynamic_reasoning = (
                "Potentially applicable because the standard addresses HDPE pipes for water supplies "
                "and related conveyance applications. Final applicability requires confirmation of nominal diameter, "
                "wall thickness, pressure class, material grade, operating conditions, jointing method, "
                "intended application, and applicable certification requirements."
            )
        else:
            # Construct dynamic technical reasoning from matrix results
            matched_params = [item['parameter'] for item in matrix if item['result'] == 'Match']
            mismatched_params = [f"{item['parameter']} ({item['standard_provision']})" for item in matrix if item['result'] == 'Mismatch']
            unknown_params = [item['parameter'] for item in matrix if item['result'] == 'Unknown']

            reasoning_parts = []
            if matched_params:
                reasoning_parts.append(f"Matches explicit requirements for: {', '.join(matched_params)}.")
            if mismatched_params:
                reasoning_parts.append(f"Contains technical deviations: {', '.join(mismatched_params)}.")
            if unknown_params:
                reasoning_parts.append(f"Requires verification for: {', '.join(unknown_params)}.")

            dynamic_reasoning = " ".join(reasoning_parts) if reasoning_parts else "Potentially applicable based on domain and specification alignment."

        has_ver_src = (getattr(std, "verification_status", "") == "Verified")

        res_item = {
            "standard_number": std.standard_number,
            "title": std.title,
            "scope": std.scope,
            "scope_summary": std.scope,
            "scope_label": "Scope summary from local catalogue — official document verification required.",
            "applicability_status": classification["applicability_status"],
            "internal_match_score": classification["internal_match_score"],
            "match_strength": classification["match_strength"],
            "field_comparison_matrix": matrix,
            "reasoning": dynamic_reasoning,
            "latest_revision": std.revision or "Revision and amendment status requires verification from official BIS standards catalogue.",
            "revision_verification_status": "Unverified",
            "amendments": [std.amendment_details] if std.amendment_details else [],
            "related_standards": rel_list,
            "evidence": [std.evidence_text] if std.evidence_text else [],
            "verification_required": True,
            "source": std.source or "Local BIS Catalogue",
            "source_url": std.source_url if (has_ver_src and std.source_url) else None,
            "source_document": "Local Catalogue Record",
            "page_or_clause": "Clause verification required",
            "retrieved_at": std.retrieved_at or now_iso,
            "verification_status": "Verification Required",
            "provenance": {
                "source": std.source or "Local BIS Catalogue",
                "source_url": std.source_url if (has_ver_src and std.source_url) else None,
                "source_document": "Local Catalogue Record",
                "page_or_clause": "Clause verification required",
                "retrieved_at": std.retrieved_at or now_iso,
                "verification_status": "Verification Required"
            }
        }
        results.append(res_item)

    # Sort results by internal match score descending
    results.sort(key=lambda x: x["internal_match_score"], reverse=True)
    return results, excluded_standards
