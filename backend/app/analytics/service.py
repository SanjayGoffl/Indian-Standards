"""
Business logic for Query Analytics.

All analytics statistics are calculated per authenticated user.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.analytics.models import QueryAnalytics
from app.analytics.schemas import (
    AnalyticsOverview,
    QueryAnalyticsCreate,
)


def log_query(
    db: Session,
    data: QueryAnalyticsCreate,
) -> QueryAnalytics:
    """
    Store analytics information for a query.

    The router ensures that data.user_id belongs to the
    authenticated user before this function is called.
    """

    analytics = QueryAnalytics(
        user_id=data.user_id,
        conversation_id=data.conversation_id,
        query_text=data.query_text,
        query_type=data.query_type,
        response_status=data.response_status,
        confidence_score=data.confidence_score,
        response_time=data.response_time,
    )

    db.add(analytics)
    db.commit()
    db.refresh(analytics)

    return analytics


def get_total_queries(
    db: Session,
    user_id: str,
) -> int:
    """
    Return total number of queries for one user.
    """

    return (
        db.query(QueryAnalytics)
        .filter(
            QueryAnalytics.user_id == user_id
        )
        .count()
    )


def get_answered_queries(
    db: Session,
    user_id: str,
) -> int:
    """
    Return number of answered queries for one user.
    """

    return (
        db.query(QueryAnalytics)
        .filter(
            QueryAnalytics.user_id == user_id,
            QueryAnalytics.response_status
            == "answered",
        )
        .count()
    )


def get_unanswered_queries(
    db: Session,
    user_id: str,
) -> int:
    """
    Return number of unanswered queries for one user.
    """

    return (
        db.query(QueryAnalytics)
        .filter(
            QueryAnalytics.user_id == user_id,
            QueryAnalytics.response_status
            == "unanswered",
        )
        .count()
    )


def get_average_confidence(
    db: Session,
    user_id: str,
) -> float | None:
    """
    Calculate average confidence score for RAG-related queries
    for one authenticated user.

    General queries are excluded because they do not evaluate
    knowledge-base retrieval quality.
    """

    result = (
        db.query(
            func.avg(
                QueryAnalytics.confidence_score
            )
        )
        .filter(
            QueryAnalytics.user_id == user_id,
            QueryAnalytics.query_type != "general",
            QueryAnalytics.response_status == "answered",
            QueryAnalytics.confidence_score.isnot(None),
        )
        .scalar()
    )

    if result is None:
        return None

    return round(
        float(result),
        3,
    )

def get_average_response_time(
    db: Session,
    user_id: str,
) -> float | None:
    """
    Calculate average response time in seconds
    for one user.
    """

    result = (
        db.query(
            func.avg(
                QueryAnalytics.response_time
            )
        )
        .filter(
            QueryAnalytics.user_id == user_id
        )
        .scalar()
    )

    if result is None:
        return None

    return round(
        float(result),
        3,
    )


def get_overview(
    db: Session,
    user_id: str,
) -> AnalyticsOverview:
    """
    Return overall query analytics
    for one authenticated user.
    """

    total = get_total_queries(
        db=db,
        user_id=user_id,
    )

    answered = get_answered_queries(
        db=db,
        user_id=user_id,
    )

    unanswered = get_unanswered_queries(
        db=db,
        user_id=user_id,
    )

    average_confidence = (
        get_average_confidence(
            db=db,
            user_id=user_id,
        )
    )

    average_response_time = (
        get_average_response_time(
            db=db,
            user_id=user_id,
        )
    )

    return AnalyticsOverview(
        total_queries=total,
        answered_queries=answered,
        unanswered_queries=unanswered,
        average_confidence=average_confidence,
        average_response_time=average_response_time,
    )


def get_query_type_statistics(
    db: Session,
    user_id: str,
) -> list[dict]:
    """
    Return number of queries grouped by query type
    for one authenticated user.
    """

    results = (
        db.query(
            QueryAnalytics.query_type,
            func.count(QueryAnalytics.id),
        )
        .filter(
            QueryAnalytics.user_id == user_id,
            QueryAnalytics.query_type.isnot(None),
        )
        .group_by(
            QueryAnalytics.query_type
        )
        .order_by(
            func.count(
                QueryAnalytics.id
            ).desc()
        )
        .all()
    )

    return [
        {
            "query_type": query_type,
            "count": count,
        }
        for query_type, count in results
    ]