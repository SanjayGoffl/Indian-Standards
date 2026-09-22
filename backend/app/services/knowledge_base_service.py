from typing import List, Optional
from datetime import datetime
import uuid
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import UPLOAD_FOLDER
from app.core.models import KnowledgeBaseDocument
from app.rag.chromadb_service import (
    add_documents,
    delete_documents_for_user,
)
from app.rag.chunking import chunk_text
from app.rag.embedding import embed_chunks, load_embedding_model
from app.rag.extractor import extract_document


def _get_document(db: Session, document_id: str, user_id: str) -> Optional[KnowledgeBaseDocument]:
    return db.query(KnowledgeBaseDocument).filter(
        KnowledgeBaseDocument.id == document_id,
        KnowledgeBaseDocument.user_id == user_id
    ).first()


def get_all_user_documents(db: Session, user_id: str) -> List[KnowledgeBaseDocument]:
    """Return all documents owned by the user, ordered by creation date."""
    return db.query(KnowledgeBaseDocument).filter(
        KnowledgeBaseDocument.user_id == user_id
    ).order_by(desc(KnowledgeBaseDocument.created_at)).all()


def get_user_document_by_id(db: Session, document_id: str, user_id: str) -> Optional[KnowledgeBaseDocument]:
    """Return a single document if it belongs to the user."""
    return _get_document(db, document_id, user_id)


def delete_user_document(db: Session, document_id: str, user_id: str) -> bool:
    """Delete a document and its vectors. Return True if successful."""
    document = _get_document(db, document_id, user_id)
    if not document:
        return False

    # Delete vectors from ChromaDB
    delete_documents_for_user(document_id, user_id)

    # Delete postgres record
    db.delete(document)
    db.commit()

    # Clean up any active jobs in memory
    from app.services.metadata_service import processing_jobs
    document_job_ids = [
        job_id for job_id, job in processing_jobs.items()
        if job.get("documentId") == document_id
    ]
    for job_id in document_job_ids:
        processing_jobs.pop(job_id, None)

    return True


def create_knowledge_base_document(
    db: Session,
    user_id: str,
    file_data: bytes,
    original_filename: str,
    extension: str,
) -> tuple[str, str]:
    """Save file, create DB record, and return (document_id, file_path)."""
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    
    document_id = str(uuid.uuid4())
    unique_filename = f"{document_id}{extension}"
    file_path = UPLOAD_FOLDER / unique_filename

    # Save file
    with open(file_path, "wb") as f:
        f.write(file_data)

    # Create postgres record
    db_document = KnowledgeBaseDocument(
        id=document_id,
        user_id=user_id,
        filename=unique_filename,
        original_filename=original_filename,
        file_type=extension,
        file_size=len(file_data),
        status="processing"
    )
    db.add(db_document)
    db.commit()

    return document_id, str(file_path)


def process_knowledge_base_document(
    db: Session,
    document_id: str,
    user_id: str,
    file_path: str,
    original_filename: str,
) -> None:
    """Background task to extract, chunk, embed, and store document data."""
    try:
        from pathlib import Path
        path_obj = Path(file_path)

        # 1. Extract Text
        extracted_text = extract_document(str(path_obj))
        if not extracted_text:
            raise ValueError("No text could be extracted")

        # 2. Chunking
        chunks = chunk_text(extracted_text)
        if not chunks:
            raise ValueError("No chunks could be created")

        # 3. Embedding
        model = load_embedding_model()
        embeddings = embed_chunks(model, chunks)
        if not embeddings:
            raise ValueError("No embeddings could be generated")

        # 4. Store in ChromaDB with user_id
        metadatas = [
            {
                "document_id": document_id,
                "filename": original_filename,
                "chunk_index": i,
                "user_id": user_id,
            }
            for i in range(len(chunks))
        ]

        add_documents(
            chunks,
            embeddings,
            metadatas=metadatas,
            document_id=document_id,
        )

        # Update status
        doc = db.query(KnowledgeBaseDocument).get(document_id)
        if doc:
            doc.status = "completed"
            db.commit()

    except Exception as e:
        print(f"Error processing document {document_id}: {e}")
        doc = db.query(KnowledgeBaseDocument).get(document_id)
        if doc:
            doc.status = "failed"
            db.commit()

    finally:
        # Cleanup file
        try:
            import os
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
