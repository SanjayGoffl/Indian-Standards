from pydantic import BaseModel, Field
from typing import Literal


class QueryClassification(BaseModel):
    query_type: Literal[
        "factual",
        "procedural",
        "comparative",
        "general",
        "ambiguous"
    ] = Field(
        description="The type of query based on the user's intent."
    )


class QueryUnderstandingResult(BaseModel):
    original_query: str = Field(
        description="The original user query."
    )

    normalized_query: str = Field(
        description="The normalized version of the original query."
    )

    search_query: str = Field(
        description="The query optimized for retrieval/search."
    )

    query_type: Literal[
        "factual",
        "procedural",
        "comparative",
        "general",
        "ambiguous"
    ] = Field(
        description="The classified type of query."
    )

    entities: list[str] = Field(
        default_factory=list,
        description="Entities or concepts identified in the query."
    )

    keywords: list[str] = Field(
        default_factory=list,
        description="Important keywords useful for retrieval."
    )

    exact_terms: list[str] = Field(
        default_factory=list,
        description="Identifier-like terms that should be searched exactly."
    )