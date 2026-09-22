from app.rag.chromadb_service import delete_documents_for_user
from app.services.metadata_service import (
    documents,
    processing_jobs,
    save_documents,
)


# Return all uploaded documents.
def get_all_documents(user_id=None):
    if user_id:
        return [doc for doc in documents.values() if doc.get("user_id") == user_id]
    return list(documents.values())


# Return the processing status of an upload job.
def get_upload_job_status(job_id):
    job = processing_jobs.get(
        job_id
    )

    # Return the active job if it exists.
    if job is not None:
        return job

    # Check PostgreSQL if the job is no longer active in memory.
    from app.core.database import SessionLocal
    from app.core.models import KnowledgeBaseDocument
    db = SessionLocal()
    try:
        # Since we don't store job_id in postgres, we might not be able to find it this way.
        # However, if it's not in memory, it means either server restarted or it was removed.
        pass
    finally:
        db.close()

    # Return None if the job is not found.
    return None


# Delete a document and its indexed vectors.
def delete_document_by_id(document_id, user_id=None):

    # Return if the document does not exist.
    if document_id not in documents:
        return None

    # Verify ownership if user_id is provided.
    if user_id and documents[document_id].get("user_id") and documents[document_id].get("user_id") != user_id:
        return None

    # Remove document vectors from ChromaDB.
    if user_id:
        delete_documents_for_user(document_id, user_id)
    else:
        # Fallback for old documents without user_id
        from app.rag.chromadb_service import delete_documents
        delete_documents(document_id)

    # Remove document metadata.
    del documents[
        document_id
    ]

    # Save updated metadata.
    save_documents()

    # Find related upload jobs.
    document_job_ids = [
        job_id
        for job_id, job in processing_jobs.items()
        if job.get(
            "documentId"
        ) == document_id
    ]

    # Remove completed job records.
    for job_id in document_job_ids:
        processing_jobs.pop(
            job_id,
            None,
        )

    # Return success response.
    return {
        "status": "success",
        "message": "Document deleted successfully",
        "id": document_id,
    }