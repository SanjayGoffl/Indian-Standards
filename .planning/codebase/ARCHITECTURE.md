<!-- refreshed: 2026-09-27 -->
# Architecture

**Analysis Date:** 2026-09-27

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend (React SPA)                          │
│   State-driven tab router — `frontend/src/App.jsx`                   │
│   Pages: Auth, Dashboard, NewRecommendation, Results, Standards,      │
│   History, Analytics, AdminDashboard, ChatPage — `frontend/src/pages/`│
└──────────────────────────┬────────────────────────────────────────────┘
                            │ REST (fetch/axios) — `frontend/src/services/api.js`
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FastAPI Application Layer                       │
│   Entry point: `backend/app/main.py` (router registration + CORS)    │
│   Routers: `backend/app/api/*.py`, `backend/app/admin/router.py`,     │
│   `backend/app/analytics/router.py`, `backend/app/knowledge_gaps/`    │
├──────────────────────────┬─────────────────────────────────────────────┤
│  Auth/Deps               │  Query Orchestration (LangGraph)           │
│ `app/core/auth.py`       │ `app/orchestration/workflow.py`            │
│ `app/dependencies/auth.py`│ `app/orchestration/nodes.py`              │
└──────────────────────────┴──────────────────┬─────────────────────────┘
                                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Agent Layer (single-responsibility)               │
│  `app/agents/memory` `app/agents/query_understanding`                │
│  `app/agents/clarification` `app/agents/retrieval`                   │
│  `app/agents/response_generation`                                    │
└──────────────────────────┬─────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  Domain Services & RAG Layer                         │
│  `app/services/*.py` (standards ingestion, applicability engine,     │
│  BIS connector, recommendation, certification, upload, OCR)          │
│  `app/rag/*.py` (chunking, embedding, extraction, ChromaDB service)  │
└──────────────────────────┬─────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Persistence & External Stores                           │
│  Relational DB via SQLAlchemy — `app/core/database.py`,               │
│  `app/core/models.py`, `app/analytics/models.py`,                     │
│  `app/knowledge_gaps/models.py` (Alembic migrations in `backend/alembic`)│
│  Vector store: ChromaDB — `app/rag/chromadb_service.py`                │
│  LLM provider: Groq (via `app/core/llm.py`,                            │
│  `app/agents/response_generation/llm_call_groq.py`)                   │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| FastAPI app | Wires routers, CORS, DB table creation, standards seeding at startup | `backend/app/main.py` |
| Query API | Auth, conversation ownership check, invokes workflow, builds analytics/transparency payload | `backend/app/api/query.py` |
| Orchestration workflow | LangGraph state machine wiring memory → understanding → routing → retrieval/clarification/general → response → save memory | `backend/app/orchestration/workflow.py` |
| Orchestration nodes | Node implementations that call into agents and mutate `WorkflowState` | `backend/app/orchestration/nodes.py` |
| Query Router | Deterministic routing decision (retrieval vs clarification vs general) based on `QueryUnderstandingResult` | `backend/app/orchestration/query_router.py` |
| Query Understanding Agent | Classifies, extracts, normalizes query intent | `backend/app/agents/query_understanding/agent.py` |
| Clarification Agent | Detects ambiguity, generates clarification questions, refines queries with user answers | `backend/app/agents/clarification/agent.py` |
| Conversation Memory Agent | Loads/stores conversation turns for context-aware follow-ups | `backend/app/agents/memory/agent.py` |
| Retrieval Agent | Combines exact + semantic search, reranking, diversification, relevance thresholding | `backend/app/agents/retrieval/agent.py` |
| Response Generation Agent | Builds grounded LLM answer from retrieved chunks, computes confidence, detects insufficient-context refusals | `backend/app/agents/response_generation/agent.py` |
| RAG chunking/embedding/extraction | Document chunking, embedding generation, text extraction from uploads | `backend/app/rag/chunking.py`, `backend/app/rag/embedding.py`, `backend/app/rag/extractor.py` |
| ChromaDB service | Vector store interface: indexing, semantic search, filename-based fallback search | `backend/app/rag/chromadb_service.py` |
| Standards services | Ingestion, applicability engine, BIS connector, knowledge base, retrieval, version verification | `backend/app/services/*.py` |
| Recommendation engine | Requirement analysis, recommendation generation/validation, certification lookup | `backend/app/services/requirement_analyzer.py`, `recommendation_service.py`, `recommendation_validator.py`, `certification_service.py` |
| Analytics module | Query logging, theme extraction/embedding, procurement analytics | `backend/app/analytics/*.py`, `backend/app/api/analytics.py` |
| Knowledge gaps module | Detects and records unanswered/low-confidence queries | `backend/app/knowledge_gaps/*.py` |
| Transparency service | Builds evidence/grounding metadata returned to frontend | `backend/app/transparency/service.py` |
| Voice module | Speech-to-text input handling and TTS-ready text preparation | `backend/app/voice/*.py` |
| Admin module | Admin dashboard endpoints (users, documents) | `backend/app/admin/*.py` |
| Database layer | Engine/session factory, declarative `Base`, `init_db()` idempotent column migrations | `backend/app/core/database.py` |
| Frontend App shell | State-based tab router (no react-router), owns `activeTab`/`selectedRequestId` | `frontend/src/App.jsx` |
| Frontend API client | Centralized fetch wrapper for backend calls | `frontend/src/services/api.js` |
| Auth context | React context providing `user`, `isLoggedIn`, `login`/`logout` | `frontend/src/context/Authcontext.jsx` |

## Pattern Overview

**Overall:** Layered service architecture with an agentic RAG core orchestrated by a LangGraph state machine. FastAPI provides the HTTP boundary; a directed graph of nodes (each backed by a single-purpose "agent" class/module) performs query understanding, routing, retrieval, and generation.

**Key Characteristics:**
- Explicit state machine (`WorkflowState` TypedDict) threaded through every node — no hidden global mutation of request state.
- Agents are stateless callables/classes instantiated once at module load (`_llm`, `_query_understanding_agent`, `_retrieval_agent`, `_clarification_agent`, `_memory_agent` in `backend/app/orchestration/nodes.py`), then reused across requests.
- Defense-in-depth fallback chains in retrieval (exact → semantic+threshold → filename fallback → semantic no-threshold) rather than failing fast, favoring "always return something" over strict correctness.
- Analytics/knowledge-gap logging is deliberately isolated with try/except + rollback so instrumentation failures never break the core query path (`backend/app/api/query.py`).
- Frontend uses local component state (`useState`) for navigation instead of a router library — "SPA-as-single-page-with-switch" pattern in `frontend/src/App.jsx`.

## Layers

**API Layer:**
- Purpose: HTTP request/response handling, auth enforcement, request validation (Pydantic), translating orchestration results into API-shaped JSON.
- Location: `backend/app/api/`, `backend/app/admin/`, `backend/app/analytics/router.py`, `backend/app/knowledge_gaps/router.py`
- Contains: FastAPI `APIRouter` instances, one file per resource/domain (auth, documents, query, upload, voice, knowledge_base, procurement, standards, analytics, health, conversations).
- Depends on: Orchestration layer, services layer, `app/core/database.py` (via `Depends(get_db)`), `app/dependencies/auth.py`.
- Used by: Frontend via REST calls (`frontend/src/services/api.js`, `analytics.js`).

**Orchestration Layer:**
- Purpose: Coordinates multi-step agentic query processing as a LangGraph graph.
- Location: `backend/app/orchestration/`
- Contains: `workflow.py` (graph construction, conditional edges, `run_workflow` public entry), `nodes.py` (node functions), `state.py` (`WorkflowState` TypedDict), `query_router.py` (deterministic routing rules).
- Depends on: Agent layer (`app/agents/*`), `app/core/llm.py`.
- Used by: `backend/app/api/query.py`.

**Agent Layer:**
- Purpose: Single-responsibility units of "intelligence" — each wraps a narrow piece of LLM or search logic.
- Location: `backend/app/agents/{clarification,memory,query_understanding,response_generation,retrieval}/`
- Contains: Agent classes (e.g. `QueryUnderstandingAgent`, `RetrievalAgent`, `ClarificationAgent`, `ConversationMemoryAgent`), Pydantic schemas per agent, prompt builders.
- Depends on: `app/rag/*` (retrieval agent), `app/core/llm.py` (LLM-backed agents).
- Used by: Orchestration nodes only — agents are never called directly from API routers.

**Domain Services Layer:**
- Purpose: Business logic not tied to the conversational query path — standards ingestion/applicability, procurement recommendations, certification, document/upload handling, OCR, metadata, benchmarking.
- Location: `backend/app/services/`
- Contains: ~19 service modules, each typically exposing plain functions or a service class consumed by one or more API routers.
- Depends on: `app/rag/*`, `app/core/models.py`, `app/core/database.py`.
- Used by: `backend/app/api/procurement.py`, `standards.py`, `upload.py`, `documents.py`, `knowledge_base.py`.

**RAG Layer:**
- Purpose: Document ingestion pipeline (extraction → chunking → embedding) and vector search.
- Location: `backend/app/rag/`
- Contains: `chunking.py`, `embedding.py`, `extractor.py`, `chromadb_service.py` (ChromaDB collection management, semantic search, filename fallback search).
- Depends on: `app/core/embedding_model.py`.
- Used by: Retrieval agent (`app/agents/retrieval/*`), upload/document services.

**Persistence Layer:**
- Purpose: Relational data model and session management.
- Location: `backend/app/core/database.py`, `backend/app/core/models.py`, `backend/app/analytics/models.py`, `backend/app/knowledge_gaps/models.py`, `backend/alembic/`
- Contains: SQLAlchemy `engine`/`SessionLocal`/`Base`, ORM models, `init_db()` with hand-rolled idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` statements (see Anti-Patterns), Alembic migration scripts.
- Depends on: `DATABASE_URL` env var (SQLite or Postgres — dialect-sensitive `connect_args`).
- Used by: Every layer via `Depends(get_db)` or direct `SessionLocal()` instantiation.

**Frontend Presentation Layer:**
- Purpose: SPA UI, forms, dashboards, chat interface, admin views.
- Location: `frontend/src/pages/`, `frontend/src/components/`
- Contains: One `.jsx` file per page/route (`DashboardPage`, `ChatPage`, `AdminDashboard`, etc.), reusable components (`Sidebar`, `ChatBubble`, `CitationDisplay`, `FileUploader`, `VoiceInput`).
- Depends on: `frontend/src/services/api.js`, `frontend/src/context/Authcontext.jsx`, `frontend/src/hooks/useSpeechRecognition.js`.
- Used by: `frontend/src/App.jsx` (top-level tab switch), `frontend/src/main.jsx` (mount point).

## Data Flow

### Primary Request Path (Chat Query)

1. Frontend submits a query via `frontend/src/services/api.js` → `POST /query` (`backend/app/api/query.py:85`).
2. API validates auth (`get_current_user`, `backend/app/dependencies/auth.py`) and conversation ownership, then calls `run_workflow()` (`backend/app/orchestration/workflow.py:328`).
3. Graph executes `memory_node` (`backend/app/orchestration/nodes.py:279`) — loads prior conversation turns if `conversation_id` present.
4. `route_after_memory` sends new queries to `query_understanding_node` (`nodes.py:334`), or clarification answers directly to `clarification_node`.
5. `routing_node` (`nodes.py:409`) calls the deterministic `route_query()` (`backend/app/orchestration/query_router.py`) to pick `retrieval`, `clarification`, or `general`.
6. Retrieval path: `retrieval_node` (`nodes.py:627`) calls `RetrievalAgent.run()` (`backend/app/agents/retrieval/agent.py`), with three fallback tiers (user-filtered semantic+exact → backward-compat no-user-filter retry → filename-based fallback via `search_by_filename` in `app/rag/chromadb_service.py` → pure-semantic no-threshold fallback).
7. `response_generation_node` (`nodes.py:839`) calls `generate_response()` (`backend/app/agents/response_generation/agent.py`), which builds a grounded answer via `llm_call_groq.py` and computes a confidence score.
8. `save_memory_node` (`nodes.py:1038`) persists the exchange when `conversation_id` is set.
9. Back in `backend/app/api/query.py`, the result is enriched with transparency data (`app/transparency/service.py`), speech text (`app/voice/output.py`), analytics logging (`app/analytics/service.py:log_query`), and knowledge-gap detection (`app/knowledge_gaps/service.py`) before returning JSON.

### Document Ingestion Flow

1. Frontend uploads a file via `FileUploader.jsx` → `POST /upload` (`backend/app/api/upload.py`) or `/documents` (`backend/app/api/documents.py`).
2. `app/services/upload_service.py` / `document_service.py` extract text (`app/rag/extractor.py`, `app/services/ocr_service.py` for images).
3. `app/rag/chunking.py` splits extracted text into chunks; `app/rag/embedding.py` generates vector embeddings.
4. `app/rag/chromadb_service.py` indexes chunks into the ChromaDB collection, tagged with `user_id` for later filtering.

### Standards/Procurement Recommendation Flow

1. `POST` to `backend/app/api/procurement.py` triggers `app/services/requirement_analyzer.py`.
2. `app/services/applicability_engine.py` and `app/services/standards_retrieval.py` determine which Indian Standards apply.
3. `app/services/recommendation_service.py` builds recommendations; `recommendation_validator.py` checks them; `certification_service.py` attaches certification requirements.
4. Results are persisted and retrievable via `backend/app/api/standards.py` and displayed on `RecommendationResultsPage.jsx`.

**State Management:**
- Backend: Request-scoped `WorkflowState` dict passed through LangGraph nodes; no cross-request in-memory state except the shared singleton agent instances (stateless) and the SQLAlchemy engine/session factory.
- Frontend: Component-local `useState` in `App.jsx` for active tab/selected request; `Authcontext.jsx` (React Context) for auth/session state; no global store (Redux/Zustand) present.

## Key Abstractions

**WorkflowState (TypedDict):**
- Purpose: Single shared state object threaded through every LangGraph node; explicitly documents which fields belong to which milestone (M2 core fields vs M3 memory/clarification fields) plus an internal `_db` field that must never leak to the API response.
- Examples: `backend/app/orchestration/state.py`
- Pattern: `TypedDict(total=False)` — every field optional, nodes use `state.get(key, default)` defensively.

**Agent classes (`*Agent`):**
- Purpose: Encapsulate one stage of the RAG pipeline behind a `.run()`/`.generate_question()`/`.get_context()`-style method.
- Examples: `QueryUnderstandingAgent`, `RetrievalAgent`, `ClarificationAgent`, `ConversationMemoryAgent` — all instantiated once in `backend/app/orchestration/nodes.py` lines 68-85.
- Pattern: Constructor takes config/LLM dependency; instance is a module-level singleton reused across requests (not re-instantiated per request).

**Pydantic schemas per agent (`schemas.py`):**
- Purpose: Typed contracts for agent inputs/outputs (e.g. `QueryUnderstandingResult`, `QueryRefinementRequest`).
- Examples: `backend/app/agents/query_understanding/schemas.py`, `backend/app/agents/clarification/schemas.py`, `backend/app/agents/response_generation/schemas.py`
- Pattern: `.model_dump()` used to convert to plain dicts before entering `WorkflowState` or JSON responses.

## Entry Points

**FastAPI HTTP server:**
- Location: `backend/app/main.py`
- Triggers: `uvicorn app.main:app` (implied by FastAPI app object; no explicit `if __name__` runner in `main.py`).
- Responsibilities: Registers all routers, configures CORS from `app/core/config.py`, runs `lifespan()` to create DB tables and seed Indian Standards catalog (`app/services/standards_knowledge_base.py:seed_indian_standards`).

**LangGraph workflow (programmatic + CLI):**
- Location: `backend/app/orchestration/workflow.py`
- Triggers: `run_workflow()` called from `backend/app/api/query.py`; also runnable standalone via `python -m app.orchestration.workflow` (guarded `if __name__ == "__main__":` block at line 439 with inline smoke tests).

**Frontend Vite entry:**
- Location: `frontend/src/main.jsx` → mounts `App.jsx`
- Triggers: `npm run dev` / Vite build (`frontend/vite.config.js`).
- Responsibilities: Wraps app in `AuthProvider` (from `Authcontext.jsx`), renders `App`.

**Alembic migrations:**
- Location: `backend/alembic/env.py`, `backend/alembic/versions/`
- Triggers: `alembic upgrade head` (manual/CI), configured via `backend/alembic.ini`.
- Responsibilities: Formal schema migrations — coexists with the ad-hoc `init_db()` column-patching in `app/core/database.py` (see Anti-Patterns).

## Architectural Constraints

- **Threading:** FastAPI's default sync-request model; SQLAlchemy sessions are request-scoped via `Depends(get_db)` (`backend/app/core/database.py:100`), not shared across requests. No explicit async DB driver — routes use sync SQLAlchemy `Session`.
- **Global state:** Module-level singleton agent instances and the compiled LangGraph graph (`workflow = build_workflow()`, `backend/app/orchestration/workflow.py:325`) are created once at import time and shared across all requests — agents must remain stateless/thread-safe.
- **Circular imports:** None observed directly, but `backend/app/rag/chromadb_service.py` is imported lazily inside `retrieval_node()` (`backend/app/orchestration/nodes.py:705`) rather than at module top — likely to avoid heavy import-time cost or a circular dependency with `app/agents/retrieval`.
- **Database dialect coupling:** `init_db()` (`backend/app/core/database.py:52-97`) issues raw `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` SQL, which is PostgreSQL syntax and will fail silently (caught and logged as debug) on SQLite — meaning schema drift may go unnoticed on SQLite environments.

## Anti-Patterns

### Hand-rolled schema migration inside application startup

**What happens:** `init_db()` in `backend/app/core/database.py` runs ~30 raw `ALTER TABLE ADD COLUMN IF NOT EXISTS` statements every time it's called, in addition to the formal Alembic migration setup in `backend/alembic/`.
**Why it's wrong:** Two competing migration systems (Alembic + ad-hoc SQL) can drift out of sync; the raw SQL is Postgres-specific and silently no-ops on SQLite (caught by a bare `except Exception` at line 96), masking real schema errors.
**Do this instead:** Consolidate all schema changes into Alembic migrations (`backend/alembic/versions/`) and remove the raw `ALTER TABLE` list from `init_db()`, or gate it behind an explicit dev-only flag.

### Broad exception swallowing on startup

**What happens:** `backend/app/main.py` lifespan wraps `Base.metadata.create_all()` and `seed_indian_standards()` in a bare `try/except Exception` that only prints a warning (lines 39-45).
**Why it's wrong:** A failed table creation or seed step will not stop the app from starting, so the API can come up in a broken/partially-initialized state without a clear operator signal.
**Do this instead:** Log with proper severity (`logging.error`) and consider failing fast in production, or health-check the DB state explicitly.

### Debug `print()` statements embedded in orchestration logic

**What happens:** `retrieval_node()` and `response_generation_node()` in `backend/app/orchestration/nodes.py` contain many `print(...)` calls for relevance scores, fallback status, etc. (lines 682-820, 875-905).
**Why it's wrong:** Print statements bypass structured logging, can't be filtered/leveled in production, and clutter stdout under load.
**Do this instead:** Replace with the `logging` module (already used elsewhere, e.g. `backend/app/core/database.py`) at appropriate levels (`debug`/`info`).

## Error Handling

**Strategy:** Defensive per-node try/except in orchestration (`backend/app/orchestration/nodes.py`) that sets `state["error"]` rather than raising, allowing the graph's conditional edges (`route_after_*` functions in `workflow.py`) to short-circuit to `END` on any error. At the API layer, `backend/app/api/query.py` catches `HTTPException` (re-raised), `ValueError` (→ 400), and generic `Exception` (→ 500).

**Patterns:**
- Node-level: catch exceptions, return `{**state, "error": f"<Stage> failed: {error}"}` — never raise from within a node.
- API-level: analytics/knowledge-gap side effects wrapped in their own try/except with `db.rollback()` so they can never break the primary response (`backend/app/api/query.py:332-378`).

## Cross-Cutting Concerns

**Logging:** Mixed — `logging` module used in `app/core/database.py`; raw `print()` used extensively in `app/orchestration/nodes.py` for debug tracing (see Anti-Patterns).
**Validation:** Pydantic models throughout (`app/models/request_models.py`, per-agent `schemas.py` files) validate request/response shapes; `run_workflow()` performs manual type/value checks on `query`/`k` before invoking the graph.
**Authentication:** JWT/session-based via `app/core/auth.py` and `app/dependencies/auth.py` (`get_current_user` dependency), enforced per-route with `Depends(get_current_user)`.

---

*Architecture analysis: 2026-09-27*
