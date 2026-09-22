from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.knowledge_gaps.models import KnowledgeGap
from app.knowledge_gaps.schemas import (
    KnowledgeGapCreate,
    KnowledgeGapStatistics,
)


CONFIDENCE_THRESHOLD = 0.50


def detect_knowledge_gap(
    response_status: str,
    confidence_score: float | None,
    retrieval_count: int,
) -> tuple[bool, str | None]:
    """Return whether the query indicates a knowledge gap."""

    if response_status == "unanswered":
        return True, "Unanswered query"

    if retrieval_count == 0:
        return True, "No relevant chunks"

    if (
        confidence_score is not None
        and confidence_score < CONFIDENCE_THRESHOLD
    ):
        return True, "Low confidence"

    return False, None


def create_knowledge_gap(
    db: Session,
    data: KnowledgeGapCreate,
    user_id: str,
) -> KnowledgeGap:
    """
    Create a user-specific gap or increment the count
    for an exact repeated query belonging to that user.
    """

    existing_gap = (
        db.query(KnowledgeGap)
        .filter(
            KnowledgeGap.user_id == user_id,
            func.lower(KnowledgeGap.query_text)
            == data.query_text.lower(),
        )
        .first()
    )

    if existing_gap:
        existing_gap.occurrence_count += 1

        if data.confidence_score is not None:
            existing_gap.confidence_score = (
                data.confidence_score
            )

        # If a previously resolved gap appears again,
        # reopen it because the same knowledge problem has
        # occurred again for this user.
        existing_gap.status = "open"

        db.commit()
        db.refresh(existing_gap)

        return existing_gap

    gap = KnowledgeGap(
        user_id=user_id,
        query_text=data.query_text,
        query_type=data.query_type,
        reason=data.reason,
        confidence_score=data.confidence_score,
        occurrence_count=1,
        status="open",
    )

    db.add(gap)
    db.commit()
    db.refresh(gap)

    return gap


def get_knowledge_gaps(
    db: Session,
    user_id: str,
) -> list[KnowledgeGap]:
    """
    Return only knowledge gaps belonging to the
    authenticated user.
    """

    return (
        db.query(KnowledgeGap)
        .filter(
            KnowledgeGap.user_id == user_id
        )
        .order_by(
            KnowledgeGap.occurrence_count.desc()
        )
        .all()
    )


def get_top_knowledge_gaps(
    db: Session,
    user_id: str,
    limit: int = 10,
) -> list[KnowledgeGap]:
    """
    Return the most frequent knowledge gaps
    belonging only to the authenticated user.
    """

    return (
        db.query(KnowledgeGap)
        .filter(
            KnowledgeGap.user_id == user_id
        )
        .order_by(
            KnowledgeGap.occurrence_count.desc()
        )
        .limit(limit)
        .all()
    )


def get_gap_statistics(
    db: Session,
    user_id: str,
) -> KnowledgeGapStatistics:
    """
    Return knowledge-gap statistics for one user only.
    """

    base_query = (
        db.query(KnowledgeGap)
        .filter(
            KnowledgeGap.user_id == user_id
        )
    )

    total = base_query.count()

    open_gaps = (
        db.query(KnowledgeGap)
        .filter(
            KnowledgeGap.user_id == user_id,
            KnowledgeGap.status == "open",
        )
        .count()
    )

    resolved_gaps = (
        db.query(KnowledgeGap)
        .filter(
            KnowledgeGap.user_id == user_id,
            KnowledgeGap.status == "resolved",
        )
        .count()
    )

    reason_result = (
        db.query(
            KnowledgeGap.reason,
            func.count(KnowledgeGap.id),
        )
        .filter(
            KnowledgeGap.user_id == user_id
        )
        .group_by(
            KnowledgeGap.reason
        )
        .order_by(
            func.count(
                KnowledgeGap.id
            ).desc()
        )
        .first()
    )

    return KnowledgeGapStatistics(
        total_gaps=total,
        open_gaps=open_gaps,
        resolved_gaps=resolved_gaps,
        most_common_reason=(
            reason_result[0]
            if reason_result
            else None
        ),
    )