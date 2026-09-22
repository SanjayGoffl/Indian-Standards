"""
Pydantic schemas for Procurement Specifications and Indian Standards Recommendation Engine.
Supports technical accuracy, Field Comparison Matrix, explainable match scoring,
anti-hallucination disclaimers, and excluded standards.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RequirementExtract(BaseModel):
    category: str = Field(..., description="Parameter category e.g. Conductor, Base Insulation, Outer Sheath, Additional Property, Voltage Rating, Required Test")
    parameter: str = Field(..., description="Specific parameter name")
    value_spec: str = Field(..., description="Extracted requirement value or specification constraint")


class FieldComparisonItem(BaseModel):
    parameter: str
    required_value: str
    standard_provision: str
    result: str  # Match, Mismatch, Unknown, Not Applicable


class RelatedStandardInfo(BaseModel):
    standard_number: str
    title: str
    relationship_type: str  # normative_reference, test_method, safety, installation, terminology, material, related_product
    description: Optional[str] = None
    verification_status: Optional[str] = "Verification required from official BIS catalogue."


class CertificationInfo(BaseModel):
    certification_type: str  # BIS Product Certification / ISI, Compulsory Registration Scheme (CRS), Hallmarking, etc.
    applicability: str  # Confirmed Applicable, Potentially Applicable, Not Confirmed, Verification Required, Not Applicable
    product_category: Optional[str] = None
    relevant_is_number: Optional[str] = None
    regulatory_instrument: Optional[str] = None
    evidence_source: Optional[str] = None
    evidence_date: Optional[str] = "Unverified"
    effective_date: Optional[str] = "Unverified"
    verification_status: Optional[str] = "Verification Required"
    explanation: Optional[str] = None
    disclaimer: Optional[str] = "Official Gazette verification required prior to tender publication."
    source_url: Optional[str] = None
    evidence_text: Optional[str] = None


class ExcludedStandardItem(BaseModel):
    standard_number: str
    title: str
    category: str
    exclusion_reason: str


class StandardRecommendationItem(BaseModel):
    standard_number: str
    title: str
    scope: Optional[str] = None
    applicability_status: str  # Recommended, Potentially Applicable, Related Standard, Verification Required, Not Applicable
    internal_match_score: float = Field(default=0.75, ge=0.0, le=1.0)
    match_strength: str = Field(default="Medium")  # High, Medium, Low, Unknown
    reasoning: str
    latest_revision: Optional[str] = None
    revision_verification_status: str = Field(default="Unverified")  # Verified, Unverified, Not Available
    amendments: List[str] = Field(default_factory=list)
    field_comparison_matrix: List[FieldComparisonItem] = Field(default_factory=list)
    related_standards: List[RelatedStandardInfo] = Field(default_factory=list)
    certification_requirements: List[CertificationInfo] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    verification_required: bool = True


class StandardVerificationItem(BaseModel):
    standard_number: str
    title: str
    verification_status: str = Field(default="Verification Required from Official BIS Document")
    source_url: Optional[str] = None


class ProcurementAnalysisResponse(BaseModel):
    request_id: Optional[str] = None
    procurement_summary: str
    product_category: Optional[str] = None
    extracted_requirements: List[RequirementExtract] = Field(default_factory=list)
    recommended_standards: List[StandardRecommendationItem] = Field(default_factory=list)
    potentially_applicable_standards: List[StandardRecommendationItem] = Field(default_factory=list)
    standards_requiring_verification: List[StandardVerificationItem] = Field(default_factory=list)
    related_standards: List[RelatedStandardInfo] = Field(default_factory=list)
    excluded_standards: List[ExcludedStandardItem] = Field(default_factory=list)
    certification_guidance: List[CertificationInfo] = Field(default_factory=list)
    missing_requirements: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    disclaimer: str = Field(
        default="The match score is an internal AI retrieval indicator. It does not represent official BIS approval, compliance, certification, or legal validity."
    )
    created_at: Optional[str] = None


class ProcurementAnalysisRequest(BaseModel):
    input_text: Optional[str] = None
    product_category: Optional[str] = None
    procurement_purpose: Optional[str] = None
    technical_specifications: Optional[str] = None
    target_language: Optional[str] = "en"
