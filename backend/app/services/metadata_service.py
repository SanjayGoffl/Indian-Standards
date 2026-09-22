import json

from app.core.config import DOCUMENTS_FILE, METADATA_FOLDER


# Create the metadata directory if it does not exist.
METADATA_FOLDER.mkdir(parents=True, exist_ok=True)

# Load saved document metadata from disk.
if DOCUMENTS_FILE.exists():
    try:
        documents = json.loads(
            DOCUMENTS_FILE.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        # Start with an empty collection if loading fails.
        documents = {}
else:
    documents = {}

# Store upload job status during document processing.
processing_jobs = {}


# Save document metadata to the JSON file.
def save_documents():
    DOCUMENTS_FILE.write_text(
        json.dumps(
            documents,
            indent=2,
        ),
        encoding="utf-8",
    )


# Update the status of an upload job.
def update_job(
    job_id,
    *,
    status=None,
    stage=None,
    progress=None,
    message=None,
    chunks_count=None,
    embeddings_count=None,
    vectors_stored=None,
    error=None,
):
    job = processing_jobs.get(job_id)

    # Return if the job does not exist.
    if job is None:
        return

    # Update available job details.
    if status is not None:
        job["status"] = status

    if stage is not None:
        job["stage"] = stage

    if progress is not None:
        job["progress"] = progress

    if message is not None:
        job["message"] = message

    if chunks_count is not None:
        job["chunksCount"] = chunks_count

    if embeddings_count is not None:
        job["embeddingsCount"] = embeddings_count

    if vectors_stored is not None:
        job["vectorsStored"] = vectors_stored

    if error is not None:
        job["error"] = error


# Update the processing status of a document.
def update_document_status(
    document_id,
    *,
    status=None,
    stage=None,
    progress=None,
    message=None,
    chunks_count=None,
    embeddings_count=None,
    vectors_stored=None,
    error=None,
):
    document = documents.get(document_id)

    # Return if the document does not exist.
    if document is None:
        return

    # Update available document details.
    if status is not None:
        document["status"] = status

    if stage is not None:
        document["stage"] = stage

    if progress is not None:
        document["progress"] = progress

    if message is not None:
        document["message"] = message

    if chunks_count is not None:
        document["chunksCount"] = chunks_count

    if embeddings_count is not None:
        document["embeddingsCount"] = embeddings_count

    if vectors_stored is not None:
        document["vectorsStored"] = vectors_stored

    if error is not None:
        document["error"] = error

    # Save updated metadata.
    save_documents()