"""
LLM configuration, initialization, and response generation service.

Keeps provider/model configuration outside the agents so that
the LLM can be changed without modifying agent logic.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage


# backend/.env
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)


def get_llm() -> ChatGroq:
    """
    Create and return the configured Groq chat model.

    Raises:
        RuntimeError: If required environment variables are missing.
    """

    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL")

    if not api_key:
        raise RuntimeError(
            f"GROQ_API_KEY is missing. "
            f"Add it to: {ENV_FILE}"
        )

    if not model:
        raise RuntimeError(
            f"GROQ_MODEL is missing. "
            f"Add it to: {ENV_FILE}"
        )

    return ChatGroq(
        api_key=api_key,
        model=model,
        temperature=0,
    )


class LLMService:
    """
    Service wrapper for invoking LLM completions with system and human prompts.
    """

    def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        llm = get_llm()
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        response = llm.invoke(messages)
        return getattr(response, "content", str(response))


llm_service = LLMService()