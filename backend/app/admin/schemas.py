"""
Pydantic schemas for the Admin Dashboard.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class AdminUserSummary(BaseModel):
    """
    Summary of a single user, for the admin user list.
    """

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    document_count: int
    query_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUsersListResponse(BaseModel):
    users: List[AdminUserSummary]
    total_users: int


class AdminDashboardOverview(BaseModel):
    """
    High-level system stats for the admin dashboard home view.
    """

    total_users: int
    total_documents: int
    total_queries: int
    answered_queries: int
    unanswered_queries: int
    average_confidence: Optional[float] = None
    average_response_time: Optional[float] = None
    total_knowledge_gaps: int
    most_common_gap_reason: Optional[str] = None


class AdminUserDocument(BaseModel):
    """
    A single document belonging to a user, shown inside AdminUserDetail.
    """

    id: str
    filename: str
    file_type: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserDetail(BaseModel):
    """
    Full detail view for a single user, including their documents.
    """

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    document_count: int
    query_count: int
    documents: List[AdminUserDocument]

    model_config = ConfigDict(from_attributes=True)


class AdminUserStatusUpdate(BaseModel):
    """Enable or disable a user account."""

    is_active: bool


class AdminUserRoleUpdate(BaseModel):
    """Request body for changing a user's system role."""

    role: str


class AdminDocumentSummary(BaseModel):
    """
    A document shown in the admin's system-wide document list,
    including who owns it.
    """

    id: str
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    created_at: datetime
    owner_id: str
    owner_email: str

    model_config = ConfigDict(from_attributes=True)


class QueriesPerUser(BaseModel):
    user_id: str
    email: str
    query_count: int


class FrequentQuery(BaseModel):
    query_text: str
    occurrence_count: int