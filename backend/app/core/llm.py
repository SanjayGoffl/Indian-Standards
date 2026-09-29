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


FALLBACK_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]


class LLMService:
    """
    Service wrapper for invoking LLM completions with system and human prompts.
    """

    call_count: int = 0  # process-wide count of LLM invocations (for per-request accounting)

    def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        LLMService.call_count += 1
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        api_key = os.getenv("GROQ_API_KEY")
        configured_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        models_to_try = [configured_model] + [m for m in FALLBACK_MODELS if m != configured_model]

        last_error = None
        for m in models_to_try:
            try:
                llm = ChatGroq(api_key=api_key, model=m, temperature=0)
                response = llm.invoke(messages)
                return getattr(response, "content", str(response))
            except Exception as e:
                last_error = e
                continue

        raise last_error or RuntimeError("All LLM models failed.")


llm_service = LLMService()