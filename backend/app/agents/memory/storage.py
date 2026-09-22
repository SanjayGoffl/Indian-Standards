"""
Conversation memory storage helpers.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.models import Conversation, ConversationMessage
from .schemas import ConversationTurn


def _safe_json_dumps(value: Any) -> str | None:
    """
    Serialize metadata safely.

    Returns None when there is nothing to store.
    """
    if value is None:
        return None

    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )
    except (TypeError, ValueError):
        return None


def _safe_json_loads(value: str | None) -> dict:
    """
    Deserialize stored metadata safely.
    """
    if not value:
        return {}

    try:
        result = json.loads(value)

        if isinstance(result, dict):
            return result

        return {}

    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def save_turn(
    db: Session,
    turn: ConversationTurn,
    response_metadata: dict | None = None,
):
    """
    Save one user/assistant turn.

    response_metadata is attached only to the assistant message.
    """

    conversation = db.get(
        Conversation,
        turn.conversation_id,
    )

    if conversation is None:
        raise ValueError(
            "Conversation does not exist."
        )

    # ---------------------------------------------------------------
    # User message
    # ---------------------------------------------------------------

    user_message = ConversationMessage(
        conversation_id=turn.conversation_id,
        role="user",
        content=turn.user_query,
    )

    db.add(user_message)

    # Flush the user message first so its autoincremented ID is
    # permanently before the assistant message ID.  Message IDs are the
    # deterministic ordering key used when history/memory is read back.
    db.flush()

    # ---------------------------------------------------------------
    # Assistant message
    # ---------------------------------------------------------------

    if turn.ai_response:
        assistant_message = ConversationMessage(
            conversation_id=turn.conversation_id,
            role="assistant",
            content=turn.ai_response,
            message_metadata=_safe_json_dumps(
                response_metadata
            ),
        )

        db.add(assistant_message)
        db.flush()

    # ---------------------------------------------------------------
    # Explicitly advance conversation activity timestamp.
    #
    # Do not read the existing timestamp and assign it back.  That leaves
    # updated_at unchanged and can cause the conversation list to reopen an
    # older conversation as the "latest" one.  func.now() is evaluated by
    # the database for this write.
    # ---------------------------------------------------------------

    conversation.updated_at = func.now()

    db.commit()


def get_history(
    db: Session,
    conversation_id: str,
):
    """
    Return all messages for a conversation in deterministic insertion order.

    The integer message ID is the database-generated sequence and is more
    reliable than created_at for ordering a user/assistant pair because both
    rows can share the same database timestamp.
    """

    messages = (
        db.query(ConversationMessage)
        .filter(
            ConversationMessage.conversation_id
            == conversation_id
        )
        .order_by(
            ConversationMessage.id.asc()
        )
        .all()
    )

    return messages


def get_message_metadata(
    message: ConversationMessage,
) -> dict:
    """
    Return decoded message metadata.
    """

    return _safe_json_loads(
        message.message_metadata
    )