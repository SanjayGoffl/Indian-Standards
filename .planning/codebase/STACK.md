# Technology Stack

**Analysis Date:** 2026-09-27

## Languages

**Primary:**
- Python 3.11.9 (`backend/.python-version`) - backend API, RAG pipeline, agents
- JavaScript (ES2020+, JSX) - `frontend/src/**` React application

**Secondary:**
- SQL (Alembic migration DDL, raw `ALTER TABLE` statements in `backend/app/core/database.py`)
- HTML/CSS via Vite/React (`frontend/index.html`)

## Runtime

**Environment:**
- Backend: Python 3.11 virtualenv at `backend/.venv`
- Frontend: Node.js (version not pinned via `.nvmrc`; Vite 8 requires modern Node, engines not declared in `frontend/package.json`)

**Package Manager:**
- Backend: pip, dependencies declared unpinned/pinned mix in `backend/requirements.txt` (no lockfile / `requirements.lock` present)
- Frontend: npm, lockfile present at `frontend/package-lock.json`

## Frameworks

**Core:**
- FastAPI 0.141.1 (`backend/requirements.txt`, entrypoint `backend/app/main.py`) - REST API framework
- Uvicorn 0.52.1 - ASGI server
- React 19.2.8 + React DOM 19.2.8 (`frontend/package.json`) - frontend SPA
- Vite 8.2.0 (`frontend/vite.config.js`) - frontend build/dev server, uses `@vitejs/plugin-react`
- LangChain 1.3.14 / `langchain-text-splitters` 1.1.2 / `langchain-groq` 1.1.3 / LangGraph 1.2.10 - LLM orchestration and agent graph (used across `backend/app/agents/*` and `backend/app/orchestration/`)

**Testing:**
- Custom test scripts under `backend/app/test/` (e.g. `test_bis_ingestion_and_retrieval.py`, `test_procurement_engine.py`, `test_hdpe_piping_applicability.py`, `test_new_improvements_and_security.py`) - no pytest config file detected; framework appears to be plain Python scripts/assertions rather than a configured pytest suite
- No frontend test framework detected (no Jest/Vitest config in `frontend/`)

**Build/Dev:**
- oxlint 1.75.0 (`frontend/.oxlintrc.json`) - frontend linter (`npm run lint`)
- Alembic (`backend/alembic.ini`, `backend/alembic/`) - database schema migrations

## Key Dependencies

**Critical:**
- `langchain-groq` 1.1.3 + `langgraph` 1.2.10 - LLM orchestration for the multi-agent RAG workflow (query understanding, clarification, retrieval, response generation) in `backend/app/agents/`
- `sentence-transformers` 5.7.0 - embeddings via `all-MiniLM-L6-v2` model, loaded once via `backend/app/core/embedding_model.py`
- `chromadb` 1.5.9 - vector store for semantic search, persisted at `chroma_db/` (path configured in `backend/app/core/config.py` as `CHROMA_DB_PATH`)
- `SQLAlchemy` + `psycopg[binary]` - ORM and PostgreSQL driver (`backend/app/core/database.py`)
- `python-jose[cryptography]` 3.5.0 + `bcrypt` - JWT auth and password hashing (`backend/app/core/auth.py`)

**Infrastructure:**
- `pypdf`, `python-docx`, `pymupdf`, `pandas`, `Pillow` - document ingestion/parsing for uploaded standards documents
- `paddlepaddle` + `paddleocr` - OCR for scanned/image document ingestion
- `alembic` - versioned DB schema migrations
- `email-validator` - used with Pydantic models for auth email validation
- `react-markdown` 10.1.0 + `remark-gfm` 4.0.1 - renders LLM markdown responses in the frontend chat UI

## Configuration

**Environment:**
- Backend config via `.env` file loaded with `python-dotenv` in multiple modules (`backend/app/core/database.py`, `backend/app/core/auth.py`, `backend/app/core/llm.py`). Template at `backend/.env.example`; actual `.env` present but not read (secret-protected).
  - Key vars: `GROQ_API_KEY`, `GROQ_MODEL`, `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `FRONTEND_URL` (used for CORS in `backend/app/core/config.py`)
- Frontend config via Vite env vars, template at `frontend/.env.example` (`VITE_API_BASE_URL=http://127.0.0.1:8000`); actual `frontend/.env` present but not read (secret-protected)

**Build:**
- `frontend/vite.config.js` - Vite build config using `@vitejs/plugin-react`
- `frontend/.oxlintrc.json` - lint rules
- `backend/alembic.ini` + `backend/alembic/` - migration environment config

## Platform Requirements

**Development:**
- Python 3.11.x virtualenv (`backend/.venv`)
- Node.js compatible with Vite 8 / React 19 (no explicit engine pin found)
- PostgreSQL database reachable at `DATABASE_URL` (default local: `postgresql+psycopg://postgres:...@localhost:5432/querynest`)
- Local filesystem folders auto-created/used: `uploads/`, `metadata/`, `chroma_db/` (all relative to `backend/` per `backend/app/core/config.py`)

**Production:**
- Backend deployable as an ASGI app (Uvicorn) with FastAPI lifespan startup seeding standards data (`backend/app/main.py`)
- No containerization files (Dockerfile/docker-compose) detected in repo root, `backend/`, or `frontend/`
- No CI/CD pipeline config detected (no `.github/workflows`)

---

*Stack analysis: 2026-09-27*
