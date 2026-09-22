import re


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "be",
    "by",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "or",
    "please",
    "show",
    "tell",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}


def normalize_query(query: str) -> str:
    """Normalize query text for extraction."""

    if not query:
        return ""

    query = query.lower().replace("\\_", "_")
    query = re.sub(r"\s+", " ", query)

    return query.strip()


def extract_exact_terms(query: str) -> list[str]:
    """
    Extract identifier-like values from a user query.

    Examples:
        Name_1
        Name_7
        email_25@example.com
        user-123
    """

    normalized_query = normalize_query(query)

    if not normalized_query:
        return []

    terms = []

    # Identifiers such as Name_1.
    terms.extend(
        re.findall(
            r"\b\d{3,}\b",
            normalized_query,
        )
    )

    # Email addresses.
    terms.extend(
        re.findall(
            r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b",
            normalized_query,
        )
    )

    # Other identifiers containing digits.
    terms.extend(
        re.findall(
            r"\b[a-z][a-z0-9-]*\d[a-z0-9-]*\b",
            normalized_query,
        )
    )

    # Remove duplicates while preserving order.
    unique_terms = []

    for term in terms:
        if term not in unique_terms:
            unique_terms.append(term)

    return unique_terms


def extract_entities(
    query: str,
    exact_terms: list[str],
) -> list[str]:
    """
    Extract entities from the query.

    Initially, identifier-like exact terms are treated
    as entities for retrieval purposes.
    """

    return exact_terms.copy()


def extract_keywords(
    query: str,
    exact_terms: list[str],
) -> list[str]:
    """
    Extract important keyword terms from the query.
    """

    normalized_query = normalize_query(query)

    if not normalized_query:
        return []

    words = re.findall(
        r"\b[a-zA-Z][a-zA-Z0-9-]*\b",
        normalized_query,
    )

    exact_terms_lower = {
        term.lower()
        for term in exact_terms
    }

    keywords = []

    for word in words:

        word_lower = word.lower()

        if word_lower in STOPWORDS:
            continue

        if word_lower in exact_terms_lower:
            continue

        if word_lower not in keywords:
            keywords.append(word_lower)

    return keywords


def extract_query_information(
    query: str,
) -> dict[str, list[str]]:
    """
    Extract entities, keywords, and exact terms
    from a user query.
    """

    exact_terms = extract_exact_terms(query)

    entities = extract_entities(
        query,
        exact_terms,
    )

    keywords = extract_keywords(
        query,
        exact_terms,
    )

    return {
        "entities": entities,
        "keywords": keywords,
        "exact_terms": exact_terms,
    }