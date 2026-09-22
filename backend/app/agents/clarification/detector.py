from typing import Optional

from app.core.llm import get_llm


class ClarificationDetector:
    def __init__(self, llm=None):
        self.llm = llm or get_llm()

    def needs_clarification(
        self,
        query: str,
        query_type: Optional[str] = None,
    ) -> bool:

        if not query or not query.strip():
            return True

        if query_type is not None:
            return query_type.lower().strip() == "ambiguous"

        return self._detect_with_llm(query)

    def _detect_with_llm(self, query: str) -> bool:

        prompt = f"""
Determine whether this query requires clarification.

Return ONLY:
YES
or
NO

The query needs clarification if important information is
missing or multiple interpretations are possible.

Query:
{query}
"""

        response = self.llm.invoke(prompt)

        content = getattr(
            response,
            "content",
            str(response),
        )

        return content.strip().upper().startswith("YES")
