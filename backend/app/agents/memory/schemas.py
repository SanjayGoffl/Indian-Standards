from pydantic import BaseModel
from typing import Optional


class ConversationTurn(BaseModel):
    conversation_id: str
    user_query: str
    ai_response: Optional[str] = None
    timestamp: Optional[str] = None