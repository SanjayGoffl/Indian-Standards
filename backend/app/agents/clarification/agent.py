from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_llm

from .detector import ClarificationDetector
from .prompts import (
    CLARIFICATION_QUESTION_PROMPT,
    QUERY_REFINEMENT_PROMPT,
)
from .schemas import (
    ClarificationRequest,
    ClarificationResult,
    QueryRefinementRequest,
    RefinedQueryResult,
)


class ClarificationAgent:
    """
    Domain-agnostic Clarification Agent for Milestone 3.

    Responsibilities:
    - Determine whether clarification is required.
    - Generate a targeted clarification question.
    - Refine an ambiguous query using the user's clarification.

    Conversation memory is handled by the Memory Agent and
    orchestration layer.
    """

    def __init__(self, llm=None):
        self.llm = llm or get_llm()
        self.detector = ClarificationDetector(self.llm)

    def check_query(
        self,
        request: ClarificationRequest,
    ) -> ClarificationResult:
        """
        Determine whether the supplied query requires clarification.
        """

        query = (request.query or "").strip()

        if not query:
            raise ValueError(
                "Query cannot be empty."
            )

        needs_clarification = (
            self.detector.needs_clarification(
                query=query,
                query_type=request.query_type,
            )
        )

        if not needs_clarification:
            return ClarificationResult(
                needs_clarification=False,
                refined_query=query,
            )

        question = self.generate_question(
            query
        )

        return ClarificationResult(
            needs_clarification=True,
            clarification_question=question,
        )

    def generate_question(
        self,
        query: str,
    ) -> str:
        """
        Generate one concise, targeted clarification question.
        """

        query = (query or "").strip()

        if not query:
            raise ValueError(
                "Query cannot be empty."
            )

        prompt = ChatPromptTemplate.from_template(
            CLARIFICATION_QUESTION_PROMPT
        )

        messages = prompt.format_messages(
            query=query
        )

        response = self.llm.invoke(
            messages
        )

        question = getattr(
            response,
            "content",
            str(response),
        )

        if isinstance(
            question,
            list,
        ):
            question = " ".join(
                str(item)
                for item in question
            )

        question = str(
            question
        ).strip()

        if not question:
            raise ValueError(
                "Clarification Agent generated an empty question."
            )

        return question

    def refine_query(
        self,
        request: QueryRefinementRequest,
    ) -> RefinedQueryResult:
        """
        Refine an ambiguous query using the user's clarification.

        The resulting query is designed to be passed directly into
        the existing Query Understanding and Retrieval pipeline.
        """

        original_query = (
            request.original_query or ""
        ).strip()

        clarification_question = (
            request.clarification_question or ""
        ).strip()

        user_response = (
            request.user_response or ""
        ).strip()

        if not original_query:
            raise ValueError(
                "Original query cannot be empty."
            )

        if not user_response:
            raise ValueError(
                "Clarification response cannot be empty."
            )

        prompt = ChatPromptTemplate.from_template(
            QUERY_REFINEMENT_PROMPT
        )

        messages = prompt.format_messages(
            original_query=original_query,
            clarification_question=(
                clarification_question
            ),
            user_response=user_response,
        )

        response = self.llm.invoke(
            messages
        )

        refined_query = getattr(
            response,
            "content",
            str(response),
        )

        if isinstance(
            refined_query,
            list,
        ):
            refined_query = " ".join(
                str(item)
                for item in refined_query
            )

        refined_query = str(
            refined_query
        ).strip()

        # Remove accidental surrounding quotation marks.
        if (
            len(refined_query) >= 2
            and refined_query[0] in {
                '"',
                "'",
                "`",
            }
            and refined_query[-1]
            == refined_query[0]
        ):
            refined_query = (
                refined_query[1:-1].strip()
            )

        if not refined_query:
            raise ValueError(
                "Clarification Agent returned an empty refined query."
            )

        return RefinedQueryResult(
            conversation_id=(
                request.conversation_id
            ),
            original_query=original_query,
            clarification_question=(
                clarification_question
            ),
            user_response=user_response,
            refined_query=refined_query,
        )