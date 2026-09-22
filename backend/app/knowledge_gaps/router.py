from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import User
from app.dependencies.auth import get_current_user

from app.knowledge_gaps.schemas import (
    KnowledgeGapResponse,
    KnowledgeGapStatistics,
)

from app.knowledge_gaps.service import (
    get_gap_statistics,
    get_knowledge_gaps,
    get_top_knowledge_gaps,
)


router = APIRouter(
    prefix="/knowledge-gaps",
    tags=["Knowledge Gap Detection"],
)


@router.get(
    "",
    response_model=list[KnowledgeGapResponse],
)
def list_knowledge_gaps(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Return knowledge gaps for the authenticated user only.
    """

    return get_knowledge_gaps(
        db=db,
        user_id=str(current_user.id),
    )


@router.get(
    "/top",
    response_model=list[KnowledgeGapResponse],
)
def top_knowledge_gaps(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Return top knowledge gaps for the authenticated user only.
    """

    return get_top_knowledge_gaps(
        db=db,
        user_id=str(current_user.id),
        limit=limit,
    )


@router.get(
    "/statistics",
    response_model=KnowledgeGapStatistics,
)
def knowledge_gap_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Return knowledge-gap statistics for the authenticated user only.
    """

    return get_gap_statistics(
        db=db,
        user_id=str(current_user.id),
    )