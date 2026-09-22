"""
Business logic for the Admin Dashboard.

Admin overview stats are system-wide, so query statistics are
calculated directly here (no user_id filter) rather than reusing
the existing per-user analytics functions, which require a user_id
and are designed for the normal user-facing analytics endpoints.

Reuses Knowledge Gaps functions as-is, since knowledge gaps are
already system-wide in the current schema (no user_id on that table).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.models import User, KnowledgeBaseDocument
from app.core.config import UPLOAD_FOLDER
from app.rag.chromadb_service import delete_all_documents_for_user
from app.analytics.models import QueryAnalytics
from app.knowledge_gaps.models import KnowledgeGap
from app.admin.schemas import (
    AdminDashboardOverview,
    AdminUserSummary,
    AdminUserDetail,
    AdminUserDocument,
    AdminDocumentSummary,
    QueriesPerUser,
    FrequentQuery,
)


def get_total_users(db: Session) -> int:
    return db.query(User).count()


def get_total_documents(db: Session) -> int:
    return db.query(KnowledgeBaseDocument).count()


def get_total_queries_system_wide(db: Session) -> int:
    """Total queries across ALL users (no user_id filter)."""
    return db.query(QueryAnalytics).count()


def get_answered_queries_system_wide(db: Session) -> int:
    return (
        db.query(QueryAnalytics)
        .filter(QueryAnalytics.response_status == "answered")
        .count()
    )


def get_unanswered_queries_system_wide(db: Session) -> int:
    return (
        db.query(QueryAnalytics)
        .filter(QueryAnalytics.response_status == "unanswered")
        .count()
    )


def get_average_confidence_system_wide(db: Session) -> float | None:
    result = (
        db.query(func.avg(QueryAnalytics.confidence_score))
        .filter(QueryAnalytics.confidence_score.isnot(None))
        .scalar()
    )
    return round(float(result), 3) if result is not None else None


def get_average_response_time_system_wide(db: Session) -> float | None:
    result = (
        db.query(func.avg(QueryAnalytics.response_time))
        .filter(QueryAnalytics.response_time.isnot(None))
        .scalar()
    )
    return round(float(result), 3) if result is not None else None

def get_gap_statistics_system_wide(db: Session) -> dict:
    """
    Knowledge-gap stats across ALL users, computed here in the
    admin module directly. Only selects specific columns (not the
    full ORM object) to avoid the user_id column mismatch that
    exists between the knowledge_gaps model and the current
    database migration.
    """
    total = db.query(func.count(KnowledgeGap.id)).scalar()

    open_gaps = (
        db.query(func.count(KnowledgeGap.id))
        .filter(KnowledgeGap.status == "open")
        .scalar()
    )

    reason_result = (
        db.query(
            KnowledgeGap.reason,
            func.count(KnowledgeGap.id),
        )
        .group_by(KnowledgeGap.reason)
        .order_by(func.count(KnowledgeGap.id).desc())
        .first()
    )

    return {
        "total_gaps": total or 0,
        "most_common_reason": reason_result[0] if reason_result else None,
    }


def get_dashboard_overview(db: Session) -> AdminDashboardOverview:
    """Combined system-wide overview for the admin dashboard home view."""
    gap_stats = get_gap_statistics_system_wide(db)

    return AdminDashboardOverview(
        total_users=get_total_users(db),
        total_documents=get_total_documents(db),
        total_queries=get_total_queries_system_wide(db),
        answered_queries=get_answered_queries_system_wide(db),
        unanswered_queries=get_unanswered_queries_system_wide(db),
        average_confidence=get_average_confidence_system_wide(db),
        average_response_time=get_average_response_time_system_wide(db),
        total_knowledge_gaps=gap_stats["total_gaps"],
        most_common_gap_reason=gap_stats["most_common_reason"],
    )


def get_users_summary(db: Session) -> list[AdminUserSummary]:
    """Per-user summary: document count and query count for each user."""
    users = db.query(User).all()
    summaries = []

    for user in users:
        document_count = (
            db.query(KnowledgeBaseDocument)
            .filter(KnowledgeBaseDocument.user_id == user.id)
            .count()
        )
        query_count = (
            db.query(QueryAnalytics)
            .filter(QueryAnalytics.user_id == user.id)
            .count()
        )
        summaries.append(
            AdminUserSummary(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                is_active=user.is_active,
                document_count=document_count,
                query_count=query_count,
                created_at=user.created_at,
            )
        )

    return summaries


def get_user_detail(db: Session, user_id: str) -> AdminUserDetail:
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    documents = (
        db.query(KnowledgeBaseDocument)
        .filter(KnowledgeBaseDocument.user_id == user.id)
        .all()
    )

    query_count = (
        db.query(QueryAnalytics)
        .filter(QueryAnalytics.user_id == user.id)
        .count()
    )

    return AdminUserDetail(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        document_count=len(documents),
        query_count=query_count,
        documents=[
            AdminUserDocument(
                id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type,
                status=doc.status,
                created_at=doc.created_at,
            )
            for doc in documents
        ],
    )



def _get_user_or_404(db: Session, user_id: str) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return user


def update_user_status(
    db: Session,
    user_id: str,
    is_active: bool,
    acting_admin: User,
) -> AdminUserDetail:
    """Block or unblock a user without changing their stored data."""
    user = _get_user_or_404(db, user_id)

    if user.id == acting_admin.id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot block your own administrator account.",
        )

    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return get_user_detail(db, user_id)


def update_user_role(
    db: Session,
    user_id: str,
    role: str,
    acting_admin: User,
) -> AdminUserDetail:
    """Promote a user to Admin or demote an Admin back to User."""
    user = _get_user_or_404(db, user_id)

    if user.id == acting_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own administrator role.",
        )

    normalized_role = (role or "").strip().lower()
    if normalized_role not in {"admin", "user"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be either Admin or User.",
        )

    new_role = "Admin" if normalized_role == "admin" else "User"

    if user.role == new_role:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User is already a {new_role}.",
        )

    user.role = new_role
    db.commit()
    db.refresh(user)
    return get_user_detail(db, user_id)


# Backward-compatible alias for existing internal callers.
def promote_user_to_admin(
    db: Session,
    user_id: str,
    acting_admin: User,
    role: str = "Admin",
) -> AdminUserDetail:
    return update_user_role(db, user_id, role, acting_admin)


def delete_user_as_admin(
    db: Session,
    user_id: str,
    acting_admin: User,
) -> None:
    """Permanently remove a user and clean their user-owned vectors first."""
    user = _get_user_or_404(db, user_id)

    if user.id == acting_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove your own administrator account.",
        )

    documents = (
        db.query(KnowledgeBaseDocument)
        .filter(KnowledgeBaseDocument.user_id == user.id)
        .all()
    )

    try:
        # Remove all vectors tagged with this user before deleting the
        # relational records. Older vectors without user_id are deliberately
        # left untouched because ownership cannot be determined safely.
        delete_all_documents_for_user(str(user.id))

        for document in documents:
            # Uploaded files are stored under the backend upload directory
            # using the generated database filename. Never trust a client
            # supplied path here; resolve only the basename stored by the app.
            if document.filename:
                uploaded_file = UPLOAD_FOLDER / Path(document.filename).name
                if uploaded_file.exists():
                    uploaded_file.unlink()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to clean the user's knowledge-base vectors. Account was not deleted.",
        ) from exc

    db.delete(user)
    db.commit()

def get_all_documents(db: Session) -> list[AdminDocumentSummary]:
    documents = (
        db.query(KnowledgeBaseDocument, User)
        .join(User, KnowledgeBaseDocument.user_id == User.id)
        .all()
    )

    return [
        AdminDocumentSummary(
            id=doc.id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            status=doc.status,
            created_at=doc.created_at,
            owner_id=user.id,
            owner_email=user.email,
        )
        for doc, user in documents
    ]


def delete_document_as_admin(db: Session, document_id: str) -> None:
    document = (
        db.query(KnowledgeBaseDocument)
        .filter(KnowledgeBaseDocument.id == document_id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    db.delete(document)
    db.commit()
    # NOTE: PostgreSQL record only - check with Subhiksha about also
    # cleaning up the matching ChromaDB vectors, same as the normal
    # user-facing delete endpoint does.


def get_queries_per_user(db: Session) -> list[QueriesPerUser]:
    results = (
        db.query(User.id, User.email, func.count(QueryAnalytics.id))
        .join(QueryAnalytics, QueryAnalytics.user_id == User.id)
        .group_by(User.id, User.email)
        .order_by(func.count(QueryAnalytics.id).desc())
        .all()
    )
    return [
        QueriesPerUser(user_id=uid, email=email, query_count=count)
        for uid, email, count in results
    ]


def get_frequent_queries(db: Session, limit: int = 10) -> list[FrequentQuery]:
    results = (
        db.query(QueryAnalytics.query_text, func.count(QueryAnalytics.id))
        .group_by(QueryAnalytics.query_text)
        .order_by(func.count(QueryAnalytics.id).desc())
        .limit(limit)
        .all()
    )
    return [
        FrequentQuery(query_text=text, occurrence_count=count)
        for text, count in results
    ]
