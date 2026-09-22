import re


class QueryNormalizer:
    """
    Normalizes user queries before they are passed to the
    Query Understanding Agent.
    """

    @staticmethod
    def normalize(query: str) -> str:
        """
        Clean and normalize a user query.

        Args:
            query: Raw user query.

        Returns:
            Normalized query string.
        """
        if not isinstance(query, str):
            raise TypeError("Query must be a string.")

        # Remove leading/trailing whitespace
        query = query.strip()

        # Collapse multiple spaces/newlines into a single space
        query = re.sub(r"\s+", " ", query)

        # Remove unnecessary spaces before punctuation
        query = re.sub(r"\s+([,.!?;:])", r"\1", query)

        return query

    @staticmethod
    def normalize_for_search(query: str) -> str:
        """
        Prepare a query for retrieval/search.

        This performs slightly more aggressive normalization
        while preserving the original meaning.
        """
        query = QueryNormalizer.normalize(query)

        # Remove repeated punctuation such as "???" or "!!!"
        query = re.sub(r"([!?.,])\1+", r"\1", query)

        return query