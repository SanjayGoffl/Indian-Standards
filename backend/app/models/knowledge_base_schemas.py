from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional


class KnowledgeBaseDocumentResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeBaseDocumentsListResponse(BaseModel):
    documents: List[KnowledgeBaseDocumentResponse]


class KnowledgeBaseSearchRequest(BaseModel):
    query: str
    k: int = 3


class SearchResultMetadata(BaseModel):
    document_id: str
    filename: str
    chunk_index: Optional[int] = None
    user_id: Optional[str] = None


class KnowledgeBaseSearchResult(BaseModel):
    chunk_id: str
    content: str
    metadata: SearchResultMetadata
    distance: Optional[float] = None


class KnowledgeBaseSearchResponse(BaseModel):
    success: bool
    query: str
    results: List[KnowledgeBaseSearchResult]
    count: int
