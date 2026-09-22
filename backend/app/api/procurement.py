"""
Procurement API Router.
Handles procurement specification analysis submissions, document upload/OCR integration,
recommendation retrieval, user analysis history, and request deletion.
Enforces user data isolation and JWT validation.
"""

import os
import json
import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.core.models import User, ProcurementRequest
from app.models.procurement_schemas import ProcurementAnalysisResponse
from app.rag.extractor import extract_document
from app.services.recommendation_service import process_procurement_recommendation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/procurement", tags=["procurement"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/analyze", response_model=ProcurementAnalysisResponse)
async def analyze_procurement_specification(
    input_text: Optional[str] = Form(None),
    product_category: Optional[str] = Form(None),
    procurement_purpose: Optional[str] = Form(None),
    technical_specifications: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits natural-language text or uploaded procurement document for Indian Standards recommendation.
    Enforces user ownership via JWT authentication.
    """
    uploaded_file_path = None
    extracted_doc_text = None

    # Handle document upload & extraction / OCR
    if file:
        file_ext = os.path.splitext(file.filename)[1].lower()
        saved_filename = f"{uuid.uuid4()}{file_ext}"
        saved_path = os.path.join(UPLOAD_DIR, saved_filename)
        
        with open(saved_path, "wb") as f:
            content = await file.read()
            f.write(content)

        uploaded_file_path = saved_path

        try:
            # Extract text using RAG extractor (supports PDF, DOCX, TXT, CSV, images OCR)
            extraction_result = extract_document(saved_path)
            if isinstance(extraction_result, dict):
                extracted_doc_text = extraction_result.get("text", "")
            else:
                extracted_doc_text = str(extraction_result)
        except Exception as e:
            logger.error(f"Document extraction error: {str(e)}")
            extracted_doc_text = f"[Text extraction attempted for {file.filename}]"


    # Combine input texts
    spec_text = input_text or ""
    if technical_specifications:
        spec_text += "\n" + technical_specifications

    if not spec_text and not extracted_doc_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide specification text, technical specifications, or upload a document."
        )

    # Process recommendation
    report = process_procurement_recommendation(
        db=db,
        user_id=current_user.id,
        input_text=spec_text,
        uploaded_file_path=uploaded_file_path,
        extracted_doc_text=extracted_doc_text,
        product_category=product_category,
        procurement_purpose=procurement_purpose
    )

    return report


@router.get("/requests")
def get_user_procurement_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves history of procurement requests for the authenticated user only.
    """
    requests = db.query(ProcurementRequest).filter(
        ProcurementRequest.user_id == current_user.id
    ).order_by(ProcurementRequest.created_at.desc()).all()

    results = []
    for req in requests:
        parsed_result = None
        if req.result_json:
            try:
                parsed_result = json.loads(req.result_json)
            except Exception:
                pass

        results.append({
            "id": req.id,
            "product_category": req.product_category,
            "procurement_purpose": req.procurement_purpose,
            "processing_status": req.processing_status,
            "created_at": str(req.created_at),
            "summary": parsed_result.get("procurement_summary") if parsed_result else req.input_text[:150] if req.input_text else "Procurement Specification",
            "recommended_count": len(parsed_result.get("recommended_standards", [])) if parsed_result else 0
        })

    return {"requests": results}


@router.get("/requests/{request_id}", response_model=ProcurementAnalysisResponse)
def get_procurement_request_detail(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves detailed recommendation result for a specific request.
    Strictly verifies user ownership.
    """
    req = db.query(ProcurementRequest).filter(
        ProcurementRequest.id == request_id,
        ProcurementRequest.user_id == current_user.id
    ).first()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement request not found or unauthorized access."
        )

    if req.result_json:
        return json.loads(req.result_json)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Recommendation result details unavailable."
    )


@router.delete("/requests/{request_id}")
def delete_procurement_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a user's procurement request and associated recommendations.
    Strictly verifies user ownership.
    """
    req = db.query(ProcurementRequest).filter(
        ProcurementRequest.id == request_id,
        ProcurementRequest.user_id == current_user.id
    ).first()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement request not found or unauthorized access."
        )

    db.delete(req)
    db.commit()

    return {"message": "Procurement request deleted successfully."}
