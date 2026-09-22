from typing import Optional

from pydantic import BaseModel, Field


class ClarificationRequest(BaseModel):
    query: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    query_type: Optional[str] = None


class ClarificationResult(BaseModel):
    needs_clarification: bool
    clarification_question: Optional[str] = None
    refined_query: Optional[str] = None


class QueryRefinementRequest(BaseModel):
    original_query: str
    clarification_question: str
    user_response: str
    conversation_id: Optional[str] = None


class RefinedQueryResult(BaseModel):
    conversation_id: Optional[str] = None
    original_query: str
    clarification_question: str
    user_response: str
    refined_query: str
