"""
FastAPI routes for Query Analytics.

All analytics endpoints are scoped to the currently
authenticated user.
"""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
)

from sqlalchemy.orm import Session

from app.analytics.schemas import (
    AnalyticsOverview,
    QueryAnalyticsCreate,
    QueryAnalyticsResponse,
    QueryThemeResponse,
)

from app.analytics.service import (
    get_overview,
    get_query_type_statistics,
    log_query,
)

from app.analytics.theme_service import get_query_themes

from app.core.database import get_db
from app.core.models import User
from app.dependencies.auth import get_current_user


router = APIRouter(
    prefix="/analytics",
    tags=["Query Analytics"],
)


@router.post(
    "/log",
    response_model=QueryAnalyticsResponse,
    summary="Log Query Analytics",
)
def create_query_analytics(
    data: QueryAnalyticsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Store analytics information for the authenticated user.

    The user_id supplied by the frontend is ignored and replaced
    with the authenticated user's database ID. This prevents one
    user from writing analytics records under another user's ID.
    """

    authenticated_user_id = str(
        current_user.id
    )

    # Preserve the existing request schema while ensuring that
    # user_id always belongs to the authenticated user.
    data = data.model_copy(
        update={
            "user_id": authenticated_user_id
        }
    )

    return log_query(
        db=db,
        data=data,
    )


@router.get(
    "/overview",
    response_model=AnalyticsOverview,
    summary="Get Analytics Overview",
)
def analytics_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return query statistics only for the authenticated user.
    """

    user_id = str(
        current_user.id
    )

    return get_overview(
        db=db,
        user_id=user_id,
    )


@router.get(
    "/query-types",
    summary="Get Query Type Statistics",
)
def query_type_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return query counts grouped by query type
    only for the authenticated user.
    """

    user_id = str(
        current_user.id
    )

    return get_query_type_statistics(
        db=db,
        user_id=user_id,
    )


@router.get(
    "/query-themes",
    response_model=list[QueryThemeResponse],
    summary="Get Common Query Themes",
)
def query_theme_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Group semantically similar queries for the authenticated user and
    expose theme-level knowledge-gap signals.
    """

    user_id = str(current_user.id)
    return get_query_themes(
        db=db,
        user_id=user_id,
    )
