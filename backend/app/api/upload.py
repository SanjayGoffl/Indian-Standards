from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
)

from app.services.document_service import (
    get_upload_job_status,
)

from app.services.upload_service import (
    create_upload_job,
    process_uploaded_document,
    validate_upload_data,
    validate_upload_filename,
)

from app.core.database import get_db
from sqlalchemy.orm import Session
from app.dependencies.auth import get_current_user
from app.core.models import User

# Router for document upload endpoints.
router = APIRouter()


# Upload a document for background processing.
@router.post("/upload", status_code=202)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    # Validate uploaded filename.
    filename_error = validate_upload_filename(
        Path(file.filename) if file.filename else None
    )

    if filename_error is not None:
        return filename_error

    extension = Path(file.filename).suffix.lower()

    # Read uploaded file.
    file_data = await file.read()

    # Validate uploaded content.
    data_error = validate_upload_data(
        file_data
    )

    if data_error is not None:
        return data_error

    document_id = None
    job_id = None
    file_path = None

    try:

        # Save the uploaded file and create a processing job.
        document_id, job_id, file_path = create_upload_job(
            db,
            file,
            file_data,
            extension,
            user_id=str(current_user.id),
        )

        # Process the document in the background.
        background_tasks.add_task(
            process_uploaded_document,
            job_id,
            document_id,
            file_path,
            file.filename,
            str(current_user.id),
        )

        return {
            "status": "accepted",
            "message": "File uploaded successfully.",
            "jobId": job_id,
            "documentId": document_id,
            "filename": file.filename,
        }

    except Exception as error:

        # Remove partially uploaded files if processing fails.
        if file_path is not None and file_path.exists():
            file_path.unlink()

        return {
            "status": "failed",
            "message": str(error),
        }


# Return upload job status.
@router.get("/upload/status/{job_id}")
def get_upload_status(job_id: str):

    job = get_upload_job_status(
        job_id
    )

    if job is not None:
        return job

    raise HTTPException(
        status_code=404,
        detail="Upload job not found",
    )