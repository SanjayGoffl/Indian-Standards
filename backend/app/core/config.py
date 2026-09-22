import os
from pathlib import Path


# Define the project's base directory.
BASE_DIR = Path(__file__).resolve().parents[2]

# Folder for temporarily storing uploaded files.
UPLOAD_FOLDER = BASE_DIR / "uploads"

# Folder for storing document metadata.
METADATA_FOLDER = BASE_DIR / "metadata"

# JSON file containing uploaded document information.
DOCUMENTS_FILE = METADATA_FOLDER / "documents.json"

# Folder where the ChromaDB vector database is stored.
CHROMA_DB_PATH = BASE_DIR / "chroma_db"

# Supported file formats for document upload.
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt",
    ".csv",
    ".jpg",
    ".jpeg",
    ".png",
}

# Maximum allowed upload size (10 MB).
MAX_FILE_SIZE = 10 * 1024 * 1024


# -------------------------------------------------------------
# CORS
# -------------------------------------------------------------

LOCAL_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip()

CORS_ALLOW_ORIGINS = [
    *LOCAL_ORIGINS,
    *(
        origin.strip()
        for origin in FRONTEND_URL.split(",")
        if origin.strip()
    ),
]
