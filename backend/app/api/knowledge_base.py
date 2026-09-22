from pathlib import Path
from fastapi import APIRouter, Depends, BackgroundTasks, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import User
from app.dependencies.auth import get_current_user
from app.models.knowledge_base_schemas import (
    KnowledgeBaseDocumentResponse,
    KnowledgeBaseDocumentsListResponse,
    KnowledgeBaseSearchRequest,
    KnowledgeBaseSearchResponse,
    KnowledgeBaseSearchResult,
    SearchResultMetadata
)
from app.services.knowledge_base_service import (
    get_all_user_documents,
    get_user_document_by_id,
    delete_user_document,
    create_knowledge_base_document,
    process_knowledge_base_document
)
from app.services.upload_service import validate_upload_filename, validate_upload_data
from app.rag.embedding import load_embedding_model, embed_chunks
from app.rag.chromadb_service import search_documents_for_user

router = APIRouter(tags=["Knowledge Base"])


@router.post("/knowledge-base/documents", status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filename_error = validate_upload_filename(Path(file.filename) if file.filename else None)
    if filename_error is not None:
        raise HTTPException(status_code=400, detail=filename_error["message"])

    extension = Path(file.filename).suffix.lower()
    file_data = await file.read()

    data_error = validate_upload_data(file_data)
    if data_error is not None:
        raise HTTPException(status_code=400, detail=data_error["message"])

    try:
        document_id, file_path = create_knowledge_base_document(
            db=db,
            user_id=current_user.id,
            file_data=file_data,
            original_filename=file.filename,
            extension=extension
        )

        background_tasks.add_task(
            process_knowledge_base_document,
            db,
            document_id,
            current_user.id,
            file_path,
            file.filename
        )

        return {
            "status": "accepted",
            "message": "File uploaded successfully. Processing in background.",
            "document_id": document_id
        }

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.get("/knowledge-base/documents", response_model=KnowledgeBaseDocumentsListResponse)
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    documents = get_all_user_documents(db, current_user.id)
    return {"documents": documents}


@router.get("/knowledge-base/documents/{document_id}", response_model=KnowledgeBaseDocumentResponse)
def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = get_user_document_by_id(db, document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/knowledge-base/documents/{document_id}")
def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    success = delete_user_document(db, document_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"message": "Document deleted successfully."}


@router.post("/knowledge-base/search", response_model=KnowledgeBaseSearchResponse)
def search_knowledge_base(
    request: KnowledgeBaseSearchRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Stand-alone semantic search restricted to the user's private documents.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        model = load_embedding_model()
        query_embedding = embed_chunks(model, [request.query])[0]

        chroma_results = search_documents_for_user(
            query_embedding=query_embedding,
            user_id=current_user.id,
            k=request.k
        )

        documents = chroma_results.get("documents", [[]])[0] if chroma_results.get("documents") else []
        metadatas = chroma_results.get("metadatas", [[]])[0] if chroma_results.get("metadatas") else []
        distances = chroma_results.get("distances", [[]])[0] if chroma_results.get("distances") else []
        ids = chroma_results.get("ids", [[]])[0] if chroma_results.get("ids") else []

        results = []
        for i, content in enumerate(documents):
            if not content:
                continue
            
            results.append(KnowledgeBaseSearchResult(
                chunk_id=ids[i] if i < len(ids) else f"result_{i}",
                content=content,
                metadata=SearchResultMetadata(**metadatas[i]) if i < len(metadatas) else SearchResultMetadata(document_id="unknown", filename="unknown"),
                distance=distances[i] if i < len(distances) else None
            ))

        return KnowledgeBaseSearchResponse(
            success=True,
            query=request.query,
            results=results,
            count=len(results)
        )

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
