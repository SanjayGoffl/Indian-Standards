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

    for std in applicable_candidates:
        # Check standard relationships (normative references, test methods)
        relationships = db.query(StandardRelationship).filter(StandardRelationship.standard_id == std.id).all()
        rel_list = []
        for r in relationships:
            rel_std = db.query(IndianStandard).filter(IndianStandard.id == r.related_standard_id).first()
            if rel_std:
                # Ensure related standard's category is also relevant
                if not any(ex["standard_number"] == rel_std.standard_number for ex in excluded_standards):
                    rel_list.append({
                        "standard_number": rel_std.standard_number,
                        "title": rel_std.title,
                        "relationship_type": r.relationship_type,
                        "description": r.description or f"Related {r.relationship_type} standard",
                        "verification_status": "Verified in database catalogue"
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

        dynamic_reasoning = " ".join(reasoning_parts)

        res_item = {
            "standard_number": std.standard_number,
            "title": std.title,
            "scope": std.scope,
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
            "verification_required": True if not has_qco else False
        }
        results.append(res_item)

    # Sort results by internal match score descending
    results.sort(key=lambda x: x["internal_match_score"], reverse=True)
    return results, excluded_standards
