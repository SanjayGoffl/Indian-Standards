from .schemas import QueryClassification
from langchain_core.language_models import BaseChatModel


def classify_query(
    llm: BaseChatModel,
    query: str,
) -> QueryClassification:
    """
    Classify a user query into exactly one supported query type.

    The classifier distinguishes between clear queries and queries
    that require clarification before retrieval.
    """

    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    # Use native JSON Schema structured output.
    structured_llm = llm.with_structured_output(
        QueryClassification,
        method="json_schema",
        strict=True,
    )

    prompt = f"""
You are the query classification component of a knowledge
retrieval and conversational question-answering system.

Classify the user's query into EXACTLY ONE of these five categories:

1. factual
   - The user asks for a fact, definition, explanation, event,
     person, entity, or specific information that is expected to
     be answered from the user's uploaded knowledge base or
     project-specific documents.
   - The query refers to information that may exist in the
     uploaded documents.
   - Examples:
       "What does the Retrieval Agent do?"
       "What is the leave policy in the uploaded document?"
       "When was the Tribunals Reforms Bill mentioned in the document?"

2. procedural
   - The user asks how to perform something, how something works
     as a process, or asks for steps/instructions.
   - The subject and requested action are sufficiently clear.
   - Examples:
       "How does the retrieval pipeline work?"
       "How do I upload a document?"

3. comparative
   - The user explicitly asks to compare two or more identifiable
     entities, concepts, events, options, or items.
   - The entities being compared must be sufficiently clear.
   - Examples:
       "What is the difference between semantic and exact search?"
       "Compare the Retrieval Agent and Clarification Agent."

4. general
   - The user asks a general-knowledge, everyday, conversational,
     or common question that does NOT depend on the uploaded
     knowledge base.
   - These questions should be answered directly using the LLM's
     general knowledge.
   - Examples:
       "What is the capital of the United States?"
       "Who is the Prime Minister of Kenya?"
       "What is a computer?"
       "What is artificial intelligence?"
       "How are you?"
       "Hello"
       
5. ambiguous
   - The query is unclear, incomplete, underspecified, or does not
     provide enough information to determine exactly what the user
     is referring to.
   - Use ambiguous when a human would need to ask a follow-up
     question before giving a precise answer.
   - This includes unresolved references such as:
       "it", "its", "that", "this", "they", "them", "the above",
       "the previous one", etc., when their referent is not explicitly
       identifiable from the query itself.
   - This includes underspecified entities when multiple possible
     entities could match the query.
   - This includes generic references such as:
       "the bill"
       "the law"
       "the committee"
       "the regulations"
       "the new policy"
       when the query does not identify which one.
   - This includes questions such as:
       "What happened in August?"
       when no specific topic or domain is identified.
   - This includes questions such as:
       "How did it affect companies?"
       when "it" has no explicit referent in the query.
   - This includes questions such as:
       "What is its significance?"
       when "its" has no explicit referent.
   - This includes questions such as:
       "Tell me about the bill."
       when multiple bills could be relevant.
   - This includes questions asking about a missing subject:
       "Tell me more."
       "Explain further."
       "What happened after that?"
   - A query can be ambiguous even when the knowledge base contains
     a likely answer. Do NOT select one likely interpretation simply
     because it appears frequently in the knowledge base.

IMPORTANT RULES:

- Use "factual", "procedural", or "comparative" when the query is
  intended to be answered using the uploaded knowledge base.
- Use "general" ONLY for explicit conversational greetings (e.g., "Hello", "How are you") or questions that are unmistakably general-knowledge and cannot possibly be a search for a user's uploaded document.
- CRITICAL: Questions about specific technologies, services, products, companies, or technical concepts (e.g., "What is AWS Lambda?", "What is Docker?", "How does Kubernetes work?") must ALWAYS be classified as "factual" or "procedural" — NEVER as "general". The user may have uploaded documents about these topics, and the retrieval pipeline must be used to check.
- If the user types a noun phrase, a document name, or a topic without forming a full conversational sentence (e.g. "AWS Certified Cloud Practitioner certificate", "invoice 123", "resume", "flood.jpg"), assume they are searching for it in the uploaded knowledge base and classify it as "factual" or "ambiguous" depending on specificity. Do NOT classify it as "general".
- Do not route a normal general-knowledge question to retrieval
  merely because it is phrased as a factual question.
- Return exactly ONE category.
- Do not use "ambiguous" merely because a query is short.
- Use "ambiguous" when the missing information prevents a precise
  answer or when multiple plausible interpretations exist.
- Do not guess the user's intended subject.
- Do not use knowledge-base content to silently choose between
  multiple possible interpretations.
- If the query explicitly names a single clear subject, do NOT mark
  it ambiguous merely because other topics also exist in the
  knowledge base.
- If a previous conversational context has already been used to
  resolve a follow-up query into a standalone query, classify the
  resolved query based on that resolved wording.
- A clear query about a named entity remains factual even if it is
  short.
- A query containing an unresolved pronoun/reference is ambiguous
  unless the referenced subject is explicitly present in the query.
- A query containing multiple independent requests should not be
  treated as a simple factual query. If the request cannot be
  interpreted unambiguously, classify it as ambiguous.

Examples for the current knowledge-base style:

"Who won India's 600th Test?"
→ factual

"What does the Retrieval Agent do?"
→ factual

"How does semantic retrieval work?"
→ procedural

"What is the capital of the United States?"
→ general

"Who is the Prime Minister of Kenya?"
→ general

"What is artificial intelligence?"
→ general

"How are you?"
→ general

"Hello"
→ general

"What does the Retrieval Agent do?"
→ factual

"What is the leave policy in the uploaded document?"
→ factual

"How does the retrieval pipeline work according to the document?"
→ procedural

"Compare semantic search and exact search in the project."
→ comparative

"What about the new law?"
→ ambiguous

"Tell me about the bill."
→ ambiguous

"How did it affect companies?"
→ ambiguous

"Explain the new regulations."
→ ambiguous

"What is its significance?"
→ ambiguous

"Tell me about the committee."
→ ambiguous

"How much was approved and why?"
→ ambiguous

"What happened after that?"
→ ambiguous

"What happened in August?"
→ ambiguous

"What happened to AI and what happened in Indian sports?"
→ ambiguous

User query:
{query}
"""

    return structured_llm.invoke(prompt)