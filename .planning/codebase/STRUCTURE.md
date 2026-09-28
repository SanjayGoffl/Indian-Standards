# Codebase Structure

**Analysis Date:** 2026-09-27

## Directory Layout

```
indian_standards/
├── backend/                        # FastAPI + LangGraph Python backend
│   ├── alembic/                    # Formal DB schema migrations
│   │   ├── versions/               # Individual migration scripts
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── app/
│   │   ├── admin/                  # Admin dashboard API (users, docs)
│   │   ├── agents/                 # Single-responsibility RAG agents
│   │   │   ├── clarification/      # Ambiguity detection + query refinement
│   │   │   ├── memory/             # Conversation memory persistence
│   │   │   ├── query_understanding/# Intent classification/extraction
│   │   │   ├── response_generation/# Grounded answer generation (Groq LLM)
│   │   │   └── retrieval/          # Exact + semantic search, reranking
│   │   ├── analytics/              # Query analytics, theme extraction
│   │   ├── api/                    # FastAPI routers (one file per resource)
│   │   ├── core/                   # DB engine, auth, config, LLM client, ORM models
│   │   ├── dependencies/           # FastAPI dependency providers (auth)
│   │   ├── knowledge_gaps/         # Knowledge-gap detection/tracking
│   │   ├── models/                 # Pydantic request/response schemas
│   │   ├── orchestration/          # LangGraph workflow, nodes, state, router
│   │   ├── rag/                    # Chunking, embedding, extraction, ChromaDB
│   │   ├── services/               # Domain services (standards, procurement, OCR…)
│   │   ├── test/                   # Pytest test suite
│   │   ├── transparency/           # Response grounding/evidence metadata
│   │   ├── utils/                  # Small shared utilities
│   │   ├── voice/                  # Speech input/output helpers
│   │   ├── __init__.py
│   │   └── main.py                 # FastAPI app entry point
│   ├── scratch/                    # Ad-hoc manual test scripts (not pytest)
│   ├── .env / .env.example
│   ├── alembic.ini
│   └── requirements.txt
├── frontend/                       # React (Vite) SPA
│   ├── public/                     # Static assets (favicon, icons)
│   ├── src/
│   │   ├── assets/                 # Images used by components
│   │   ├── components/             # Reusable UI components
│   │   ├── context/                # React Context providers (auth)
│   │   ├── hooks/                  # Custom React hooks
│   │   ├── pages/                  # One file per top-level page/tab
│   │   ├── services/               # API client modules
│   │   ├── App.jsx                 # Root component + tab router
│   │   ├── main.jsx                # Vite/React mount entry point
│   │   └── index.css / App.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Directory Purposes

**`backend/app/api/`:**
- Purpose: HTTP-facing routers, one file per domain resource.
- Contains: `auth.py`, `query.py`, `documents.py`, `upload.py`, `voice.py`, `knowledge_base.py`, `procurement.py`, `standards.py`, `analytics.py`, `health.py`, `conversations.py`.
- Key files: `query.py` (main chat/RAG endpoint), `procurement.py` (recommendation engine entry point).

**`backend/app/orchestration/`:**
- Purpose: LangGraph state machine that coordinates the agentic query pipeline.
- Contains: `workflow.py` (graph build + `run_workflow`), `nodes.py` (node functions), `state.py` (`WorkflowState` TypedDict), `query_router.py` (routing rules).

**`backend/app/agents/`:**
- Purpose: Narrow, single-purpose logic units invoked only from orchestration nodes.
- Contains: One subpackage per agent (`clarification/`, `memory/`, `query_understanding/`, `response_generation/`, `retrieval/`), each with `agent.py` + `schemas.py` and supporting modules (e.g. `retrieval/semantic_search.py`, `retrieval/reranker.py`, `retrieval/exact_search.py`).

**`backend/app/services/`:**
- Purpose: Business logic independent of the conversational query path — standards data, procurement recommendations, document/OCR handling.
- Contains: `applicability_engine.py`, `bis_connector.py`, `standards_ingestion.py`, `standards_knowledge_base.py`, `standards_retrieval.py`, `requirement_analyzer.py`, `recommendation_service.py`, `recommendation_validator.py`, `certification_service.py`, `document_service.py`, `upload_service.py`, `ocr_service.py`, `metadata_service.py`, `version_verification.py`, `benchmark_evaluator.py`, `knowledge_base_service.py`, `query_service.py`.

**`backend/app/rag/`:**
- Purpose: Document ingestion (extraction/chunking/embedding) and vector search infrastructure.
- Contains: `extractor.py`, `chunking.py`, `embedding.py`, `chromadb_service.py`.

**`backend/app/core/`:**
- Purpose: Cross-cutting infrastructure — DB, auth, config, ORM models, LLM/embedding client setup.
- Contains: `database.py` (engine/session/`init_db`), `models.py` (SQLAlchemy ORM models: `Conversation`, `User`, `IndianStandard`, etc.), `auth.py`, `config.py` (`CORS_ALLOW_ORIGINS` and other env-derived settings), `llm.py` (`get_llm()`), `embedding_model.py`.

**`backend/app/models/`:**
- Purpose: Pydantic request/response schemas not tied to a specific agent.
- Contains: `request_models.py` (`QueryRequest`), `auth_models.py`, `knowledge_base_schemas.py`, `procurement_schemas.py`.

**`backend/app/analytics/`, `backend/app/knowledge_gaps/`, `backend/app/transparency/`, `backend/app/voice/`, `backend/app/admin/`:**
- Purpose: Feature-scoped vertical modules, each following the `router.py` + `service.py` + `schemas.py` (+ `models.py`) convention.

**`backend/app/test/`:**
- Purpose: Pytest suite exercising ingestion/retrieval, applicability, memory, procurement engine, and security.
- Contains: `conftest.py`, `test_bis_ingestion_and_retrieval.py`, `test_hdpe_piping_applicability.py`, `test_memory.py`, `test_new_improvements_and_security.py`, `test_procurement_engine.py`.

**`backend/scratch/`:**
- Purpose: Manual/ad-hoc scripts for exploratory testing, not part of the pytest suite.
- Contains: `test_all_scenarios.py`, `test_gloves.py`.
- Generated: No. Committed: Yes (but not CI-run).

**`backend/alembic/`:**
- Purpose: Formal SQLAlchemy schema migrations (coexists with ad-hoc column patching in `app/core/database.py::init_db`).
- Contains: `versions/` (one file per migration), `env.py`, `script.py.mako`.

**`frontend/src/pages/`:**
- Purpose: One file per top-level application view, switched by `App.jsx`'s `activeTab` state (no URL routing library).
- Contains: `AuthPage.jsx`, `DashboardPage.jsx`, `NewRecommendationPage.jsx`, `RecommendationResultsPage.jsx`, `StandardsCatalogPage.jsx`, `HistoryPage.jsx`, `AnalyticsPage.jsx`, `ChatPage.jsx`, `UploadPage.jsx`, `KnowledgeGapPage.jsx`, `AdminDashboard.jsx`, `AdminAnalytics.jsx`, `AdminDocuments.jsx`, `AdminUsers.jsx`, `AdminUserDetail.jsx`.

**`frontend/src/components/`:**
- Purpose: Reusable UI building blocks shared across pages.
- Contains: `Sidebar.jsx` (nav), `ChatBubble.jsx`, `CitationDisplay.jsx`, `GroundingEvidenceView.jsx`, `FileUploader.jsx`, `VoiceInput.jsx`, `speechtotext.jsx`, `Footer.jsx`.

**`frontend/src/services/`:**
- Purpose: Centralized API client functions wrapping backend REST calls.
- Contains: `api.js` (general endpoints), `analytics.js` (analytics-specific calls).

**`frontend/src/context/`:**
- Purpose: React Context providers for cross-component state.
- Contains: `Authcontext.jsx` (`useAuth()` hook, login/logout, session state).

**`frontend/src/hooks/`:**
- Purpose: Custom reusable React hooks.
- Contains: `useSpeechRecognition.js`.

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: FastAPI app, router registration, CORS, startup lifespan.
- `backend/app/orchestration/workflow.py`: `run_workflow()` — programmatic entry to the RAG pipeline; also has a CLI smoke-test block.
- `frontend/src/main.jsx`: Vite/React mount point.

**Configuration:**
- `backend/app/core/config.py`: CORS origins and other app settings (env-derived).
- `backend/.env` / `backend/.env.example`: Backend environment variables (existence noted only — never read contents).
- `frontend/.env` / `frontend/.env.example`: Frontend environment variables (existence noted only).
- `backend/alembic.ini`, `backend/alembic/env.py`: Migration configuration.
- `frontend/vite.config.js`: Vite build/dev server config.
- `frontend/.oxlintrc.json`: Linter config.

**Core Logic:**
- `backend/app/orchestration/nodes.py`: All LangGraph node implementations (the "brain" wiring agents together).
- `backend/app/agents/retrieval/agent.py`: Retrieval orchestration (exact + semantic + reranking + diversification).
- `backend/app/services/applicability_engine.py`, `requirement_analyzer.py`, `recommendation_service.py`: Procurement recommendation domain logic.

**Testing:**
- `backend/app/test/`: Pytest suite (see `TESTING.md` if generated separately).
- `backend/scratch/`: Manual verification scripts, not part of automated test runs.

## Naming Conventions

**Files:**
- Python: `snake_case.py` throughout backend (e.g. `standards_knowledge_base.py`, `applicability_engine.py`).
- React components: `PascalCase.jsx` (e.g. `ChatBubble.jsx`, `DashboardPage.jsx`); one exception observed: `speechtotext.jsx` (lowercase) and `Authcontext.jsx` (lowercase "context") — inconsistent casing exists, follow `PascalCase.jsx` for new components.
- Page components: suffixed `*Page.jsx` (e.g. `ChatPage.jsx`, `UploadPage.jsx`, `HistoryPage.jsx`).
- Companion CSS: co-located with matching name (e.g. `AdminDashboard.jsx` + `AdminDashboard.css`, `HistoryPage.jsx` + `HistoryPage.css`).

**Directories:**
- Backend: lowercase, singular-or-plural-as-natural noun per feature/domain (`agents`, `services`, `models`, `api`, `rag`), each agent/feature subpackage has its own `__init__.py`.
- Frontend: lowercase plural by role (`pages`, `components`, `services`, `hooks`, `context`).

## Where to Add New Code

**New Feature (backend, conversational path):**
- New agent logic: `backend/app/agents/<new_agent>/agent.py` + `schemas.py`, wired into `backend/app/orchestration/nodes.py` and `workflow.py`.
- New non-conversational domain logic: `backend/app/services/<new_service>.py`.
- New API endpoint: add to an existing router in `backend/app/api/` or create a new router file there, then register it in `backend/app/main.py`.
- Tests: `backend/app/test/test_<feature>.py`, using `backend/app/test/conftest.py` fixtures.

**New Feature (frontend):**
- New page/tab: `frontend/src/pages/<Name>Page.jsx`, then add a case to the `renderActivePage()` switch in `frontend/src/App.jsx` and a nav entry in `frontend/src/components/Sidebar.jsx`.
- New reusable UI: `frontend/src/components/<Name>.jsx`.
- New API call: add a function to `frontend/src/services/api.js` (or `analytics.js` for analytics-specific calls).

**Database changes:**
- Add/modify SQLAlchemy models in `backend/app/core/models.py` (or the relevant feature's `models.py`, e.g. `backend/app/analytics/models.py`).
- Generate an Alembic migration under `backend/alembic/versions/` — do not extend the raw `ALTER TABLE` list in `backend/app/core/database.py::init_db()` (see `ARCHITECTURE.md` Anti-Patterns).

**Utilities:**
- Shared backend helpers: `backend/app/utils/`.
- Shared frontend hooks: `frontend/src/hooks/`.

## Special Directories

**`backend/.venv/`:**
- Purpose: Python virtual environment.
- Generated: Yes. Committed: No (`.gitignore`'d).

**`backend/scratch/`:**
- Purpose: Manual exploratory test scripts, separate from the pytest suite in `backend/app/test/`.
- Generated: No. Committed: Yes, but excluded from CI test discovery conventions (verify actual CI config if added later).

**`backend/alembic/versions/`:**
- Purpose: Auto-generated migration scripts (via `alembic revision --autogenerate`), then hand-edited.
- Generated: Partially (scaffolded, then edited). Committed: Yes.

---

*Structure analysis: 2026-09-27*
