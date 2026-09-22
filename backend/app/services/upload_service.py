import logging
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    UPLOAD_FOLDER,
)

from app.core.database import SessionLocal
from app.core.models import KnowledgeBaseDocument

from app.rag.chromadb_service import add_documents
from app.rag.chunking import chunk_text_with_sections
from app.rag.embedding import embed_chunks, load_embedding_model
from app.rag.extractor import extract_document

from app.services.metadata_service import (
    processing_jobs,
    update_document_status,
    update_job,
)

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Upload directory
# -------------------------------------------------------------------

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------------------------
# Validation
# -------------------------------------------------------------------

def validate_upload_filename(filename):
    """
    Validate uploaded filename and extension.
    """

    if not filename:
        return {
            "status": "failed",
            "message": "No file selected",
        }

    extension = filename.suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return {
            "status": "failed",
            "message": (
                "Unsupported file type. "
                "Use PDF, DOCX, TXT, CSV, JPG, JPEG or PNG."
            ),
        }

    return None


def validate_upload_data(file_data):
    """
    Validate uploaded file contents and size.
    """

    if len(file_data) == 0:
        return {
            "status": "failed",
            "message": "Uploaded file is empty",
        }

    if len(file_data) > MAX_FILE_SIZE:
        return {
            "status": "failed",
            "message": "File size exceeds 10 MB",
        }

    return None


# -------------------------------------------------------------------
# Create upload job
# -------------------------------------------------------------------

def create_upload_job(
    db: Session,
    file,
    file_data,
    extension,
    user_id=None,
):
    """
    Save uploaded file and create the document record in PostgreSQL.

    IMPORTANT:
    The `db` argument is intentionally kept because your existing
    upload.py passes the SQLAlchemy session into this function.
    """

    document_id = uuid.uuid4().hex
    job_id = uuid.uuid4().hex

    unique_filename = f"{document_id}{extension}"

    file_path = UPLOAD_FOLDER / unique_filename

    # ---------------------------------------------------------------
    # Save temporary uploaded file
    # ---------------------------------------------------------------

    with open(file_path, "wb") as output_file:
        output_file.write(file_data)

    try:
        # -----------------------------------------------------------
        # Store document metadata in PostgreSQL
        # -----------------------------------------------------------

        db_doc = KnowledgeBaseDocument(
            id=document_id,
            user_id=str(user_id) if user_id else "",
            filename=unique_filename,
            original_filename=file.filename,
            file_type=extension.lstrip("."),
            file_size=len(file_data),
            status="processing",
        )

        db.add(db_doc)
        db.commit()

        # -----------------------------------------------------------
        # Initialize upload-job progress
        # -----------------------------------------------------------

        processing_jobs[job_id] = {
            "jobId": job_id,
            "documentId": document_id,
            "filename": file.filename,
            "status": "processing",
            "stage": "uploaded",
            "progress": 10,
            "message": "File uploaded successfully.",
            "chunksCount": 0,
            "embeddingsCount": 0,
            "vectorsStored": 0,
            "error": None,
        }

        return document_id, job_id, file_path

    except Exception:
        db.rollback()

        if file_path.exists():
            file_path.unlink()

        raise


# -------------------------------------------------------------------
# Background document processing
# -------------------------------------------------------------------

def process_uploaded_document(
    job_id,
    document_id,
    file_path,
    original_filename,
    user_id=None,
):
    """
    Process uploaded document:

        File
          ↓
        OCR / extraction
          ↓
        Chunking
          ↓
        Embeddings
          ↓
        ChromaDB
          ↓
        PostgreSQL status = completed
    """

    process_start_time = time.perf_counter()

    try:

        # ===========================================================
        # 1. OCR / TEXT EXTRACTION
        # ===========================================================

        update_job(
            job_id,
            status="processing",
            stage="extracting",
            progress=20,
            message="Extracting text from document...",
        )

        update_document_status(
            document_id,
            status="processing",
            stage="extracting",
            progress=20,
            message="Extracting text from document...",
        )

        # -----------------------------------------------------------
        # Page-level progress callback for OCR-enabled PDF extraction
        # -----------------------------------------------------------

        def page_progress(page_num, total_pages):
            try:
                total_pages = max(int(total_pages), 1)
                page_num = min(
                    max(int(page_num), 1),
                    total_pages,
                )

                # OCR extraction occupies approximately 20% -> 35%
                progress = 20 + int(
                    (page_num / total_pages) * 15
                )

                message = (
                    f"Processing page "
                    f"{page_num}/{total_pages}..."
                )

                update_job(
                    job_id,
                    stage="extracting",
                    progress=progress,
                    message=message,
                )

                update_document_status(
                    document_id,
                    stage="extracting",
                    progress=progress,
                    message=message,
                )

            except Exception as callback_error:
                # Progress callback failure should never terminate OCR.
                logger.warning(
                    "OCR progress callback failed: %s",
                    callback_error,
                )

        logger.info(
            "[OCR] Starting extraction for '%s'",
            original_filename,
        )

        extraction_result = extract_document(
            str(file_path),
            page_progress_callback=page_progress,
        )

        if not extraction_result or not isinstance(
            extraction_result,
            dict,
        ):
            raise ValueError(
                "No text could be extracted from the file."
            )

        extracted_text = (
            extraction_result.get("text") or ""
        ).strip()

        extracted_images = (
            extraction_result.get("images") or []
        )

        if not extracted_text and not extracted_images:
            raise ValueError(
                "No readable text or content could be "
                "extracted from the file."
            )

        logger.info(
            "[OCR] Extraction completed for '%s' "
            "(text chars=%d, embedded chunks=%d)",
            original_filename,
            len(extracted_text),
            len(extracted_images),
        )

        # -----------------------------------------------------------
        # Include original filename in searchable text.
        # This helps queries such as:
        # "What is in mcp_handwritten_notes.jpeg?"
        # -----------------------------------------------------------

        if extracted_text:
            full_text = (
                f"File Name: {original_filename}\n\n"
                f"{extracted_text}"
            )
        else:
            full_text = ""

        # ===========================================================
        # 2. CHUNKING
        # ===========================================================

        update_job(
            job_id,
            stage="chunking",
            progress=40,
            message="Creating document chunks...",
        )

        update_document_status(
            document_id,
            stage="chunking",
            progress=40,
            message="Creating document chunks...",
        )

        chunks = []
        chunk_records = []

        chunking_start = time.perf_counter()

        document_file_type = file_path.suffix.lower().lstrip(".")

        if full_text:
            chunk_records = chunk_text_with_sections(
                full_text,
                file_type=document_file_type,
            )
            chunks = [
                record.get("content", "")
                for record in chunk_records
                if record.get("content")
            ]

        chunking_time = time.perf_counter() - chunking_start

        logger.info(
            "[RAG] Chunking completed for '%s' in %.2fs",
            original_filename,
            chunking_time,
        )

        # -----------------------------------------------------------
        # Metadata for normal extracted text
        # -----------------------------------------------------------

        metadatas = []
        for index, chunk in enumerate(chunks):
            record = (
                chunk_records[index]
                if index < len(chunk_records)
                else {}
            )

            is_csv_row = (
                document_file_type == "csv"
                and record.get("record_type") == "csv_row"
            )

            metadata = {
                "document_id": document_id,
                "filename": original_filename,
                "chunk_index": index,
                "source_type": (
                    "csv_row"
                    if is_csv_row
                    else "text"
                ),
                "user_id": str(user_id) if user_id else "",
            }

            if is_csv_row:
                metadata["record_type"] = "csv_row"
                row_number = record.get("csv_row_number")
                if row_number is not None:
                    metadata["csv_row_number"] = str(row_number)

            section_heading = record.get("section_heading")
            if section_heading:
                metadata["section_heading"] = section_heading

            metadatas.append(metadata)

        # -----------------------------------------------------------
        # Add OCR-derived page/image chunks
        # -----------------------------------------------------------

        for image_item in extracted_images:

            metadata = dict(
                image_item.get("metadata") or {}
            )

            page_number = metadata.get(
                "page_number"
            )

            image_index = metadata.get(
                "image_index",
                "?",
            )

            content = str(
                image_item.get("content") or ""
            ).strip()

            if not content:
                continue

            page_info = (
                f"Page {page_number} "
                if page_number is not None
                else ""
            )

            image_content = (
                f"File Name: {original_filename}\n"
                f"{page_info}"
                f"Image {image_index}\n"
                f"{content}"
            )

            chunks.append(image_content)

            # -------------------------------------------------------
            # Preserve OCR/extraction metadata supplied by extractor.
            # -------------------------------------------------------

            metadata.update(
                {
                    "document_id": document_id,
                    "filename": original_filename,
                    "chunk_index": len(chunks) - 1,
                    "user_id": (
                        str(user_id)
                        if user_id
                        else ""
                    ),
                }
            )

            # Remove any old VLM label if present.
            if metadata.get("source_type") == "vlm":
                metadata["source_type"] = "ocr"

            # If extractor supplied no source type, use OCR.
            metadata.setdefault(
                "source_type",
                "ocr",
            )

            metadatas.append(metadata)

        if not chunks:
            raise ValueError(
                "No chunks could be created from the file."
            )

        chunks_count = len(chunks)

        update_job(
            job_id,
            stage="chunking",
            progress=50,
            message=(
                f"Created {chunks_count} "
                f"document chunks."
            ),
            chunks_count=chunks_count,
        )

        update_document_status(
            document_id,
            stage="chunking",
            progress=50,
            message=(
                f"Created {chunks_count} "
                f"document chunks."
            ),
            chunks_count=chunks_count,
        )

        # ===========================================================
        # 3. EMBEDDINGS
        # ===========================================================

        update_job(
            job_id,
            stage="embedding",
            progress=60,
            message="Generating embeddings...",
        )

        update_document_status(
            document_id,
            stage="embedding",
            progress=60,
            message="Generating embeddings...",
        )

        logger.info(
            "[RAG] Loading embedding model..."
        )

        model = load_embedding_model()

        embedding_start = time.perf_counter()

        embeddings = embed_chunks(
            model,
            chunks,
        )

        embedding_time = time.perf_counter() - embedding_start

        logger.info(
            "[RAG] Embeddings generated for '%s' in %.2fs",
            original_filename,
            embedding_time,
        )

        if not embeddings:
            raise ValueError(
                "No embeddings could be generated."
            )

        embeddings_count = len(embeddings)

        update_job(
            job_id,
            stage="embedding",
            progress=75,
            message=(
                f"Generated {embeddings_count} "
                f"embeddings."
            ),
            embeddings_count=embeddings_count,
        )

        update_document_status(
            document_id,
            stage="embedding",
            progress=75,
            message=(
                f"Generated {embeddings_count} "
                f"embeddings."
            ),
            embeddings_count=embeddings_count,
        )

        # ===========================================================
        # 4. CHROMADB STORAGE
        # ===========================================================

        update_job(
            job_id,
            stage="storing",
            progress=85,
            message="Storing vectors in ChromaDB...",
        )

        update_document_status(
            document_id,
            stage="storing",
            progress=85,
            message="Storing vectors in ChromaDB...",
        )

        storage_start = time.perf_counter()

        add_documents(
            chunks,
            embeddings,
            metadatas=metadatas,
            document_id=document_id,
        )

        storage_time = time.perf_counter() - storage_start

        logger.info(
            "[RAG] ChromaDB storage completed for '%s' "
            "in %.2fs",
            original_filename,
            storage_time,
        )

        vectors_stored = len(chunks)

        update_job(
            job_id,
            stage="storing",
            progress=95,
            message=(
                f"Stored {vectors_stored} "
                f"vectors in ChromaDB."
            ),
            vectors_stored=vectors_stored,
        )

        update_document_status(
            document_id,
            stage="storing",
            progress=95,
            message=(
                f"Stored {vectors_stored} "
                f"vectors in ChromaDB."
            ),
            vectors_stored=vectors_stored,
        )

        # ===========================================================
        # 5. MARK POSTGRESQL DOCUMENT AS COMPLETED
        # ===========================================================

        completed_at = datetime.now(
            timezone.utc
        ).isoformat()

        db_session = SessionLocal()

        try:

            db_doc = (
                db_session.query(
                    KnowledgeBaseDocument
                )
                .filter(
                    KnowledgeBaseDocument.id
                    == document_id
                )
                .first()
            )

            if db_doc is None:
                raise ValueError(
                    "Document record was not found "
                    "in PostgreSQL."
                )

            db_doc.status = "completed"

            # Commit final database state.
            db_session.commit()

        finally:
            db_session.close()

        # ===========================================================
        # 6. FINAL JOB STATUS
        # ===========================================================

        update_job(
            job_id,
            status="completed",
            stage="completed",
            progress=100,
            message="Document processed successfully.",
            chunks_count=chunks_count,
            embeddings_count=embeddings_count,
            vectors_stored=vectors_stored,
        )

        update_document_status(
            document_id,
            status="completed",
            stage="completed",
            progress=100,
            message="Document processed successfully.",
            chunks_count=chunks_count,
            embeddings_count=embeddings_count,
            vectors_stored=vectors_stored,
        )

        total_time = (
            time.perf_counter()
            - process_start_time
        )

        logger.info(
            "[RAG] Total processing time for '%s': %.2fs",
            original_filename,
            total_time,
        )

    # ===============================================================
    # ERROR HANDLING
    # ===============================================================

    except Exception as error:

        error_message = str(error)

        logger.exception(
            "[UPLOAD] Processing failed for '%s': %s",
            original_filename,
            error_message,
        )

        update_job(
            job_id,
            status="failed",
            stage="error",
            progress=100,
            message="Document processing failed.",
            error=error_message,
        )

        update_document_status(
            document_id,
            status="failed",
            stage="error",
            progress=100,
            message="Document processing failed.",
            error=error_message,
        )

        # -----------------------------------------------------------
        # Mark PostgreSQL document as failed
        # -----------------------------------------------------------

        db_session = SessionLocal()

        try:

            db_doc = (
                db_session.query(
                    KnowledgeBaseDocument
                )
                .filter(
                    KnowledgeBaseDocument.id
                    == document_id
                )
                .first()
            )

            if db_doc:
                db_doc.status = "failed"
                db_session.commit()

        except Exception as db_error:

            db_session.rollback()

            logger.exception(
                "[UPLOAD] Failed to update PostgreSQL "
                "failure status: %s",
                db_error,
            )

        finally:
            db_session.close()

    # ===============================================================
    # CLEANUP
    # ===============================================================

    finally:

        try:
            if file_path.exists():
                file_path.unlink()

        except Exception as cleanup_error:

            logger.warning(
                "[UPLOAD] Could not remove temporary file '%s': %s",
                file_path,
                cleanup_error,
            )