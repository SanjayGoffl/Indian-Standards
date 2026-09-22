"""
FastAPI routes for the Admin Dashboard.

Access is restricted to users with role == "Admin" (see User model
in app.core.models - role defaults to "User" for everyone else).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.admin.schemas import (
    AdminDashboardOverview,
    AdminUsersListResponse,
    AdminUserDetail,
    AdminUserStatusUpdate,
    AdminUserRoleUpdate,
    AdminDocumentSummary,
    QueriesPerUser,
    FrequentQuery,
)
from app.admin.service import (
    get_dashboard_overview,
    get_users_summary,
    get_user_detail,
    update_user_status,
    update_user_role,
    delete_user_as_admin,
    get_all_documents,
    delete_document_as_admin,
    get_queries_per_user,
    get_frequent_queries,
)
from app.core.database import get_db
from app.core.models import User
from app.dependencies.auth import get_current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Ensure the authenticated user has the "Admin" role.
    Reuses the existing get_current_user dependency (JWT validation)
    and adds a role check on top.
    """
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


router = APIRouter(
    prefix="/admin",
    tags=["Admin Dashboard"],
    dependencies=[Depends(require_admin)],
)


@router.get(
    "/overview",
    response_model=AdminDashboardOverview,
    summary="Get Admin Dashboard Overview",
)
def admin_overview(
    db: Session = Depends(get_db),
):
    """
    Return system-wide stats: total users, total documents, and
    query analytics (reused from the existing analytics module).
    """
    return get_dashboard_overview(db)


@router.get(
    "/users",
    response_model=AdminUsersListResponse,
    summary="Get All Users With Usage Summary",
)
def admin_users(
    db: Session = Depends(get_db),
):
    """
    Return every user with their document count and query count.
    """
    users = get_users_summary(db)
    return AdminUsersListResponse(
        users=users,
        total_users=len(users),
    )


@router.get(
    "/users/{user_id}",
    response_model=AdminUserDetail,
    summary="Get Single User Detail",
)
def admin_user_detail(
    user_id: str,
    db: Session = Depends(get_db),
):
    """
    Return full detail for one user, including their uploaded documents.
    """
    return get_user_detail(db, user_id)


@router.patch(
    "/users/{user_id}/status",
    response_model=AdminUserDetail,
    summary="Block or Unblock a User",
)
def admin_update_user_status(
    user_id: str,
    payload: AdminUserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Enable or disable a user's ability to authenticate and use the API."""
    return update_user_status(db, user_id, payload.is_active, current_user)


@router.patch(
    "/users/{user_id}/role",
    response_model=AdminUserDetail,
    summary="Change a User's System Role",
)
def admin_update_user_role(
    user_id: str,
    payload: AdminUserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Promote a user to Admin or demote an Admin back to User."""
    return update_user_role(db, user_id, payload.role, current_user)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently Delete a User Account",
)
def admin_delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Permanently delete a user and their user-owned knowledge vectors."""
    delete_user_as_admin(db, user_id, current_user)


@router.get(
    "/documents",
    response_model=list[AdminDocumentSummary],
    summary="Get All Documents (System-Wide)",
)
def admin_documents(
    db: Session = Depends(get_db),
):
    """
    Return every document in the system, along with its owner.
    """
    return get_all_documents(db)


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Any User's Document (Admin Override)",
)
def admin_delete_document(
    document_id: str,
    db: Session = Depends(get_db),
):
    """
    Delete a document belonging to any user.
    """
    delete_document_as_admin(db, document_id)


@router.get(
    "/analytics/queries-per-user",
    response_model=list[QueriesPerUser],
    summary="Get Query Count Per User",
)
def admin_queries_per_user(
    db: Session = Depends(get_db),
):
    """
    Return how many queries each user has made.
    """
    return get_queries_per_user(db)


@router.get(
    "/analytics/frequent-queries",
    response_model=list[FrequentQuery],
    summary="Get Most Frequent Queries (System-Wide)",
)
def admin_frequent_queries(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """
    Return the most commonly asked queries across all users.
    """
    return get_frequent_queries(db, limit=limit)