from typing import Any, Dict

from .normalizer import QueryNormalizer
from .classifier import classify_query
from .extractor import extract_query_information
from .schemas import QueryUnderstandingResult


class QueryUnderstandingAgent:
    """
    Query Understanding Agent.

    Responsibilities:
    - Normalize the user's query
    - Extract entities, keywords, and exact terms
    - Classify the user's query
    - Produce a structured query-understanding result
    """

    def __init__(self, llm: Any) -> None:
        self.normalizer = QueryNormalizer()
        self.llm = llm

    def run(self, query: str) -> QueryUnderstandingResult:
        """
        Process a user query.

        Args:
            query: Raw query from the user.

        Returns:
            Structured query-understanding result.
        """

        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        # Normalize the query.
        normalized_query = self.normalizer.normalize(query)
        search_query = self.normalizer.normalize_for_search(query)

        # Extract entities, keywords, and exact terms.
        extracted = extract_query_information(query)

        # Classify the query using the configured LangChain chat model.
        classification = classify_query(
            self.llm,
            normalized_query,
        )

        # Build the final structured result.
        return QueryUnderstandingResult(
            original_query=query,
            normalized_query=normalized_query,
            search_query=search_query,
            query_type=classification.query_type,
            entities=extracted["entities"],
            keywords=extracted["keywords"],
            exact_terms=extracted["exact_terms"],
        )