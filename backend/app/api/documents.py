from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.core.models import User, KnowledgeBaseDocument
from app.services.knowledge_base_service import delete_user_document

# Router for document management.
router = APIRouter()


# Return all indexed documents.
@router.get("/documents")
def get_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    docs = db.query(KnowledgeBaseDocument).filter(
        KnowledgeBaseDocument.user_id == current_user.id
    ).order_by(KnowledgeBaseDocument.created_at.desc()).all()
    
    return [
        {
            "id": doc.id,
            "name": doc.original_filename,
            "size": doc.file_size,
            "status": "indexed" if doc.status == "completed" else doc.status,
            "uploadedAt": doc.created_at.isoformat(),
        }
        for doc in docs
    ]


# Delete a document from the knowledge base.
@router.delete("/documents/{document_id}")
def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    success = delete_user_document(
        db,
        document_id,
        user_id=str(current_user.id)
    )

    # Return 404 if the document does not exist.
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return {
        "status": "success",
        "message": "Document deleted successfully",
        "id": document_id,
    }